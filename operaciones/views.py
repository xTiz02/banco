from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

from .models import Deposito, Retiro, Transferencia, OperacionPlazoFijo, \
  Movimiento
from .forms import DepositoForm, RetiroForm, TransferenciaForm, \
  CancelarPlazoForm, RenovarPlazoForm
from cuentas.models import Cuenta
from core.models import TipoCambio


@login_required
def realizar_deposito(request):
  """Vista para realizar depósito"""
  if request.method == 'POST':
    form = DepositoForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          deposito = form.save(commit=False)
          deposito.usuario = request.user

          cuenta = deposito.cuenta

          # Verificar si la cuenta está activa
          if not cuenta.esta_activa or cuenta.estado == 'CERRADA':
            raise ValidationError(
              'No se pueden realizar depósitos en cuentas inactivas o cerradas')

          # Guardar depósito
          deposito.save()

          # Actualizar saldo de la cuenta
          saldo_anterior = cuenta.saldo
          cuenta.saldo += deposito.monto
          cuenta.actualizar_ultimo_movimiento()
          cuenta.save()

          # Registrar movimiento
          movimiento = Movimiento.objects.create(
              cuenta=cuenta,
              tipo_movimiento='DEPOSITO',
              monto=deposito.monto,
              saldo_anterior=saldo_anterior,
              saldo_nuevo=cuenta.saldo,
              descripcion=f'Depósito en {cuenta.get_tipo_cuenta_display()}',
              usuario=request.user,
              requiere_autorizacion=deposito.requiere_autorizacion,
              clave_autorizacion=deposito.clave_autorizacion,
              origen_fondos=deposito.origen_fondos
          )

          deposito.movimiento = movimiento
          deposito.save()

          messages.success(
              request,
              f'Depósito de {deposito.monto} {cuenta.get_moneda_display()} realizado exitosamente. '
              f'Nuevo saldo: {cuenta.saldo}'
          )
          return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.id)

      except ValidationError as e:
        messages.error(request, str(e))
      except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = DepositoForm()

  context = {
    'form': form,
    'operacion': 'Depósito',
  }

  return render(request, 'operaciones/deposito.html', context)


@login_required
def realizar_retiro(request):
  """Vista para realizar retiro"""
  if request.method == 'POST':
    form = RetiroForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          retiro = form.save(commit=False)
          retiro.usuario = request.user

          cuenta = retiro.cuenta

          # Verificar si la cuenta está activa
          if not cuenta.esta_activa or cuenta.estado == 'CERRADA':
            raise ValidationError(
              'No se pueden realizar retiros en cuentas inactivas o cerradas')

          # Verificar si puede retirar
          if not cuenta.puede_retirar(retiro.monto):
            raise ValidationError('Saldo insuficiente o cuenta embargada')

          # Guardar retiro
          retiro.save()

          # Actualizar saldo de la cuenta
          saldo_anterior = cuenta.saldo
          cuenta.saldo -= retiro.monto
          cuenta.actualizar_ultimo_movimiento()
          cuenta.save()

          # Registrar movimiento
          movimiento = Movimiento.objects.create(
              cuenta=cuenta,
              tipo_movimiento='RETIRO',
              monto=retiro.monto,
              saldo_anterior=saldo_anterior,
              saldo_nuevo=cuenta.saldo,
              descripcion=f'Retiro de {cuenta.get_tipo_cuenta_display()}',
              usuario=request.user
          )

          retiro.movimiento = movimiento
          retiro.save()

          messages.success(
              request,
              f'Retiro de {retiro.monto} {cuenta.get_moneda_display()} realizado exitosamente. '
              f'Nuevo saldo: {cuenta.saldo}'
          )
          return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.id)

      except ValidationError as e:
        messages.error(request, str(e))
      except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = RetiroForm()

  context = {
    'form': form,
    'operacion': 'Retiro',
  }

  return render(request, 'operaciones/retiro.html', context)


