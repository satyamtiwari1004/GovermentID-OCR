from django.db import models
import os
from datetime import datetime

def passport_image_path(instance, filename):
    # Get the file extension
    ext = filename.split('.')[-1]
    # Generate a unique filename using timestamp
    filename = f"passport_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    return os.path.join('passports', filename)

# Create your models here.

class Passport(models.Model):
    image = models.ImageField(upload_to=passport_image_path)
    passport_number = models.CharField(max_length=50, blank=True)
    surname = models.CharField(max_length=100, blank=True)
    given_names = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    date_of_birth = models.CharField(max_length=50, blank=True)
    place_of_birth = models.CharField(max_length=100, blank=True)
    date_of_issue = models.CharField(max_length=50, blank=True)
    date_of_expiry = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Passport {self.passport_number} - {self.surname}"
