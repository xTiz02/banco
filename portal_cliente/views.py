from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from clientes.models import Cliente, UsuarioCliente
from cuentas.models import Cuenta
from operaciones.models import Movimiento, Deposito, Retiro, Transferencia, OperacionPlazoFijo
from core.models import TipoCambio, Usuario
from .forms import (
    RegistroClienteForm, LoginClienteForm,
    RecuperarPasswordForm, CambiarPasswordForm,
    AperturaCuentaClienteForm, DepositoClienteForm,
    RetiroClienteForm, TransferenciaClienteForm,
    CerrarCuentaForm, OperacionPlazoForm
)


def login_required_cliente(view_func):
    """Decorador personalizado para verificar autenticación de cliente"""

    def wrapper(request, *args, **kwargs):
        if not request.session.get('cliente_id'):
            messages.warning(request, 'Debe iniciar sesión para acceder')
            return redirect('portal:login')

        # Verificar timeout de sesión
        last_activity = request.session.get('last_activity_cliente')
        if last_activity:
            now = timezone.now().timestamp()
            if now - last_activity > 60:  # 1 minuto
                del request.session['cliente_id']
                messages.warning(request, 'Su sesión ha expirado por inactividad')
                return redirect('portal:login')

        # Actualizar última actividad
        request.session['last_activity_cliente'] = timezone.now().timestamp()

        return view_func(request, *args, **kwargs)

    return wrapper


# ==================== AUTENTICACIÓN ====================

@require_http_methods(["GET", "POST"])
def registro_cliente(request):
    """Vista de registro para clientes"""
    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            try:
                dni = form.cleaned_data['dni']
                password = form.cleaned_data['password']
                palabra_recuperacion = form.cleaned_data['palabra_recuperacion']

                # Verificar que el cliente exista
                try:
                    cliente = Cliente.objects.get(
                        numero_documento=dni,
                        tipo_documento='DNI',
                        tipo_cliente='NATURAL'
                    )
                except Cliente.DoesNotExist:
                    messages.error(request, 'No se encontró un cliente con ese DNI')
                    return render(request, 'portal_cliente/registro.html', {'form': form})

                # Verificar que tenga cuentas activas
                if not cliente.tiene_cuentas_activas():
                    messages.error(
                        request,
                        'Su DNI no tiene cuentas activas en el banco. Por favor acérquese a una agencia.'
                    )
                    return render(request, 'portal_cliente/registro.html', {'form': form})

                # Verificar que no tenga usuario ya creado
                if hasattr(cliente, 'usuario_web'):
                    messages.error(request, 'Este DNI ya tiene un usuario registrado')
                    return render(request, 'portal_cliente/registro.html', {'form': form})

                # Crear usuario cliente
                with transaction.atomic():
                    usuario = UsuarioCliente()
                    usuario.cliente = cliente
                    usuario.username = dni
                    usuario.palabra_recuperacion = palabra_recuperacion.lower()
                    usuario.validar_password(password)
                    usuario.set_password(password)
                    usuario.agregar_password_historial()
                    usuario.save()

                    messages.success(
                        request,
                        f'¡Registro exitoso! Bienvenido {cliente.get_nombre_completo()}. Ahora puede iniciar sesión.'
                    )
                    return redirect('portal:login')

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error inesperado: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario')
    else:
        form = RegistroClienteForm()

    return render(request, 'portal_cliente/registro.html', {'form': form})


