"""myakuweb root URL configuration."""
from django.urls import include, path

urlpatterns = [
    path('api/', include('search.urls')),
]
