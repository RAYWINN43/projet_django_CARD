"""
URL configuration for django_intro project.

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import path
from ehlo.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
    path("ehlo/", index, name='ehlo'),
]