@require_http_methods(["GET", "POST"])
def login_cliente(request):
    """Vista de login para clientes"""
    if request.session.get('cliente_id'):
        return redirect('portal:dashboard')

    if request.method == 'POST':
        form = LoginClienteForm(request.POST)
        if form.is_valid():
            dni = form.cleaned_data['dni']
            password = form.cleaned_data['password']

            try:
                usuario = UsuarioCliente.objects.select_related('cliente').get(username=dni)

                # Verificar si está bloqueado
                if usuario.bloqueado:
                    messages.error(request, 'Su cuenta está bloqueada. Contacte con el banco.')
                    return render(request, 'portal_cliente/login.html', {'form': form})

                # Verificar si puede acceder
                if not usuario.puede_acceder():
                    messages.error(request, 'Su cuenta no está activa o no tiene cuentas activas.')
                    return render(request, 'portal_cliente/login.html', {'form': form})

                # Verificar contraseña
                if usuario.check_password(password):
                    usuario.resetear_intentos_fallidos()
                    usuario.ultimo_acceso = timezone.now()
                    usuario.save()

                    request.session['cliente_id'] = usuario.cliente.id
                    request.session['usuario_cliente_id'] = usuario.id
                    request.session['last_activity_cliente'] = timezone.now().timestamp()

                    messages.success(request, f'Bienvenido {usuario.cliente.get_nombre_completo()}')
                    return redirect('portal:dashboard')
                else:
                    usuario.incrementar_intentos_fallidos()
                    intentos_restantes = 3 - usuario.intentos_fallidos

                    if usuario.bloqueado:
                        messages.error(request, 'Su cuenta ha sido bloqueada por exceder los intentos.')
                    else:
                        messages.error(request, f'Credenciales incorrectas. Le quedan {intentos_restantes} intentos.')

            except UsuarioCliente.DoesNotExist:
                messages.error(request, 'Credenciales incorrectas')
        else:
            messages.error(request, 'Por favor corrija los errores en el formulario')
    else:
        form = LoginClienteForm()

    return render(request, 'portal_cliente/login.html', {'form': form})


def logout_cliente(request):
    """Vista de cierre de sesión para clientes"""
    if 'cliente_id' in request.session:
        del request.session['cliente_id']
    if 'usuario_cliente_id' in request.session:
        del request.session['usuario_cliente_id']
    if 'last_activity_cliente' in request.session:
        del request.session['last_activity_cliente']

    messages.success(request, 'Ha cerrado sesión correctamente')
    return redirect('portal:login')


@require_http_methods(["GET", "POST"])
def recuperar_password(request):
    """Vista para recuperar contraseña"""
    if request.method == 'POST':
        form = RecuperarPasswordForm(request.POST)
        if form.is_valid():
            dni = form.cleaned_data['dni']
            palabra = form.cleaned_data['palabra_recuperacion']

            try:
                usuario = UsuarioCliente.objects.get(
                    username=dni,
                    palabra_recuperacion=palabra.lower()
                )

                request.session['recuperar_usuario_id'] = usuario.id
                messages.success(request, 'Verificación exitosa. Ahora puede cambiar su contraseña.')
                return redirect('portal:cambiar_password')

            except UsuarioCliente.DoesNotExist:
                messages.error(request, 'DNI o palabra de recuperación incorrectos')
        else:
            messages.error(request, 'Por favor corrija los errores')
    else:
        form = RecuperarPasswordForm()

    return render(request, 'portal_cliente/recuperar_password.html', {'form': form})


@require_http_methods(["GET", "POST"])
def cambiar_password(request):
    """Vista para cambiar contraseña después de recuperación"""
    if 'recuperar_usuario_id' not in request.session:
        messages.error(request, 'Sesión inválida')
        return redirect('portal:recuperar_password')

    if request.method == 'POST':
        form = CambiarPasswordForm(request.POST)
        if form.is_valid():
            nueva_password = form.cleaned_data['nueva_password']

            try:
                usuario = UsuarioCliente.objects.get(id=request.session['recuperar_usuario_id'])
                usuario.validar_password(nueva_password)

                if usuario.password_en_historial(nueva_password):
                    raise ValidationError('No puede usar una contraseña anterior')

                usuario.set_password(nueva_password)
                usuario.agregar_password_historial()
                usuario.bloqueado = False
                usuario.intentos_fallidos = 0
                usuario.save()

                del request.session['recuperar_usuario_id']

                messages.success(request, 'Contraseña cambiada exitosamente. Ahora puede iniciar sesión.')
                return redirect('portal:login')

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores')
    else:
        form = CambiarPasswordForm()

    return render(request, 'portal_cliente/cambiar_password.html', {'form': form})


