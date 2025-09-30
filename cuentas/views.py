from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from decimal import Decimal

from .models import Cuenta, Embargo
from .forms import CuentaForm, EmbargoForm, BuscarCuentaForm, CerrarCuentaForm
from clientes.models import Cliente
from operaciones.models import Movimiento


@login_required
def lista_cuentas(request):
  """Vista para listar cuentas"""
  cuentas = Cuenta.objects.select_related('cliente',
                                          'usuario_apertura').all().order_by(
    '-fecha_apertura')

  # Búsqueda
  form = BuscarCuentaForm(request.GET)
  if form.is_valid():
    busqueda = form.cleaned_data.get('busqueda')
    tipo_cuenta = form.cleaned_data.get('tipo_cuenta')
    estado = form.cleaned_data.get('estado')

    if busqueda:
      cuentas = cuentas.filter(
          Q(numero_cuenta__icontains=busqueda) |
          Q(cliente__codigo__icontains=busqueda) |
          Q(cliente__numero_documento__icontains=busqueda) |
          Q(cliente__nombres__icontains=busqueda) |
          Q(cliente__apellido_paterno__icontains=busqueda) |
          Q(cliente__razon_social__icontains=busqueda)
      )

    if tipo_cuenta:
      cuentas = cuentas.filter(tipo_cuenta=tipo_cuenta)

    if estado:
      cuentas = cuentas.filter(estado=estado)

  context = {
    'cuentas': cuentas,
    'form': form,
  }

  return render(request, 'cuentas/lista.html', context)


@login_required
def apertura_cuenta(request):
  """Vista para aperturar cuenta"""
  if request.method == 'POST':
    form = CuentaForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          cuenta = form.save(commit=False)
          cuenta.usuario_apertura = request.user
          cuenta.save()

          # Registrar movimiento de apertura
          Movimiento.objects.create(
              cuenta=cuenta,
              tipo_movimiento='APERTURA',
              monto=cuenta.saldo,
              saldo_anterior=Decimal('0.00'),
              saldo_nuevo=cuenta.saldo,
              descripcion=f'Apertura de {cuenta.get_tipo_cuenta_display()}',
              usuario=request.user
          )

          messages.success(
              request,
              f'Cuenta {cuenta.numero_cuenta} aperturada exitosamente para {cuenta.cliente.get_nombre_completo()}'
          )
          return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.id)

      except ValidationError as e:
        messages.error(request, f'Error al aperturar cuenta: {str(e)}')
      except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = CuentaForm()

  context = {
    'form': form,
    'accion': 'Aperturar',
  }

  return render(request, 'cuentas/form.html', context)


@login_required
def detalle_cuenta(request, cuenta_id):
  """Vista para ver detalles de la cuenta"""
  cuenta = get_object_or_404(
      Cuenta.objects.select_related('cliente', 'usuario_apertura'),
      pk=cuenta_id
  )

  # Últimos 20 movimientos
  movimientos = cuenta.movimientos.select_related('usuario').order_by(
    '-fecha_hora')[:20]

  # Embargos activos
  embargos_activos = cuenta.embargos.filter(esta_vigente=True).order_by(
    '-fecha_embargo')

  # Calcular saldo disponible
  saldo_disponible = cuenta.get_saldo_disponible()

  # Calcular interés si es cuenta a plazo
  interes_generado = None
  if cuenta.tipo_cuenta == 'PLAZO':
    interes_generado = cuenta.calcular_interes_generado()

  context = {
    'cuenta': cuenta,
    'movimientos': movimientos,
    'embargos_activos': embargos_activos,
    'saldo_disponible': saldo_disponible,
    'interes_generado': interes_generado,
  }

  return render(request, 'cuentas/detalle.html', context)


@login_required
def cerrar_cuenta(request, cuenta_id):
  """Vista para cerrar cuenta"""
  cuenta = get_object_or_404(Cuenta, pk=cuenta_id)

  if request.method == 'POST':
    form = CerrarCuentaForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          if not cuenta.puede_cerrarse():
            raise ValidationError(
              'La cuenta no puede cerrarse porque tiene saldo o embargos activos')

          cuenta.cerrar_cuenta()

          # Registrar movimiento de cierre
          Movimiento.objects.create(
              cuenta=cuenta,
              tipo_movimiento='CIERRE',
              monto=Decimal('0.00'),
              saldo_anterior=Decimal('0.00'),
              saldo_nuevo=Decimal('0.00'),
              descripcion='Cierre de cuenta',
              usuario=request.user
          )

          messages.success(request,
                           f'Cuenta {cuenta.numero_cuenta} cerrada exitosamente.')
          return redirect('cuentas:lista_cuentas')

      except ValidationError as e:
        messages.error(request, str(e))
      except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
    else:
      messages.error(request, 'Por favor confirme el cierre de la cuenta.')
  else:
    form = CerrarCuentaForm()

  context = {
    'cuenta': cuenta,
    'form': form,
  }

  return render(request, 'cuentas/cerrar.html', context)


