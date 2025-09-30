from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path('resumen-dia/', views.resumen_operaciones_dia, name='resumen_operaciones_dia'),
    path('consultar-movimientos/', views.consultar_movimientos, name='consultar_movimientos'),
]