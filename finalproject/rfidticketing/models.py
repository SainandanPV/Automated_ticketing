from django.db import models
from django.contrib.auth.models import User
import requests
from decimal import Decimal

from django.conf import settings


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField(null=True)
    phone_number = models.CharField(max_length=10, null=True)

    def __str__(self):
        return self.user.username


class RFIDCard(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    uid = models.CharField(max_length=30, unique=True, null=True)  # UID for RFID card
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f'Card for {self.user.username}'


import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class RFIDCardLog(models.Model):
    rfid_card = models.ForeignKey(RFIDCard, on_delete=models.CASCADE)
    entry_timestamp = models.DateTimeField(auto_now_add=True)
    exit_timestamp = models.DateTimeField(null=True, blank=True)
    entry_latitude = models.FloatField(default=0.0)
    entry_longitude = models.FloatField(default=0.0)
    exit_latitude = models.FloatField(null=True, blank=True)
    exit_longitude = models.FloatField(null=True, blank=True)
    passenger_count = models.IntegerField(default=1)  # Add this line
    fare_deducted = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)


    def __str__(self):
        return f"Trip on {self.entry_timestamp} - {self.exit_timestamp or 'Ongoing'}"


    def calculate_distance(self):
        origin = f"{self.entry_latitude},{self.entry_longitude}"
        destination = f"{self.exit_latitude},{self.exit_longitude}"

        google_maps_api_key = settings.GOOGLE_MAPS_API_KEY
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&key={google_maps_api_key}"

        response = requests.get(url)
        directions_data = response.json()

        logger.info(f"Google Maps API Response: {directions_data}")  # Log the entire response

        if directions_data['status'] == 'OK':
            route = directions_data['routes'][0]
            leg = route['legs'][0]
            distance = leg['distance']['value']
            logger.info(f"Distance from API: {distance} meters")  # Log raw distance
            return distance / 1000  # Convert to kilometers
        else:
            logger.error(f"Error from Google Maps API: {directions_data.get('error_message', 'Unknown Error')}")
            return None
        



    

  
    def calculate_amount(self):
        distance = self.calculate_distance()
        logger.info(f"Calculated Distance: {distance} km")
        if distance:
            fare = Decimal(distance) * Decimal('1.25') * Decimal(self.passenger_count)  
            fare = fare.quantize(Decimal('0.01'))  # Rounds to 2 decimal places
            logger.info(f"Calculated Fare: {fare} INR")
            return fare
        return Decimal('0')



class Transaction(models.Model):
    rfid_card = models.ForeignKey('RFIDCard', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)


    
class RFIDLocation(models.Model):
    rfid_card = models.ForeignKey(RFIDCard, on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=15, decimal_places=9)
    longitude = models.DecimalField(max_digits=15, decimal_places=9)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Location for {self.rfid_card.uid} at {self.timestamp}"

