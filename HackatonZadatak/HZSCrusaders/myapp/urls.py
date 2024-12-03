from django.urls import path
from . import views
from django.contrib import admin

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('custom-admin/', views.admin_login, name='admin_login'),
    path('custom-admin/verify-otp/', views.admin_verify_otp, name='admin_verify_otp'),
    path('custom-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('custom-admin/logout/', views.admin_logout, name='admin_logout'),
]
