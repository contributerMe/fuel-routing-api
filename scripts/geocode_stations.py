import csv
import concurrent.futures
from geopy.geocoders import ArcGIS
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

INPUT_CSV = 'fuel-prices-for-be-assessment.csv'
OUTPUT_CSV = 'fuel_prices_geocoded.csv'

def geocode_single_station(row):
    geolocator = ArcGIS(timeout=10)
    # Use the Truckstop Name, City, and State for a smart POI search
    query = f"{row['Truckstop Name']}, {row['City']}, {row['State']}"
    
    try:
        location = geolocator.geocode(query)
        if location:
            row['Latitude'] = location.latitude
            row['Longitude'] = location.longitude
            return row
    except (GeocoderTimedOut, GeocoderServiceError):
        pass
        
    # Fallback to Address, City, State if the name search fails
    query_fallback = f"{row['Address']}, {row['City']}, {row['State']}"
    try:
        location = geolocator.geocode(query_fallback)
        if location:
            row['Latitude'] = location.latitude
            row['Longitude'] = location.longitude
            return row
    except (GeocoderTimedOut, GeocoderServiceError):
        pass

    return None

def main():
    print("Reading input CSV...")
    stations = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stations.append(row)
            
    print(f"Loaded {len(stations)} stations. Starting Geocoding via ArcGIS...")
    
    successful_rows = []
    
    # We use 10 workers to speed up the 8,000 network requests without overwhelming the API
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Map the function over the stations
        futures = {executor.submit(geocode_single_station, row): row for row in stations}
        
        count = 0
        for future in concurrent.futures.as_completed(futures):
            count += 1
            if count % 500 == 0:
                print(f"Processed {count} / {len(stations)} stations...")
                
            result = future.result()
            if result:
                successful_rows.append(result)
                
    print(f"Successfully geocoded {len(successful_rows)} out of {len(stations)} stations.")
    
    if not successful_rows:
        print("No stations were geocoded.")
        return
        
    print("Writing output CSV...")
    with open(OUTPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        fieldnames = list(successful_rows[0].keys())
        # Ensure Latitude and Longitude are at the end if they weren't already
        if 'Latitude' not in fieldnames:
            fieldnames.extend(['Latitude', 'Longitude'])
            
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in successful_rows:
            writer.writerow(row)
            
    print("Done!")

if __name__ == '__main__':
    main()
