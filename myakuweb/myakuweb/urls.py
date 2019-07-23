"""myakuweb root URL Configuration"""
from django.urls import include, path

urlpatterns = [
    path('', include('search.urls')),
]
