import requests

def get_route(start_coords, end_coords):
    """
    coords should be (lon, lat) tuples.
    Returns GeoJSON LineString geometry and total distance in meters.
    """
    start_lon, start_lat = start_coords
    end_lon, end_lat = end_coords
    
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}?overview=simplified&geometries=geojson"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    if data.get('code') != 'Ok' or not data.get('routes'):
        return None, 0
        
    route = data['routes'][0]
    geometry = route['geometry'] # dict with type: LineString, coordinates: [[lon, lat], ...]
    distance = route['distance'] # meters
    
    return geometry, distance
