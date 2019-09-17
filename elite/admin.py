from django.contrib import admin
from .models import Planet, Price, System

# Register your models here.
admin.site.register(Planet)
admin.site.register(Price)
admin.site.register(System)
