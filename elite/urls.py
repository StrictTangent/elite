from django.urls import path
from . import views

app_name = 'elite'

urlpatterns = [
    path("", views.elite_main, name="elite_main"),
    path("importplanets/", views.import_planets, name="import_planets"),
    path("updateplanets/", views.update_planets, name="update_planets"),
    path("importprices/", views.import_prices, name="import_prices"),
    path("loaddatabase/", views.load_database, name="load_database"),
]