@login_required
def inactivar_cuenta(request, cuenta_id):
  """Vista para inactivar/activar cuenta"""
  cuenta = get_object_or_404(Cuenta, pk=cuenta_id)

  if request.method == 'POST':
    try:
      if cuenta.esta_activa:
        cuenta.inactivar_cuenta()
        messages.success(request,
                         f'Cuenta {cuenta.numero_cuenta} inactivada exitosamente.')
      else:
        cuenta.activar_cuenta()
        messages.success(request,
                         f'Cuenta {cuenta.numero_cuenta} activada exitosamente.')
    except Exception as e:
      messages.error(request, f'Error: {str(e)}')

  return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.id)


@login_required
def registrar_embargo(request, cuenta_id):
  """Vista para registrar embargo judicial"""
  cuenta = get_object_or_404(Cuenta, pk=cuenta_id)

  if request.method == 'POST':
    form = EmbargoForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          embargo = form.save(commit=False)
          embargo.cuenta = cuenta
          embargo.usuario_registro = request.user

          # Validar que el monto no exceda el saldo
          if not embargo.es_total and embargo.monto_embargado > cuenta.saldo:
            raise ValidationError(
              'El monto del embargo no puede exceder el saldo de la cuenta')

          embargo.save()

          # Actualizar cuenta
          if embargo.es_total:
            cuenta.embargo_total = True
            cuenta.monto_embargado = cuenta.saldo
          else:
            cuenta.monto_embargado += embargo.monto_embargado

          cuenta.estado = 'EMBARGADA'
          cuenta.save()

          # Registrar movimiento
          Movimiento.objects.create(
              cuenta=cuenta,
              tipo_movimiento='EMBARGO',
              monto=embargo.monto_embargado,
              saldo_anterior=cuenta.saldo,
              saldo_nuevo=cuenta.saldo,
              descripcion=f'Embargo judicial - Oficio: {embargo.numero_oficio}',
              usuario=request.user
          )

          messages.success(
              request,
              f'Embargo registrado exitosamente. Oficio: {embargo.numero_oficio}'
          )
          return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.id)

      except ValidationError as e:
        messages.error(request, str(e))
      except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = EmbargoForm()

  context = {
    'form': form,
    'cuenta': cuenta,
  }

  return render(request, 'cuentas/embargo.html', context)


@login_required
def levantar_embargo(request, embargo_id):
  """Vista para levantar embargo"""
  embargo = get_object_or_404(Embargo, pk=embargo_id)

  if request.method == 'POST':
    try:
      with transaction.atomic():
        cuenta = embargo.cuenta

        embargo.levantar_embargo()

        # Registrar movimiento
        Movimiento.objects.create(
            cuenta=cuenta,
            tipo_movimiento='DESEMBARGO',
            monto=embargo.monto_embargado,
            saldo_anterior=cuenta.saldo,
            saldo_nuevo=cuenta.saldo,
            descripcion=f'Levantamiento de embargo - Oficio: {embargo.numero_oficio}',
            usuario=request.user
        )

        # Si no hay más embargos, cambiar estado
        if not cuenta.embargos.filter(esta_vigente=True).exists():
          cuenta.estado = 'ACTIVA'
          cuenta.save()

        messages.success(request,
                         f'Embargo levantado exitosamente. Oficio: {embargo.numero_oficio}')
        return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.cuenta.id)

    except Exception as e:
      messages.error(request, f'Error: {str(e)}')

  return redirect('cuentas:detalle_cuenta', cuenta_id=embargo.cuenta.id)


@login_required
def movimientos_cuenta(request, cuenta_id):
  """Vista para ver todos los movimientos de una cuenta"""
  cuenta = get_object_or_404(Cuenta, pk=cuenta_id)
  movimientos = cuenta.movimientos.select_related('usuario').order_by(
    '-fecha_hora')

  context = {
    'cuenta': cuenta,
    'movimientos': movimientos,
  }

  return render(request, 'cuentas/movimientos.html', context)


@login_required
def buscar_cuenta_ajax(request):
  """Vista AJAX para buscar cuentas"""
  from django.http import JsonResponse

  busqueda = request.GET.get('q', '')

  if len(busqueda) < 3:
    return JsonResponse({'cuentas': []})

  cuentas = Cuenta.objects.filter(
      Q(numero_cuenta__icontains=busqueda) |
      Q(cliente__codigo__icontains=busqueda) |
      Q(cliente__numero_documento__icontains=busqueda)
  ).filter(esta_activa=True).select_related('cliente')[:10]

  resultados = []
  for cuenta in cuentas:
    resultados.append({
      'id': cuenta.id,
      'numero_cuenta': cuenta.numero_cuenta,
      'tipo_cuenta': cuenta.get_tipo_cuenta_display(),
      'moneda': cuenta.get_moneda_display(),
      'saldo': str(cuenta.saldo),
      'cliente': cuenta.cliente.get_nombre_completo(),
      'saldo_disponible': str(cuenta.get_saldo_disponible()),
    })

  return JsonResponse({'cuentas': resultados})