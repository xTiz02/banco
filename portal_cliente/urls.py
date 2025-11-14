from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    # Autenticación
    path('', views.login_cliente, name='login'),
    path('login/', views.login_cliente, name='login'),
    path('registro/', views.registro_cliente, name='registro'),
    path('logout/', views.logout_cliente, name='logout'),

    # Recuperación de contraseña
    path('recuperar-password/', views.recuperar_password,
         name='recuperar_password'),
    path('cambiar-password/', views.cambiar_password, name='cambiar_password'),

    # Dashboard
    path('dashboard/', views.dashboard_cliente, name='dashboard'),
]