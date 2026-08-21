from django.db import models

class FuelStation(models.Model):
    opis_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField(null=True, blank=True)
    retail_price = models.FloatField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"

    class Meta:
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
        ]

