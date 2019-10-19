"""Urls for the search app."""

from django.urls import path

from . import views

urlpatterns = [
    path('search', views.search, name='search'),
    path('resource-links', views.resource_links, name='resource_links'),
    path(
        'session-search-options', views.session_search_options,
        name='session_search_options'
    ),
]
