from django.urls import path
from . import views

app_name = 'operaciones'

urlpatterns = [
    path('deposito/', views.realizar_deposito, name='realizar_deposito'),
    path('retiro/', views.realizar_retiro, name='realizar_retiro'),
    path('transferencia/', views.realizar_transferencia, name='realizar_transferencia'),
    path('plazo/<int:cuenta_id>/cancelar/', views.cancelar_plazo_fijo, name='cancelar_plazo_fijo'),
    path('plazo/<int:cuenta_id>/renovar/', views.renovar_plazo_fijo, name='renovar_plazo_fijo'),
]