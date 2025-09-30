from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from operaciones.models import Movimiento
from cuentas.models import Cuenta
from clientes.models import Cliente
from core.models import TipoCambio


@login_required
def resumen_operaciones_dia(request):
  """Vista para mostrar el resumen de operaciones del día"""
  hoy = timezone.now().date()

  # Obtener tipo de cambio del día
  tipo_cambio = TipoCambio.obtener_actual()

  # Movimientos del día
  movimientos_hoy = Movimiento.objects.filter(
      fecha_hora__date=hoy
  ).select_related('cuenta', 'usuario')

  # Estadísticas generales
  total_operaciones = movimientos_hoy.count()

  # Depósitos
  depositos_soles = movimientos_hoy.filter(
      tipo_movimiento='DEPOSITO',
      cuenta__moneda='SOLES'
  ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

  depositos_dolares = movimientos_hoy.filter(
      tipo_movimiento='DEPOSITO',
      cuenta__moneda='DOLARES'
  ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

  cantidad_depositos = movimientos_hoy.filter(
    tipo_movimiento='DEPOSITO').count()

  # Retiros
  retiros_soles = movimientos_hoy.filter(
      tipo_movimiento='RETIRO',
      cuenta__moneda='SOLES'
  ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

  retiros_dolares = movimientos_hoy.filter(
      tipo_movimiento='RETIRO',
      cuenta__moneda='DOLARES'
  ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

  cantidad_retiros = movimientos_hoy.filter(tipo_movimiento='RETIRO').count()

  # Transferencias
  transferencias_enviadas = movimientos_hoy.filter(
      tipo_movimiento='TRANSFERENCIA_ENVIADA'
  ).count()

  transferencias_recibidas = movimientos_hoy.filter(
      tipo_movimiento='TRANSFERENCIA_RECIBIDA'
  ).count()

  cantidad_transferencias = transferencias_enviadas  # Solo contar las enviadas para no duplicar

  # Aperturas de cuenta
  aperturas_hoy = movimientos_hoy.filter(tipo_movimiento='APERTURA').count()

  # Cierres de cuenta
  cierres_hoy = movimientos_hoy.filter(tipo_movimiento='CIERRE').count()

  # Embargos y desembargos
  embargos_hoy = movimientos_hoy.filter(tipo_movimiento='EMBARGO').count()
  desembargos_hoy = movimientos_hoy.filter(tipo_movimiento='DESEMBARGO').count()

  # Operaciones de plazo fijo
  cancelaciones_plazo = movimientos_hoy.filter(
    tipo_movimiento='CANCELACION_PLAZO').count()
  renovaciones_plazo = movimientos_hoy.filter(
    tipo_movimiento='RENOVACION_PLAZO').count()

  # Convertir todo a soles para totales
  if tipo_cambio:
    depositos_total_soles = depositos_soles + (
          depositos_dolares * tipo_cambio.venta)
    retiros_total_soles = retiros_soles + (retiros_dolares * tipo_cambio.venta)
  else:
    depositos_total_soles = depositos_soles
    retiros_total_soles = retiros_soles

  # Operaciones por usuario
  operaciones_por_usuario = movimientos_hoy.values(
      'usuario__username',
      'usuario__first_name',
      'usuario__last_name'
  ).annotate(
      cantidad=Count('id')
  ).order_by('-cantidad')

  # Operaciones por tipo
  operaciones_por_tipo = movimientos_hoy.values(
      'tipo_movimiento'
  ).annotate(
      cantidad=Count('id')
  ).order_by('-cantidad')

  # Últimas operaciones
  ultimas_operaciones = movimientos_hoy.order_by('-fecha_hora')[:20]

  context = {
    'fecha': hoy,
    'tipo_cambio': tipo_cambio,
    'total_operaciones': total_operaciones,
    'depositos_soles': depositos_soles,
    'depositos_dolares': depositos_dolares,
    'depositos_total_soles': depositos_total_soles,
    'cantidad_depositos': cantidad_depositos,
    'retiros_soles': retiros_soles,
    'retiros_dolares': retiros_dolares,
    'retiros_total_soles': retiros_total_soles,
    'cantidad_retiros': cantidad_retiros,
    'cantidad_transferencias': cantidad_transferencias,
    'aperturas_hoy': aperturas_hoy,
    'cierres_hoy': cierres_hoy,
    'embargos_hoy': embargos_hoy,
    'desembargos_hoy': desembargos_hoy,
    'cancelaciones_plazo': cancelaciones_plazo,
    'renovaciones_plazo': renovaciones_plazo,
    'operaciones_por_usuario': operaciones_por_usuario,
    'operaciones_por_tipo': operaciones_por_tipo,
    'ultimas_operaciones': ultimas_operaciones,
  }

  return render(request, 'reportes/resumen_dia.html', context)


@login_required
def consultar_movimientos(request):
  """Vista para consultar movimientos de una cuenta específica"""
  from cuentas.forms import BuscarCuentaForm

  cuenta = None
  movimientos = None

  if request.GET.get('cuenta_id'):
    from cuentas.models import Cuenta
    cuenta_id = request.GET.get('cuenta_id')
    try:
      cuenta = Cuenta.objects.get(pk=cuenta_id)
      # Obtener últimos 20 movimientos
      movimientos = cuenta.movimientos.select_related('usuario').order_by(
        '-fecha_hora')[:20]
    except Cuenta.DoesNotExist:
      from django.contrib import messages
      messages.error(request, 'Cuenta no encontrada')

  context = {
    'cuenta': cuenta,
    'movimientos': movimientos,
  }

  return render(request, 'reportes/consultar_movimientos.html', context)