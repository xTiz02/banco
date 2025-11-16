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
    path('recuperar-password/', views.recuperar_password, name='recuperar_password'),
    path('cambiar-password/', views.cambiar_password, name='cambiar_password'),

    # Dashboard
    path('dashboard/', views.dashboard_cliente, name='dashboard'),

    # Mis Cuentas
    path('mis-cuentas/', views.mis_cuentas, name='mis_cuentas'),
    path('cuenta/<int:cuenta_id>/', views.detalle_cuenta_cliente, name='detalle_cuenta_cliente'),

    # Operaciones Bancarias
    path('apertura-cuenta/', views.apertura_cuenta_cliente, name='apertura_cuenta'),
    path('deposito/', views.deposito_cliente, name='deposito'),
    path('retiro/', views.retiro_cliente, name='retiro'),
    path('transferencia/', views.transferencia_cliente, name='transferencia'),

    # Cierre y Operaciones de Plazo
    path('cerrar-cuenta/<int:cuenta_id>/', views.cerrar_cuenta, name='cerrar_cuenta'),
    path('operacion-plazo/<int:cuenta_id>/', views.operacion_plazo, name='operacion_plazo'),
]