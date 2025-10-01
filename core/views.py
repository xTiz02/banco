from django.shortcuts import render

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import timedelta

from .models import Usuario, TipoCambio, AuditoriaAcceso
from .forms import LoginForm, TipoCambioForm, UsuarioForm
from cuentas.models import Cuenta
from operaciones.models import Movimiento


def es_administrador(user):
  """Verifica si el usuario es administrador"""
  return user.is_authenticated and hasattr(user,
                                           'es_administrador') and user.es_administrador()


def registrar_auditoria(request, usuario, tipo_evento, exitoso=True,
    detalle=None):
  """Registra eventos de auditoría"""
  try:
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

    AuditoriaAcceso.objects.create(
        usuario=usuario,
        tipo_evento=tipo_evento,
        ip_address=ip_address,
        user_agent=user_agent,
        exitoso=exitoso,
        detalle=detalle
    )
  except Exception as e:
    pass  # No fallar si falla la auditoría


@require_http_methods(["GET", "POST"])
def login_view(request):
  """Vista de inicio de sesión"""
  if request.user.is_authenticated:
    return redirect('core:dashboard')


  if request.method == 'POST':
    form = LoginForm(request.POST)
    if form.is_valid():
      username = form.cleaned_data['username']
      password = form.cleaned_data['password']

      try:
        usuario = Usuario.objects.get(username=username)

        # Verificar si está bloqueado
        if usuario.bloqueado:
          messages.error(
              request,
              'Su cuenta está bloqueada por exceder los intentos de inicio de sesión. '
              'Contacte al administrador.'
          )
          registrar_auditoria(request, usuario, 'LOGIN_BLOQUEADO', False)
          return render(request, 'core/login.html', {'form': form})

        # Verificar si está activo
        if not usuario.esta_activo or not usuario.is_active:
          messages.error(request,
                         'Su cuenta está inactiva. Contacte al administrador.')
          registrar_auditoria(request, usuario, 'LOGIN_INACTIVO', False)
          return render(request, 'core/login.html', {'form': form})

        # Autenticar
        user = authenticate(request, username=username, password=password)

        if user is not None:
          # Login exitoso
          login(request, user)
          usuario.resetear_intentos_fallidos()
          request.session['last_activity'] = timezone.now().timestamp()

          registrar_auditoria(request, usuario, 'LOGIN_EXITOSO', True)
          messages.success(request,
                           f'Bienvenido {usuario.get_full_name() or usuario.username}')
          return redirect('core:dashboard')
        else:
          # Credenciales incorrectas
          usuario.incrementar_intentos_fallidos()
          intentos_restantes = 3 - usuario.intentos_fallidos

          if usuario.bloqueado:
            messages.error(
                request,
                'Su cuenta ha sido bloqueada por exceder los intentos de inicio de sesión.'
            )
          else:
            messages.error(
                request,
                f'Credenciales incorrectas. Le quedan {intentos_restantes} intentos.'
            )

          registrar_auditoria(request, usuario, 'LOGIN_FALLIDO', False)

      except Usuario.DoesNotExist:
        messages.error(request, 'Credenciales incorrectas.')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = LoginForm()

  return render(request, 'core/login.html', {'form': form})


@login_required
def logout_view(request):
  """Vista de cierre de sesión"""
  usuario = request.user
  registrar_auditoria(request, usuario, 'LOGOUT', True)
  logout(request)
  messages.success(request, 'Ha cerrado sesión correctamente.')
  return redirect('core:login')