# ==================== DASHBOARD Y CONSULTAS ====================

@login_required_cliente
def dashboard_cliente(request):
    """Dashboard principal del cliente"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])
    cuentas = cliente.cuentas.filter(esta_activa=True).order_by('-fecha_apertura')

    ultimos_movimientos = Movimiento.objects.filter(
        cuenta__cliente=cliente
    ).select_related('cuenta', 'usuario').order_by('-fecha_hora')[:10]

    total_soles = sum(c.saldo for c in cuentas if c.moneda == 'SOLES')
    total_dolares = sum(c.saldo for c in cuentas if c.moneda == 'DOLARES')

    context = {
        'cliente': cliente,
        'cuentas': cuentas,
        'total_cuentas': cuentas.count(),
        'total_soles': total_soles,
        'total_dolares': total_dolares,
        'ultimos_movimientos': ultimos_movimientos,
    }

    return render(request, 'portal_cliente/dashboard.html', context)


@login_required_cliente
def mis_cuentas(request):
    """Vista para listar las cuentas del cliente"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])
    cuentas = cliente.cuentas.all().order_by('-fecha_apertura')

    # Calcular totales por moneda
    total_soles = sum(c.saldo for c in cuentas if c.moneda == 'SOLES')
    total_dolares = sum(c.saldo for c in cuentas if c.moneda == 'DOLARES')
    cuentas_activas = cuentas.filter(esta_activa=True, estado='ACTIVA').count()

    context = {
        'cliente': cliente,
        'cuentas': cuentas,
        'total_soles': total_soles,
        'total_dolares': total_dolares,
        'cuentas_activas': cuentas_activas,
    }

    return render(request, 'portal_cliente/mis_cuentas.html', context)


@login_required_cliente
def detalle_cuenta_cliente(request, cuenta_id):
    """Vista para ver detalle de una cuenta"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])
    cuenta = get_object_or_404(Cuenta, id=cuenta_id, cliente=cliente)

    movimientos = cuenta.movimientos.order_by('-fecha_hora')[:20]

    interes_generado = None
    if cuenta.tipo_cuenta == 'PLAZO':
        interes_generado = cuenta.calcular_interes_generado()

    context = {
        'cliente': cliente,
        'cuenta': cuenta,
        'movimientos': movimientos,
        'saldo_disponible': cuenta.get_saldo_disponible(),
        'interes_generado': interes_generado,
    }

    return render(request, 'portal_cliente/detalle_cuenta.html', context)


# ==================== OPERACIONES BANCARIAS ====================

@login_required_cliente
@require_http_methods(["GET", "POST"])
def apertura_cuenta_cliente(request):
    """Vista para que el cliente aperture su propia cuenta"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])

    if request.method == 'POST':
        form = AperturaCuentaClienteForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    usuario_sistema = Usuario.objects.filter(tipo_usuario='ADMINISTRADOR').first()

                    cuenta = Cuenta()
                    cuenta.cliente = cliente
                    cuenta.tipo_cuenta = form.cleaned_data['tipo_cuenta']
                    cuenta.moneda = form.cleaned_data['moneda']
                    cuenta.usuario_apertura = usuario_sistema

                    if cuenta.tipo_cuenta == 'PLAZO':
                        cuenta.monto_inicial = form.cleaned_data['monto_inicial']
                        cuenta.plazo_meses = form.cleaned_data['plazo_meses']
                        cuenta.tasa_interes_mensual = form.cleaned_data['tasa_interes_mensual']
                        cuenta.saldo = cuenta.monto_inicial
                        cuenta.fecha_vencimiento = timezone.now().date() + relativedelta(months=cuenta.plazo_meses)
                    else:
                        cuenta.saldo = Decimal('0.00')

                    cuenta.save()

                    Movimiento.objects.create(
                        cuenta=cuenta,
                        tipo_movimiento='APERTURA',
                        monto=cuenta.saldo,
                        saldo_anterior=Decimal('0.00'),
                        saldo_nuevo=cuenta.saldo,
                        descripcion=f'Apertura de {cuenta.get_tipo_cuenta_display()} - Portal Web',
                        usuario=usuario_sistema
                    )

                    messages.success(request, f'¡Cuenta {cuenta.numero_cuenta} aperturada exitosamente!')
                    return redirect('portal:mis_cuentas')

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores')
    else:
        form = AperturaCuentaClienteForm()

    context = {
        'cliente': cliente,
        'form': form,
    }

    return render(request, 'portal_cliente/apertura_cuenta.html', context)


