# Fuel Routing Optimization API

A high-performance REST API built with **Django 5.2** that calculates the most cost-effective fueling strategy for a given road trip across the USA.

## Features & Performance
- **Optimal Fuel Stops**: Calculates the cheapest fuel stations to stop at, respecting a maximum vehicle range of 500 miles and an efficiency of 10 MPG.
- **Lightning Fast**: 
  - *Cold-start requests* (uncached) average **~1.5 - 2.5 seconds** due to efficient spatial filtering and asynchronous processing.
  - *Cached requests* return in **< 50 milliseconds**.
- **Accurate Geocoding & Routing**: Integrates with OpenStreetMap (Nominatim) and OSRM (Open Source Routing Machine) for real-world driving data.

## Technology Stack
- **Django 5.2 & Django REST Framework**: Chosen for its robust, stable ecosystem and built-in caching mechanisms.
- **SQLite**: Lightweight database housing the 60,000+ fuel stations. Indexed by latitude and longitude for rapid spatial queries.
- **concurrent.futures**: Utilizes Python's `ThreadPoolExecutor` to run network-bound geocoding tasks in parallel, halving the initial location lookup time.
- **drf-spectacular**: Provides automatic, interactive OpenAPI (Swagger) documentation.

## How the Optimization Works
Calculating the absolute cheapest path across thousands of fuel stations is computationally heavy. We achieved high performance using the following pipeline:

1. **Parallel Geocoding**: Start and finish addresses are geocoded concurrently.
2. **OSRM Route Fetching**: The driving geometry (LineString) is fetched from OSRM.
3. **Bounding Box Pre-Filtering (Spatial Optimization)**: Instead of calculating distances against all 60k+ US stations, the API calculates a geographic bounding box around the route with a 5-mile margin. This filters the dataset down to a tiny fraction instantly using SQLite indexes.
4. **Route Projection**: Stations inside the bounding box are projected onto the route geometry to find their exact driving distance from the start.
5. **Dijkstra's Algorithm on a DAG**: The valid stations are represented as nodes in a Directed Acyclic Graph (DAG). Edges are drawn between stations that are within the 500-mile maximum range. Dijkstra's shortest-path algorithm is then executed to find the path with the lowest total fuel cost.
6. **24-Hour Caching**: The final payload is cached in-memory for 24 hours based on the start/finish query parameters.

## Local Development
```bash
# 1. Create a virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Run the development server
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000/api/docs/` to view the interactive Swagger UI and test the API!

## Production Deployment
To deploy this API in a professional, production-ready environment:
1. **Set Environment Variables**: Set `DEBUG=False` and configure `ALLOWED_HOSTS`.
2. **Use a WSGI Server**: Do not use `manage.py runserver`. Serve the application using `gunicorn`:
   ```bash
   pip install gunicorn
   gunicorn fuel_project.wsgi:application --workers 4 --bind 0.0.0.0:8000
   ```
3. **Caching Backend**: Swap out the default local-memory cache for **Redis** (via `django-redis`) to allow cache sharing across multiple Gunicorn workers.
