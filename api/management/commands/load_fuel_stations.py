import csv
from django.core.management.base import BaseCommand
from api.models import FuelStation

class Command(BaseCommand):
    help = 'Loads geocoded fuel stations from CSV into the database'

    def handle(self, *args, **kwargs):
        csv_path = 'fuel_prices_geocoded.csv'
        self.stdout.write(f'Loading data from {csv_path}...')

        count = 0
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    opis_id = int(row['OPIS Truckstop ID'])
                    rack_id = int(row['Rack ID']) if row['Rack ID'] else None
                    
                    FuelStation.objects.update_or_create(
                        opis_id=opis_id,
                        defaults={
                            'name': row['Truckstop Name'],
                            'address': row['Address'],
                            'city': row['City'],
                            'state': row['State'],
                            'rack_id': rack_id,
                            'retail_price': float(row['Retail Price']),
                            'latitude': float(row['Latitude']),
                            'longitude': float(row['Longitude'])
                        }
                    )
                    count += 1
                except Exception as e:
                    self.stderr.write(f"Error loading row {row['OPIS Truckstop ID']}: {e}")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully loaded {count} fuel stations into the database.'))
