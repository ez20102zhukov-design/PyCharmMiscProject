from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone

from ScriptsInfo.Parsing4gameinfo import steam_link_handler


# Create your models here.
class GameInfo(models.Model):
    title = models.CharField(max_length = 200)
    rating = models.IntegerField(default = 0)
    release = models.DateField(default = timezone.now())
    description = models.TextField()
    steam_url = models.URLField()
    image_url = models.ImageField(upload_to = 'images/')
    def __str__(self):
        return f"{steam_link_handler(self.steam_url)}, {self.title}"

class GameImages(models.Model):
    game = models.ForeignKey(GameInfo, on_delete = models.CASCADE)
    image = models.ImageField(upload_to = 'images/')

class Review(models.Model):
    game = models.ForeignKey(GameInfo, on_delete = models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.CASCADE)
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(validators = [MinValueValidator(1), MaxValueValidator(10)])
    created_at = models.DateTimeField(auto_now_add = True)
    class Meta:
        ordering = ['-created_at']
        models.UniqueConstraint(fields = ['game', 'user'], name = 'unique_review')
    def __str__(self):
        return f"{self.game} - {self.user} - {self.rating}"
