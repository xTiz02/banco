from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
  # Autenticación
  path('', views.login_view, name='login'),
  path('login/', views.login_view, name='login'),
  path('logout/', views.logout_view, name='logout'),

  # Dashboard
  path('dashboard/', views.dashboard, name='dashboard'),

  # Tipo de Cambio
  path('tipo-cambio/', views.configurar_tipo_cambio,
       name='configurar_tipo_cambio'),

  # Gestión de Usuarios (solo administradores)
  path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
  path('usuarios/crear/', views.crear_usuario, name='crear_usuario'),
  path('usuarios/<int:usuario_id>/editar/', views.editar_usuario,
       name='editar_usuario'),
  path('usuarios/<int:usuario_id>/inactivar/', views.inactivar_usuario,
       name='inactivar_usuario'),
  path('usuarios/<int:usuario_id>/desbloquear/', views.desbloquear_usuario,
       name='desbloquear_usuario'),
]