@login_required
def realizar_transferencia(request):
  """Vista para realizar transferencia entre cuentas"""
  if request.method == 'POST':
    form = TransferenciaForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          transferencia = form.save(commit=False)
          transferencia.usuario = request.user

          cuenta_origen = transferencia.cuenta_origen
          cuenta_destino = transferencia.cuenta_destino

          # Verificar que ambas cuentas estén activas
          if not cuenta_origen.esta_activa or cuenta_origen.estado == 'CERRADA':
            raise ValidationError('La cuenta origen no está activa')

          if not cuenta_destino.esta_activa or cuenta_destino.estado == 'CERRADA':
            raise ValidationError('La cuenta destino no está activa')

          # Verificar si puede retirar de origen
          if not cuenta_origen.puede_retirar(transferencia.monto_origen):
            raise ValidationError(
              'Saldo insuficiente en cuenta origen o cuenta embargada')

          # Calcular monto destino según moneda
          if cuenta_origen.moneda == cuenta_destino.moneda:
            transferencia.monto_destino = transferencia.monto_origen
          else:
            # Conversión de moneda
            tc = TipoCambio.obtener_actual()
            if not tc:
              raise ValidationError(
                'No se ha configurado el tipo de cambio del día')

            transferencia.tipo_cambio = tc.venta if cuenta_origen.moneda == 'SOLES' else tc.compra

            if cuenta_origen.moneda == 'SOLES':
              # Soles a Dólares
              transferencia.monto_destino = transferencia.monto_origen / tc.venta
            else:
              # Dólares a Soles
              transferencia.monto_destino = transferencia.monto_origen * tc.compra

            transferencia.monto_destino = transferencia.monto_destino.quantize(
              Decimal('0.01'))

          # Guardar transferencia
          transferencia.save()

          # Actualizar cuenta origen
          saldo_anterior_origen = cuenta_origen.saldo
          cuenta_origen.saldo -= transferencia.monto_origen
          cuenta_origen.actualizar_ultimo_movimiento()
          cuenta_origen.save()

          # Actualizar cuenta destino
          saldo_anterior_destino = cuenta_destino.saldo
          cuenta_destino.saldo += transferencia.monto_destino
          cuenta_destino.actualizar_ultimo_movimiento()
          cuenta_destino.save()

          # Registrar movimiento en cuenta origen
          movimiento_origen = Movimiento.objects.create(
              cuenta=cuenta_origen,
              tipo_movimiento='TRANSFERENCIA_ENVIADA',
              monto=transferencia.monto_origen,
              saldo_anterior=saldo_anterior_origen,
              saldo_nuevo=cuenta_origen.saldo,
              descripcion=f'Transferencia a cuenta {cuenta_destino.numero_cuenta}',
              usuario=request.user,
              cuenta_destino=cuenta_destino
          )

          # Registrar movimiento en cuenta destino
          movimiento_destino = Movimiento.objects.create(
              cuenta=cuenta_destino,
              tipo_movimiento='TRANSFERENCIA_RECIBIDA',
              monto=transferencia.monto_destino,
              saldo_anterior=saldo_anterior_destino,
              saldo_nuevo=cuenta_destino.saldo,
              descripcion=f'Transferencia desde cuenta {cuenta_origen.numero_cuenta}',
              usuario=request.user
          )

          transferencia.movimiento_origen = movimiento_origen
          transferencia.movimiento_destino = movimiento_destino
          transferencia.save()

          mensaje = f'Transferencia realizada exitosamente. '
          mensaje += f'Origen: {transferencia.monto_origen} {cuenta_origen.get_moneda_display()}, '
          mensaje += f'Destino: {transferencia.monto_destino} {cuenta_destino.get_moneda_display()}'

          messages.success(request, mensaje)
          return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta_origen.id)

      except ValidationError as e:
        messages.error(request, str(e))
      except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = TransferenciaForm()

  context = {
    'form': form,
    'operacion': 'Transferencia',
  }

  return render(request, 'operaciones/transferencia.html', context)


@login_required
def cancelar_plazo_fijo(request, cuenta_id):
  """Vista para cancelar cuenta a plazo fijo"""
  cuenta = get_object_or_404(Cuenta, pk=cuenta_id)

  if cuenta.tipo_cuenta != 'PLAZO':
    messages.error(request,
                   'Esta operación solo es válida para cuentas a plazo fijo')
    return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.id)

  # Calcular interés
  interes_generado = cuenta.calcular_interes_generado()
  monto_total = cuenta.saldo + interes_generado

  if request.method == 'POST':
    form = CancelarPlazoForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          # Registrar operación
          operacion = OperacionPlazoFijo.objects.create(
              cuenta=cuenta,
              tipo_operacion='CANCELACION',
              monto_principal=cuenta.saldo,
              interes_generado=interes_generado,
              monto_total=monto_total,
              usuario=request.user
          )

          # Registrar movimientos
          # 1. Movimiento de interés
          if interes_generado > 0:
            Movimiento.objects.create(
                cuenta=cuenta,
                tipo_movimiento='INTERES_PLAZO',
                monto=interes_generado,
                saldo_anterior=cuenta.saldo,
                saldo_nuevo=cuenta.saldo + interes_generado,
                descripcion=f'Interés generado por plazo fijo',
                usuario=request.user
            )

          # 2. Movimiento de cancelación
          Movimiento.objects.create(
              cuenta=cuenta,
              tipo_movimiento='CANCELACION_PLAZO',
              monto=monto_total,
              saldo_anterior=cuenta.saldo + interes_generado,
              saldo_nuevo=Decimal('0.00'),
              descripcion=f'Cancelación de plazo fijo',
              usuario=request.user
          )

          # Actualizar cuenta
          cuenta.saldo = Decimal('0.00')
          cuenta.cerrar_cuenta()

          messages.success(
              request,
              f'Plazo fijo cancelado exitosamente. '
              f'Principal: {operacion.monto_principal}, '
              f'Interés: {operacion.interes_generado}, '
              f'Total: {operacion.monto_total}'
          )
          return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.id)

      except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    else:
      messages.error(request, 'Por favor confirme la cancelación.')
  else:
    form = CancelarPlazoForm()

  context = {
    'form': form,
    'cuenta': cuenta,
    'interes_generado': interes_generado,
    'monto_total': monto_total,
  }

  return render(request, 'operaciones/cancelar_plazo.html', context)


