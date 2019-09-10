from django.db import models

class Planet(models.Model):
    name = models.TextField()
    distanceToArrival = models.IntegerField()
    #hasIcy = models.BooleanField()
    systemName = models.TextField()

    def __str__(self):
        return self.name

class Price(models.Model):
    system_id = models.IntegerField()
    station_id = models.IntegerField()
    systemName = models.TextField()
    station_name = models.TextField()
    sell_price = models.IntegerField()
    max_landing_pad_size = models.TextField()
    distance_to_star = models.IntegerField()

    def __str__(self):             
        return self.station_name