@login_required_cliente
@require_http_methods(["GET", "POST"])
def deposito_cliente(request):
    """Vista para que el cliente realice depósitos"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])

    if request.method == 'POST':
        form = DepositoClienteForm(request.POST, cliente=cliente)
        if form.is_valid():
            try:
                with transaction.atomic():
                    usuario_sistema = Usuario.objects.filter(tipo_usuario='ADMINISTRADOR').first()

                    cuenta = Cuenta.objects.get(id=form.cleaned_data['cuenta'])
                    monto = form.cleaned_data['monto']
                    origen_fondos = form.cleaned_data.get('origen_fondos', '')

                    # Verificar si requiere autorización
                    limite = Decimal('2000.00')
                    monto_comparacion = monto

                    if cuenta.moneda == 'DOLARES':
                        tc = TipoCambio.obtener_actual()
                        if tc:
                            monto_comparacion = monto * tc.venta

                    if monto_comparacion > limite and not origen_fondos:
                        raise ValidationError('Para depósitos mayores a S/ 2000 debe especificar el origen de fondos')

                    # Crear depósito
                    deposito = Deposito()
                    deposito.cuenta = cuenta
                    deposito.monto = monto
                    deposito.usuario = usuario_sistema
                    deposito.origen_fondos = origen_fondos

                    if monto_comparacion > limite:
                        deposito.requiere_autorizacion = True
                        deposito.clave_autorizacion = f'AUTO-{timezone.now().timestamp()}'

                    deposito.save()

                    # Actualizar saldo
                    saldo_anterior = cuenta.saldo
                    cuenta.saldo += monto
                    cuenta.actualizar_ultimo_movimiento()
                    cuenta.save()

                    # Registrar movimiento
                    movimiento = Movimiento.objects.create(
                        cuenta=cuenta,
                        tipo_movimiento='DEPOSITO',
                        monto=monto,
                        saldo_anterior=saldo_anterior,
                        saldo_nuevo=cuenta.saldo,
                        descripcion=f'Depósito - Portal Web',
                        usuario=usuario_sistema,
                        origen_fondos=origen_fondos,
                        requiere_autorizacion=deposito.requiere_autorizacion,
                        clave_autorizacion=deposito.clave_autorizacion
                    )

                    deposito.movimiento = movimiento
                    deposito.save()

                    messages.success(request,
                                     f'Depósito de {monto} {cuenta.get_moneda_display()} realizado exitosamente')
                    return redirect('portal:detalle_cuenta_cliente', cuenta_id=cuenta.id)

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores')
    else:
        form = DepositoClienteForm(cliente=cliente)

    context = {
        'cliente': cliente,
        'form': form,
    }

    return render(request, 'portal_cliente/deposito.html', context)


@login_required_cliente
@require_http_methods(["GET", "POST"])
def retiro_cliente(request):
    """Vista para que el cliente realice retiros"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])

    if request.method == 'POST':
        form = RetiroClienteForm(request.POST, cliente=cliente)
        if form.is_valid():
            try:
                with transaction.atomic():
                    usuario_sistema = Usuario.objects.filter(tipo_usuario='ADMINISTRADOR').first()

                    cuenta = Cuenta.objects.get(id=form.cleaned_data['cuenta'])
                    monto = form.cleaned_data['monto']

                    if not cuenta.puede_retirar(monto):
                        raise ValidationError('Saldo insuficiente o cuenta embargada')

                    # Crear retiro
                    retiro = Retiro()
                    retiro.cuenta = cuenta
                    retiro.monto = monto
                    retiro.usuario = usuario_sistema
                    retiro.save()

                    # Actualizar saldo
                    saldo_anterior = cuenta.saldo
                    cuenta.saldo -= monto
                    cuenta.actualizar_ultimo_movimiento()
                    cuenta.save()

                    # Registrar movimiento
                    movimiento = Movimiento.objects.create(
                        cuenta=cuenta,
                        tipo_movimiento='RETIRO',
                        monto=monto,
                        saldo_anterior=saldo_anterior,
                        saldo_nuevo=cuenta.saldo,
                        descripcion=f'Retiro - Portal Web',
                        usuario=usuario_sistema
                    )

                    retiro.movimiento = movimiento
                    retiro.save()

                    messages.success(request, f'Retiro de {monto} {cuenta.get_moneda_display()} realizado exitosamente')
                    return redirect('portal:detalle_cuenta_cliente', cuenta_id=cuenta.id)

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores')
    else:
        form = RetiroClienteForm(cliente=cliente)

    context = {
        'cliente': cliente,
        'form': form,
    }

    return render(request, 'portal_cliente/retiro.html', context)


