import concurrent.futures
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from api.services.geocoding import geocode_address
from api.services.routing import get_route
from api.services.optimization import get_optimal_fuel_stops

class RouteAPIView(APIView):
    
    @extend_schema(
        parameters=[
            OpenApiParameter(name='start', description='Starting location (e.g., "Los Angeles, CA")', required=True, type=OpenApiTypes.STR),
            OpenApiParameter(name='finish', description='Ending location (e.g., "New York, NY")', required=True, type=OpenApiTypes.STR),
        ],
        description="Calculates the optimal route and fuel stops between two locations in the USA.",
    )
    @method_decorator(cache_page(60 * 60 * 24)) # Cache identical requests for 24 hours
    def get(self, request):
        start_str = request.query_params.get('start')
        finish_str = request.query_params.get('finish')
        
        if not start_str or not finish_str:
            return Response({"error": "Please provide both 'start' and 'finish' query parameters."}, status=status.HTTP_400_BAD_REQUEST)
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_start = executor.submit(geocode_address, start_str)
            future_finish = executor.submit(geocode_address, finish_str)
            
            start_lon, start_lat = future_start.result()
            finish_lon, finish_lat = future_finish.result()

        if start_lon is None:
            return Response({"error": f"Could not geocode start address: {start_str}"}, status=status.HTTP_400_BAD_REQUEST)
            
        if finish_lon is None:
            return Response({"error": f"Could not geocode finish address: {finish_str}"}, status=status.HTTP_400_BAD_REQUEST)
            
        geometry, dist_meters = get_route((start_lon, start_lat), (finish_lon, finish_lat))
        if geometry is None:
            return Response({"error": "Could not find a route between the given locations."}, status=status.HTTP_400_BAD_REQUEST)
            
        stops, cost = get_optimal_fuel_stops(geometry, dist_meters)
        if stops is None:
            return Response({"error": "Could not find a sequence of fuel stops to complete this route within the 500-mile vehicle range constraint."}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response({
            "route_geometry": geometry,
            "total_distance_miles": dist_meters / 1609.34,
            "total_fuel_cost": round(cost, 2),
            "fuel_stops": stops
        })

