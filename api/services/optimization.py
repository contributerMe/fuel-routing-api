import heapq
from api.models import FuelStation
from shapely.geometry import LineString, Point
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
    true_total_miles = total_distance_meters / 1609.34
    
    # Create Shapely LineString from route coordinates
    route_line = LineString(coords)
    
    # 1 degree of latitude/longitude is roughly 69 miles. 
    # Use Euclidean distance in degrees for fast geographic filtering
    search_radius_deg = SEARCH_RADIUS_MILES / 69.0
    
    valid_stations = []
    for station in candidates:
        station_point = Point(station.longitude, station.latitude)
        
        # Fast Euclidean distance in degrees
        min_dist_deg = route_line.distance(station_point)
        
        if min_dist_deg <= search_radius_deg:
            # Distance along the line to the closest point in Euclidean degrees
            proj_dist_deg = route_line.project(station_point)
            
            # Scale the degree projection to the true driving distance in miles
            best_route_dist = (proj_dist_deg / route_line.length) * true_total_miles
            
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
    import time  
    st = time.perf_counter()
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
    et = time.perf_counter()
    time_taken = et-st    
    path.reverse()
    return path, min_cost[-1]