@login_required
def dashboard(request):
  """Vista del dashboard principal"""
  usuario = request.user

  # Verificar que el tipo de cambio esté configurado
  tc_configurado = TipoCambio.tipo_cambio_configurado_hoy()
  tipo_cambio = TipoCambio.obtener_actual()

  # Estadísticas generales
  hoy = timezone.now().date()

  # Total de clientes
  from clientes.models import Cliente
  total_clientes = Cliente.objects.filter(esta_activo=True).count()

  # Total de cuentas activas
  total_cuentas = Cuenta.objects.filter(esta_activa=True).count()

  # Operaciones del día
  operaciones_hoy = Movimiento.objects.filter(
      fecha_hora__date=hoy
  ).count()

  # Monto total operado hoy en soles
  movimientos_hoy_soles = Movimiento.objects.filter(
      fecha_hora__date=hoy,
      cuenta__moneda='SOLES'
  ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

  movimientos_hoy_dolares = Movimiento.objects.filter(
      fecha_hora__date=hoy,
      cuenta__moneda='DOLARES'
  ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

  # Convertir dólares a soles
  if tipo_cambio:
    monto_total_hoy = movimientos_hoy_soles + (
          movimientos_hoy_dolares * tipo_cambio.venta)
  else:
    monto_total_hoy = movimientos_hoy_soles

  # Últimos movimientos (solo para visualización)
  ultimos_movimientos = Movimiento.objects.select_related(
      'cuenta', 'usuario'
  ).order_by('-fecha_hora')[:10]

  # Cuentas que requieren atención
  cuentas_embargadas = Cuenta.objects.filter(
      embargo_total=True,
      esta_activa=True
  ).count()

  cuentas_inactivas = Cuenta.objects.filter(
      estado='INACTIVA'
  ).count()

  context = {
    'usuario': usuario,
    'tc_configurado': tc_configurado,
    'tipo_cambio': tipo_cambio,
    'total_clientes': total_clientes,
    'total_cuentas': total_cuentas,
    'operaciones_hoy': operaciones_hoy,
    'monto_total_hoy': monto_total_hoy,
    'ultimos_movimientos': ultimos_movimientos,
    'cuentas_embargadas': cuentas_embargadas,
    'cuentas_inactivas': cuentas_inactivas,
  }

  return render(request, 'core/dashboard.html', context)


@login_required
@user_passes_test(es_administrador, login_url='core:dashboard')
def configurar_tipo_cambio(request):
  """Vista para configurar el tipo de cambio diario"""
  hoy = timezone.now().date()
  tipo_cambio_existente = TipoCambio.objects.filter(fecha=hoy).first()

  if request.method == 'POST':
    form = TipoCambioForm(request.POST, instance=tipo_cambio_existente)
    if form.is_valid():
      try:
        tipo_cambio = form.save(commit=False)
        tipo_cambio.fecha = hoy
        tipo_cambio.usuario_registro = request.user
        tipo_cambio.save()

        messages.success(
            request,
            f'Tipo de cambio configurado: Compra {tipo_cambio.compra} - Venta {tipo_cambio.venta}'
        )
        return redirect('core:dashboard')
      except Exception as e:
        messages.error(request, f'Error al guardar tipo de cambio: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = TipoCambioForm(instance=tipo_cambio_existente)

  context = {
    'form': form,
    'tipo_cambio_existente': tipo_cambio_existente,
    'fecha': hoy,
  }

  return render(request, 'core/tipo_cambio.html', context)


@login_required
@user_passes_test(es_administrador, login_url='core:dashboard')
def lista_usuarios(request):
  """Vista para listar usuarios"""
  usuarios = Usuario.objects.all().order_by('-fecha_creacion')

  context = {
    'usuarios': usuarios,
  }

  return render(request, 'core/usuarios/lista.html', context)


@login_required
@user_passes_test(es_administrador, login_url='core:dashboard')
def crear_usuario(request):
  """Vista para crear usuario"""
  if request.method == 'POST':
    form = UsuarioForm(request.POST)
    if form.is_valid():
      try:
        usuario = form.save(commit=False)
        usuario.set_password(form.cleaned_data['password'])
        usuario.save()

        registrar_auditoria(
            request,
            request.user,
            'CREAR_USUARIO',
            True,
            f'Usuario creado: {usuario.username}'
        )

        messages.success(request,
                         f'Usuario {usuario.username} creado exitosamente.')
        return redirect('core:lista_usuarios')
      except Exception as e:
        messages.error(request, f'Error al crear usuario: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = UsuarioForm()

  context = {
    'form': form,
    'accion': 'Crear',
  }

  return render(request, 'core/usuarios/form.html', context)


@login_required
@user_passes_test(es_administrador, login_url='core:dashboard')
def editar_usuario(request, usuario_id):
  """Vista para editar usuario"""
  try:
    usuario = Usuario.objects.get(pk=usuario_id)
  except Usuario.DoesNotExist:
    messages.error(request, 'Usuario no encontrado.')
    return redirect('core:lista_usuarios')

  if request.method == 'POST':
    form = UsuarioForm(request.POST, instance=usuario)
    if form.is_valid():
      try:
        usuario = form.save(commit=False)

        # Solo actualizar contraseña si se proporcionó una nueva
        nueva_password = form.cleaned_data.get('password')
        if nueva_password:
          usuario.set_password(nueva_password)

        usuario.save()

        registrar_auditoria(
            request,
            request.user,
            'EDITAR_USUARIO',
            True,
            f'Usuario editado: {usuario.username}'
        )

        messages.success(request,
                         f'Usuario {usuario.username} actualizado exitosamente.')
        return redirect('core:lista_usuarios')
      except Exception as e:
        messages.error(request, f'Error al actualizar usuario: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = UsuarioForm(instance=usuario, edicion=True)

  context = {
    'form': form,
    'usuario': usuario,
    'accion': 'Editar',
  }

  return render(request, 'core/usuarios/form.html', context)


@login_required
@user_passes_test(es_administrador, login_url='core:dashboard')
def inactivar_usuario(request, usuario_id):
  """Vista para inactivar/activar usuario"""
  try:
    usuario = Usuario.objects.get(pk=usuario_id)

    if usuario == request.user:
      messages.error(request, 'No puede inactivar su propia cuenta.')
      return redirect('core:lista_usuarios')

    if request.method == 'POST':
      usuario.esta_activo = not usuario.esta_activo
      usuario.is_active = usuario.esta_activo
      usuario.save()

      accion = 'activado' if usuario.esta_activo else 'inactivado'
      registrar_auditoria(
          request,
          request.user,
          'CAMBIAR_ESTADO_USUARIO',
          True,
          f'Usuario {accion}: {usuario.username}'
      )

      messages.success(request,
                       f'Usuario {usuario.username} {accion} exitosamente.')
      return redirect('core:lista_usuarios')

  except Usuario.DoesNotExist:
    messages.error(request, 'Usuario no encontrado.')

  return redirect('core:lista_usuarios')


@login_required
@user_passes_test(es_administrador, login_url='core:dashboard')
def desbloquear_usuario(request, usuario_id):
  """Vista para desbloquear usuario"""
  try:
    usuario = Usuario.objects.get(pk=usuario_id)

    if request.method == 'POST':
      usuario.desbloquear()

      registrar_auditoria(
          request,
          request.user,
          'DESBLOQUEAR_USUARIO',
          True,
          f'Usuario desbloqueado: {usuario.username}'
      )

      messages.success(request,
                       f'Usuario {usuario.username} desbloqueado exitosamente.')
      return redirect('core:lista_usuarios')

  except Usuario.DoesNotExist:
    messages.error(request, 'Usuario no encontrado.')

  return redirect('core:lista_usuarios')