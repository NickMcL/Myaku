"""myakuweb root URL configuration."""
from django.urls import include, path

urlpatterns = [
    path('', include('search.urls')),
]
