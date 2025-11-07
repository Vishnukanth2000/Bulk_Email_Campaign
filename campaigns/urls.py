# campaigns/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.campaign_dashboard, name='campaign_dashboard'),
    path('campaign/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaign/create/', views.campaign_create, name='campaign_create'),
    path('recipients/upload/', views.recipient_upload, name='recipient_upload'),
]