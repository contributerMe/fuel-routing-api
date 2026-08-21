from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from api.models import FuelStation

class FuelStationModelTest(TestCase):
    def setUp(self):
        self.station = FuelStation.objects.create(
            opis_id=12345,
            name="Test Station",
            address="123 Test St",
            city="Testville",
            state="TX",
            retail_price=2.50,
            latitude=30.0,
            longitude=-90.0
        )

    def test_fuel_station_str(self):
        self.assertEqual(str(self.station), "Test Station - Testville, TX")


class RouteAPIViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('route_api')

    @patch('api.views.geocode_address')
    @patch('api.views.get_route')
    @patch('api.views.get_optimal_fuel_stops')
    def test_valid_route_request(self, mock_get_stops, mock_get_route, mock_geocode):
        # Mock geocoding responses
        # start_lon, start_lat
        mock_geocode.side_effect = [(-90.0, 30.0), (-91.0, 31.0)]
        
        # Mock route response: geometry, dist_meters
        mock_get_route.return_value = ({"type": "LineString", "coordinates": [[-90.0, 30.0], [-91.0, 31.0]]}, 160934) # 100 miles
        
        # Mock optimal stops: stops, cost
        mock_get_stops.return_value = ([{
            "stop_id": 1,
            "name": "Station A",
            "route_dist": 50.0,
            "price_per_gal": 2.0,
            "gallons_purchased": 5.0,
            "leg_cost": 10.0
        }], 20.0)

        response = self.client.get(self.url, {'start': 'City A, TX', 'finish': 'City B, TX'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('route_geometry', response.data)
        self.assertIn('total_distance_miles', response.data)
        self.assertIn('total_fuel_cost', response.data)
        self.assertIn('fuel_stops', response.data)
        self.assertEqual(response.data['total_distance_miles'], 100.0)
        self.assertEqual(response.data['total_fuel_cost'], 20.0)

    def test_missing_parameters(self):
        response = self.client.get(self.url, {'start': 'City A, TX'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], "Please provide both 'start' and 'finish' query parameters.")

    @patch('api.views.geocode_address')
    def test_invalid_start_address(self, mock_geocode):
        mock_geocode.return_value = (None, None)
        response = self.client.get(self.url, {'start': 'Invalid City', 'finish': 'City B, TX'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Could not geocode start address", response.data['error'])

    @patch('api.views.geocode_address')
    @patch('api.views.get_route')
    def test_no_route_found(self, mock_get_route, mock_geocode):
        mock_geocode.side_effect = [(-90.0, 30.0), (-91.0, 31.0)]
        mock_get_route.return_value = (None, 0)
        
        response = self.client.get(self.url, {'start': 'City A, TX', 'finish': 'Ocean, TX'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Could not find a route", response.data['error'])

    @patch('api.views.geocode_address')
    @patch('api.views.get_route')
    @patch('api.views.get_optimal_fuel_stops')
    def test_no_valid_fuel_stops(self, mock_get_stops, mock_get_route, mock_geocode):
        mock_geocode.side_effect = [(-90.0, 30.0), (-91.0, 31.0)]
        mock_get_route.return_value = ({"type": "LineString", "coordinates": [[-90.0, 30.0], [-91.0, 31.0]]}, 160934)
        mock_get_stops.return_value = (None, 0)
        
        response = self.client.get(self.url, {'start': 'City A, TX', 'finish': 'City B, TX'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Could not find a sequence of fuel stops", response.data['error'])
