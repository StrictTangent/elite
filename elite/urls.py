from django.urls import path
from . import views

app_name = 'elite'

urlpatterns = [
    path("", views.elite_main, name="elite_main"),


]
