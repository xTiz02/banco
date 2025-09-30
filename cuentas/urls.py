from django.urls import path
from . import views

app_name = 'cuentas'

urlpatterns = [
    path('', views.lista_cuentas, name='lista_cuentas'),
    path('apertura/', views.apertura_cuenta, name='apertura_cuenta'),
    path('<int:cuenta_id>/', views.detalle_cuenta, name='detalle_cuenta'),
    path('<int:cuenta_id>/cerrar/', views.cerrar_cuenta, name='cerrar_cuenta'),
    path('<int:cuenta_id>/inactivar/', views.inactivar_cuenta, name='inactivar_cuenta'),
    path('<int:cuenta_id>/movimientos/', views.movimientos_cuenta, name='movimientos_cuenta'),
    path('<int:cuenta_id>/embargo/', views.registrar_embargo, name='registrar_embargo'),
    path('embargo/<int:embargo_id>/levantar/', views.levantar_embargo, name='levantar_embargo'),
    path('buscar/', views.buscar_cuenta_ajax, name='buscar_cuenta_ajax'),
]