@login_required_cliente
@require_http_methods(["GET", "POST"])
def transferencia_cliente(request):
    """Vista para que el cliente realice transferencias"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])

    if request.method == 'POST':
        form = TransferenciaClienteForm(request.POST, cliente=cliente)
        if form.is_valid():
            try:
                with transaction.atomic():
                    usuario_sistema = Usuario.objects.filter(tipo_usuario='ADMINISTRADOR').first()

                    cuenta_origen = Cuenta.objects.get(id=form.cleaned_data['cuenta_origen'])
                    numero_cuenta_destino = form.cleaned_data['numero_cuenta_destino']
                    monto = form.cleaned_data['monto']
                    descripcion = form.cleaned_data.get('descripcion', '')

                    # Buscar cuenta destino
                    try:
                        cuenta_destino = Cuenta.objects.get(
                            numero_cuenta=numero_cuenta_destino,
                            esta_activa=True
                        )
                    except Cuenta.DoesNotExist:
                        raise ValidationError('La cuenta destino no existe o no está activa')

                    if not cuenta_origen.puede_retirar(monto):
                        raise ValidationError('Saldo insuficiente en cuenta origen')

                    # Calcular monto destino
                    if cuenta_origen.moneda == cuenta_destino.moneda:
                        monto_destino = monto
                        tipo_cambio = None
                    else:
                        tc = TipoCambio.obtener_actual()
                        if not tc:
                            raise ValidationError('No se ha configurado el tipo de cambio del día')

                        if cuenta_origen.moneda == 'SOLES':
                            monto_destino = monto / tc.venta
                            tipo_cambio = tc.venta
                        else:
                            monto_destino = monto * tc.compra
                            tipo_cambio = tc.compra

                        monto_destino = monto_destino.quantize(Decimal('0.01'))

                    # Crear transferencia
                    transferencia = Transferencia()
                    transferencia.cuenta_origen = cuenta_origen
                    transferencia.cuenta_destino = cuenta_destino
                    transferencia.monto_origen = monto
                    transferencia.monto_destino = monto_destino
                    transferencia.tipo_cambio = tipo_cambio
                    transferencia.usuario = usuario_sistema
                    transferencia.descripcion = descripcion
                    transferencia.save()

                    # Actualizar saldos
                    saldo_anterior_origen = cuenta_origen.saldo
                    cuenta_origen.saldo -= monto
                    cuenta_origen.actualizar_ultimo_movimiento()
                    cuenta_origen.save()

                    saldo_anterior_destino = cuenta_destino.saldo
                    cuenta_destino.saldo += monto_destino
                    cuenta_destino.actualizar_ultimo_movimiento()
                    cuenta_destino.save()

                    # Registrar movimientos
                    mov_origen = Movimiento.objects.create(
                        cuenta=cuenta_origen,
                        tipo_movimiento='TRANSFERENCIA_ENVIADA',
                        monto=monto,
                        saldo_anterior=saldo_anterior_origen,
                        saldo_nuevo=cuenta_origen.saldo,
                        descripcion=f'Transferencia a {cuenta_destino.numero_cuenta} - Portal Web',
                        usuario=usuario_sistema,
                        cuenta_destino=cuenta_destino
                    )

                    mov_destino = Movimiento.objects.create(
                        cuenta=cuenta_destino,
                        tipo_movimiento='TRANSFERENCIA_RECIBIDA',
                        monto=monto_destino,
                        saldo_anterior=saldo_anterior_destino,
                        saldo_nuevo=cuenta_destino.saldo,
                        descripcion=f'Transferencia desde {cuenta_origen.numero_cuenta} - Portal Web',
                        usuario=usuario_sistema
                    )

                    transferencia.movimiento_origen = mov_origen
                    transferencia.movimiento_destino = mov_destino
                    transferencia.save()

                    messages.success(request,
                                     f'Transferencia de {monto} {cuenta_origen.get_moneda_display()} realizada exitosamente')
                    return redirect('portal:mis_cuentas')

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores')
    else:
        form = TransferenciaClienteForm(cliente=cliente)

    context = {
        'cliente': cliente,
        'form': form,
    }

    return render(request, 'portal_cliente/transferencia.html', context)


@login_required_cliente
@require_http_methods(["GET", "POST"])
def cerrar_cuenta(request, cuenta_id):
    """Vista para cerrar una cuenta"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])
    cuenta = get_object_or_404(Cuenta, id=cuenta_id, cliente=cliente)

    if request.method == 'POST':
        form = CerrarCuentaForm(request.POST)
        if form.is_valid():
            try:
                if not cuenta.puede_cerrarse():
                    raise ValidationError('La cuenta no puede cerrarse porque tiene saldo o embargos')

                cuenta.cerrar_cuenta()
                messages.success(request, f'La cuenta {cuenta.numero_cuenta} ha sido cerrada exitosamente')
                return redirect('portal:mis_cuentas')

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores')
    else:
        form = CerrarCuentaForm()

    context = {
        'cliente': cliente,
        'cuenta': cuenta,
        'form': form,
    }

    return render(request, 'portal_cliente/cerrar_cuenta.html', context)


