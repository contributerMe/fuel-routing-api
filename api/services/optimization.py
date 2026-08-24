import math
import heapq
from api.models import FuelStation

def haversine(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance in miles between two points."""
    R = 3958.8  # Earth radius in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def distance_point_to_segment(px, py, x1, y1, x2, y2):
    """
    Returns the distance from point (px, py) to line segment (x1,y1)-(x2,y2)
    and the fraction of the segment where the closest point lies.
    Coordinates are approx euclidean for small distances.
    """
    l2 = (x2 - x1)**2 + (y2 - y1)**2
    if l2 == 0:
        return haversine(px, py, x1, y1), 0.0
    t = max(0, min(1, ((px - x1)*(x2 - x1) + (py - y1)*(y2 - y1)) / l2))
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)
    return haversine(px, py, proj_x, proj_y), t

def get_optimal_fuel_stops(route_geometry, total_distance_meters):
    """
    Finds the optimal fuel stops given a GeoJSON LineString geometry.
    Vehicle range: 500 miles. MPG: 10.
    """
    MAX_RANGE_MILES = 500.0
    MPG = 10.0
    SEARCH_RADIUS_MILES = 5.0
    
    coords = route_geometry['coordinates']
    if not coords:
        return None, 0
        
    # 1. Bounding Box for initial fast filtering
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)
    
    # Margin approx 5 miles (1 degree is ~69 miles)
    margin = 5.0 / 60.0
    candidates = FuelStation.objects.filter(
        longitude__gte=min_lon - margin,
        longitude__lte=max_lon + margin,
        latitude__gte=min_lat - margin,
        latitude__lte=max_lat + margin
    )
    
    # 2. Project stations onto the route to find their distance from start
    # We pre-calculate cumulative distances of route segments
    segment_cum_dist = [0.0]
    for i in range(1, len(coords)):
        d = haversine(coords[i-1][0], coords[i-1][1], coords[i][0], coords[i][1])
        segment_cum_dist.append(segment_cum_dist[-1] + d)
        
    total_haversine_miles = segment_cum_dist[-1]
    true_total_miles = total_distance_meters / 1609.34
    scale_factor = true_total_miles / total_haversine_miles if total_haversine_miles > 0 else 1.0
    
    valid_stations = []
    for station in candidates:
        min_dist = float('inf')
        best_route_dist = 0
        
        # Find closest segment
        for i in range(1, len(coords)):
            dist_to_seg, t = distance_point_to_segment(
                station.longitude, station.latitude,
                coords[i-1][0], coords[i-1][1],
                coords[i][0], coords[i][1]
            )
            if dist_to_seg < min_dist:
                min_dist = dist_to_seg
                # route distance to this projection point, scaled to true driving distance
                seg_len = segment_cum_dist[i] - segment_cum_dist[i-1]
                best_route_dist = (segment_cum_dist[i-1] + (t * seg_len)) * scale_factor
                
        if min_dist <= SEARCH_RADIUS_MILES:
            valid_stations.append({
                'id': station.id,
                'name': station.name,
                'address': station.address,
                'city': station.city,
                'state': station.state,
                'price': station.retail_price,
                'route_dist': best_route_dist,
                'coords': (station.longitude, station.latitude)
            })
            
    # 3. Shortest path algorithm 
    nodes = [{'id': 'start', 'route_dist': 0.0, 'price': 0.0}]
    # Sort stations by distance from start
    valid_stations.sort(key=lambda x: x['route_dist'])
    nodes.extend(valid_stations)
    nodes.append({'id': 'finish', 'route_dist': true_total_miles, 'price': 0.0})
    
    # Dijkstra's Algorithm
    # dist[i] = min cost to reach node i
    n = len(nodes)
    min_cost = [float('inf')] * n
    min_cost[0] = 0.0
    parent = [-1] * n
    
    for i in range(n):
        if min_cost[i] == float('inf'):
            continue
            
        current_node = nodes[i]
        
        # We can travel to any upcoming node within MAX_RANGE_MILES
        for j in range(i + 1, n):
            target_node = nodes[j]
            drive_dist = target_node['route_dist'] - current_node['route_dist']
            
            if drive_dist > MAX_RANGE_MILES:
                break # Stations are sorted, so subsequent ones are also out of range
                
            # Cost = (distance / MPG) * price at CURRENT station
            # Note: For finish node, we just buy what's needed to reach it.
            cost = (drive_dist / MPG) * current_node['price']
            
            if min_cost[i] + cost < min_cost[j]:
                min_cost[j] = min_cost[i] + cost
                parent[j] = i
                
    if min_cost[-1] == float('inf'):
        # No valid path found
        return None, 0
        
    # Reconstruct path
    path = []
    curr = parent[-1] # skip 'finish' node itself in the stops list
    forward_target = n - 1
    
    while curr > 0: # skip 'start' node (0)
        drive_dist = nodes[forward_target]['route_dist'] - nodes[curr]['route_dist']
        gallons_purchased = drive_dist / MPG
        leg_cost = gallons_purchased * nodes[curr]['price']
        
        path.append({
            "stop_id": nodes[curr]['id'],
            "name": nodes[curr]['name'],
            "address": nodes[curr].get('address'),
            "city": nodes[curr].get('city'),
            "state": nodes[curr].get('state'),
            "route_dist": round(nodes[curr]['route_dist'], 2),
            "price_per_gal": nodes[curr]['price'],
            "gallons_purchased": round(gallons_purchased, 2),
            "leg_cost": round(leg_cost, 2),
            "coords": nodes[curr]['coords']
        })
        
        forward_target = curr
        curr = parent[curr]
        
    path.reverse()
    return path, min_cost[-1]
