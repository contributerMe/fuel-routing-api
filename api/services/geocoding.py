from geopy.geocoders import Nominatim

def geocode_address(address_str):
    """Geocode a string address into lat, lon using Nominatim."""
    geolocator = Nominatim(user_agent="fuel_route_app")
    location = geolocator.geocode(address_str, country_codes='us')
    if location:
        return location.longitude, location.latitude
    return None, None