@login_required_cliente
@require_http_methods(["GET", "POST"])
def operacion_plazo(request, cuenta_id):
    """Vista para cancelar o renovar cuenta a plazo"""
    cliente = Cliente.objects.get(id=request.session['cliente_id'])
    cuenta = get_object_or_404(Cuenta, id=cuenta_id, cliente=cliente, tipo_cuenta='PLAZO')

    if request.method == 'POST':
        form = OperacionPlazoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    usuario_sistema = Usuario.objects.filter(tipo_usuario='ADMINISTRADOR').first()
                    operacion = form.cleaned_data['operacion']

                    interes_generado = cuenta.calcular_interes_generado()
                    monto_total = cuenta.monto_inicial + interes_generado

                    operacion_plazo = OperacionPlazoFijo()
                    operacion_plazo.cuenta = cuenta
                    operacion_plazo.tipo_operacion = operacion
                    operacion_plazo.monto_principal = cuenta.monto_inicial
                    operacion_plazo.interes_generado = interes_generado
                    operacion_plazo.monto_total = monto_total
                    operacion_plazo.usuario = usuario_sistema

                    if operacion == 'CANCELACION':
                        # Registrar movimiento de interés
                        Movimiento.objects.create(
                            cuenta=cuenta,
                            tipo_movimiento='INTERES_PLAZO',
                            monto=interes_generado,
                            saldo_anterior=cuenta.saldo,
                            saldo_nuevo=cuenta.saldo + interes_generado,
                            descripcion=f'Interés generado al cancelar - Portal Web',
                            usuario=usuario_sistema
                        )

                        # Registrar cancelación
                        cuenta.saldo = Decimal('0.00')
                        cuenta.estado = 'CERRADA'
                        cuenta.esta_activa = False
                        cuenta.fecha_cierre = timezone.now()
                        cuenta.save()

                        Movimiento.objects.create(
                            cuenta=cuenta,
                            tipo_movimiento='CANCELACION_PLAZO',
                            monto=monto_total,
                            saldo_anterior=monto_total,
                            saldo_nuevo=Decimal('0.00'),
                            descripcion=f'Cancelación de plazo fijo - Portal Web',
                            usuario=usuario_sistema
                        )

                        operacion_plazo.save()

                        messages.success(
                            request,
                            f'Cuenta cancelada. Monto total: {monto_total} {cuenta.get_moneda_display()} '
                            f'(Capital: {cuenta.monto_inicial}, Interés: {interes_generado})'
                        )

                    else:  # RENOVACION
                        nuevo_plazo = form.cleaned_data['nuevo_plazo_meses']
                        nueva_tasa = form.cleaned_data['nueva_tasa_interes']

                        # Crear nueva cuenta
                        nueva_cuenta = Cuenta()
                        nueva_cuenta.cliente = cliente
                        nueva_cuenta.tipo_cuenta = 'PLAZO'
                        nueva_cuenta.moneda = cuenta.moneda
                        nueva_cuenta.monto_inicial = monto_total
                        nueva_cuenta.saldo = monto_total
                        nueva_cuenta.plazo_meses = nuevo_plazo
                        nueva_cuenta.tasa_interes_mensual = nueva_tasa
                        nueva_cuenta.fecha_vencimiento = timezone.now().date() + relativedelta(months=nuevo_plazo)
                        nueva_cuenta.usuario_apertura = usuario_sistema
                        nueva_cuenta.save()

                        # Cerrar cuenta anterior
                        cuenta.saldo = Decimal('0.00')
                        cuenta.estado = 'CERRADA'
                        cuenta.esta_activa = False
                        cuenta.fecha_cierre = timezone.now()
                        cuenta.save()

                        # Registrar operación
                        operacion_plazo.nueva_cuenta = nueva_cuenta
                        operacion_plazo.nuevo_plazo_meses = nuevo_plazo
                        operacion_plazo.nueva_tasa_interes = nueva_tasa
                        operacion_plazo.save()

                        # Movimientos
                        Movimiento.objects.create(
                            cuenta=cuenta,
                            tipo_movimiento='RENOVACION_PLAZO',
                            monto=monto_total,
                            saldo_anterior=cuenta.monto_inicial,
                            saldo_nuevo=Decimal('0.00'),
                            descripcion=f'Renovación de plazo fijo - Portal Web',
                            usuario=usuario_sistema
                        )

                        Movimiento.objects.create(
                            cuenta=nueva_cuenta,
                            tipo_movimiento='APERTURA',
                            monto=monto_total,
                            saldo_anterior=Decimal('0.00'),
                            saldo_nuevo=monto_total,
                            descripcion=f'Apertura por renovación - Portal Web',
                            usuario=usuario_sistema
                        )

                        messages.success(
                            request,
                            f'Cuenta renovada exitosamente. Nueva cuenta: {nueva_cuenta.numero_cuenta}. '
                            f'Monto: {monto_total} {cuenta.get_moneda_display()}'
                        )

                    return redirect('portal:mis_cuentas')

            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Error: {str(e)}')
        else:
            messages.error(request, 'Por favor corrija los errores')
    else:
        form = OperacionPlazoForm()

    interes_generado = cuenta.calcular_interes_generado()
    monto_total = cuenta.monto_inicial + interes_generado

    context = {
        'cliente': cliente,
        'cuenta': cuenta,
        'form': form,
        'interes_generado': interes_generado,
        'monto_total': monto_total,
    }

    return render(request, 'portal_cliente/operacion_plazo.html', context)