from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import logout
from django.contrib import messages
from datetime import timedelta


class SessionTimeoutMiddleware:
  """Middleware para manejar el timeout de sesión por inactividad"""

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    if request.user.is_authenticated:
      # Rutas excluidas del timeout
      excluded_paths = [
        reverse('core:logout'),
      ]

      if request.path not in excluded_paths:
        last_activity = request.session.get('last_activity')

        if last_activity:
          now = timezone.now().timestamp()
          # 60 segundos de inactividad (1 minuto)
          if now - last_activity > 60:
            logout(request)
            messages.warning(
                request,
                'Su sesión ha expirado por inactividad. Por favor, inicie sesión nuevamente.'
            )
            return redirect('core:login')

        # Actualizar última actividad
        request.session['last_activity'] = timezone.now().timestamp()

    response = self.get_response(request)
    return response


class LoginAttemptMiddleware:
  """Middleware para verificar intentos de login fallidos"""

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    # Este middleware solo verifica, la lógica de bloqueo está en las vistas
    response = self.get_response(request)
    return response


class TipoCambioMiddleware:
  """Middleware para verificar que el tipo de cambio esté configurado"""

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    if request.user.is_authenticated:
      # Rutas que requieren tipo de cambio configurado
      rutas_operaciones = [
        '/depositos/',
        '/retiros/',
        '/transferencias/',
        '/cuentas/apertura/',
      ]

      # Rutas excluidas
      rutas_excluidas = [
        '/admin/',
        '/tipo-cambio/',
        '/logout/',
        '/static/',
        '/media/',
      ]

      # Verificar si la ruta actual requiere tipo de cambio
      requiere_tc = any(
          request.path.startswith(ruta) for ruta in rutas_operaciones)
      esta_excluida = any(
          request.path.startswith(ruta) for ruta in rutas_excluidas)

      if requiere_tc and not esta_excluida:
        from core.models import TipoCambio
        if not TipoCambio.tipo_cambio_configurado_hoy():
          messages.error(
              request,
              'Debe configurar el tipo de cambio del día antes de realizar operaciones.'
          )
          return redirect('core:configurar_tipo_cambio')

    response = self.get_response(request)
    return response