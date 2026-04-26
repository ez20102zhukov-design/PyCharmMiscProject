from django.db import models
from django.utils import timezone


# Create your models here.
class GameInfo(models.Model):
    title = models.CharField(max_length = 200)
    rating = models.IntegerField(default = 0)
    release = models.DateField(default = timezone.now())
    description = models.TextField()
    steam_url = models.URLField()
    image_url = models.ImageField(upload_to = 'images/')
