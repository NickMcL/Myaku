"""Urls for the search app."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
]
