from django.db import models

class Worker(models.Model):

    class Status(models.TextChoices):
        UP = 'U', "Up"
        DOWN = 'D', "Down"

    status = models.CharField(max_length=1, choices=Status.choices,
                              default=Status.DOWN)