@login_required
def renovar_plazo_fijo(request, cuenta_id):
  """Vista para renovar cuenta a plazo fijo"""
  cuenta = get_object_or_404(Cuenta, pk=cuenta_id)

  if cuenta.tipo_cuenta != 'PLAZO':
    messages.error(request,
                   'Esta operación solo es válida para cuentas a plazo fijo')
    return redirect('cuentas:detalle_cuenta', cuenta_id=cuenta.id)

  # Calcular interés
  interes_generado = cuenta.calcular_interes_generado()
  monto_total = cuenta.saldo + interes_generado

  if request.method == 'POST':
    form = RenovarPlazoForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          nuevo_plazo = form.cleaned_data['nuevo_plazo_meses']
          nueva_tasa = form.cleaned_data['nueva_tasa_interes']

          # Crear nueva cuenta a plazo
          nueva_cuenta = Cuenta.objects.create(
              cliente=cuenta.cliente,
              tipo_cuenta='PLAZO',
              moneda=cuenta.moneda,
              saldo=monto_total,
              monto_inicial=monto_total,
              plazo_meses=nuevo_plazo,
              tasa_interes_mensual=nueva_tasa,
              usuario_apertura=request.user
          )

          # Registrar operación
          operacion = OperacionPlazoFijo.objects.create(
              cuenta=cuenta,
              tipo_operacion='RENOVACION',
              monto_principal=cuenta.saldo,
              interes_generado=interes_generado,
              monto_total=monto_total,
              usuario=request.user,
              nueva_cuenta=nueva_cuenta,
              nuevo_plazo_meses=nuevo_plazo,
              nueva_tasa_interes=nueva_tasa
          )

          # Registrar movimiento de interés en cuenta antigua
          if interes_generado > 0:
            Movimiento.objects.create(
                cuenta=cuenta,
                tipo_movimiento='INTERES_PLAZO',
                monto=interes_generado,
                saldo_anterior=cuenta.saldo,
                saldo_nuevo=cuenta.saldo + interes_generado,
                descripcion=f'Interés generado por plazo fijo',
                usuario=request.user
            )

          # Registrar movimiento de renovación en cuenta antigua
          Movimiento.objects.create(
              cuenta=cuenta,
              tipo_movimiento='RENOVACION_PLAZO',
              monto=monto_total,
              saldo_anterior=cuenta.saldo + interes_generado,
              saldo_nuevo=Decimal('0.00'),
              descripcion=f'Renovación a nueva cuenta {nueva_cuenta.numero_cuenta}',
              usuario=request.user
          )

          # Registrar movimiento de apertura en cuenta nueva
          Movimiento.objects.create(
              cuenta=nueva_cuenta,
              tipo_movimiento='APERTURA',
              monto=monto_total,
              saldo_anterior=Decimal('0.00'),
              saldo_nuevo=monto_total,
              descripcion=f'Apertura por renovación desde cuenta {cuenta.numero_cuenta}',
              usuario=request.user
          )

          # Cerrar cuenta antigua
          cuenta.saldo = Decimal('0.00')
          cuenta.cerrar_cuenta()

          messages.success(
              request,
              f'Plazo fijo renovado exitosamente. Nueva cuenta: {nueva_cuenta.numero_cuenta}, '
              f'Monto: {nueva_cuenta.monto_inicial}, '
              f'Plazo: {nueva_cuenta.plazo_meses} meses, '
              f'Tasa: {nueva_cuenta.tasa_interes_mensual}%'
          )
          return redirect('cuentas:detalle_cuenta', cuenta_id=nueva_cuenta.id)

      except Exception as e:
        messages.error(request, f'Error: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = RenovarPlazoForm(initial={
      'nuevo_plazo_meses': cuenta.plazo_meses,
      'nueva_tasa_interes': cuenta.tasa_interes_mensual,
    })

  context = {
    'form': form,
    'cuenta': cuenta,
    'interes_generado': interes_generado,
    'monto_total': monto_total,
  }

  return render(request, 'operaciones/renovar_plazo.html', context)