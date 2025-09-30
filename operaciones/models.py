from django.db import models

# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from cuentas.models import Cuenta
from core.models import Usuario


class Movimiento(models.Model):
  """Modelo para registrar todos los movimientos de las cuentas"""
  TIPO_MOVIMIENTO_CHOICES = [
    ('DEPOSITO', 'Depósito'),
    ('RETIRO', 'Retiro'),
    ('TRANSFERENCIA_ENVIADA', 'Transferencia Enviada'),
    ('TRANSFERENCIA_RECIBIDA', 'Transferencia Recibida'),
    ('APERTURA', 'Apertura de Cuenta'),
    ('CIERRE', 'Cierre de Cuenta'),
    ('CANCELACION_PLAZO', 'Cancelación de Plazo Fijo'),
    ('RENOVACION_PLAZO', 'Renovación de Plazo Fijo'),
    ('INTERES_PLAZO', 'Interés de Plazo Fijo'),
    ('EMBARGO', 'Embargo'),
    ('DESEMBARGO', 'Levantamiento de Embargo'),
  ]

  cuenta = models.ForeignKey(
      Cuenta,
      on_delete=models.PROTECT,
      related_name='movimientos'
  )
  tipo_movimiento = models.CharField(max_length=30,
                                     choices=TIPO_MOVIMIENTO_CHOICES)
  monto = models.DecimalField(max_digits=15, decimal_places=2)
  saldo_anterior = models.DecimalField(max_digits=15, decimal_places=2)
  saldo_nuevo = models.DecimalField(max_digits=15, decimal_places=2)
  descripcion = models.TextField()
  fecha_hora = models.DateTimeField(auto_now_add=True)
  usuario = models.ForeignKey(
      Usuario,
      on_delete=models.PROTECT,
      related_name='movimientos_realizados'
  )

  # Para transferencias
  cuenta_destino = models.ForeignKey(
      Cuenta,
      on_delete=models.PROTECT,
      related_name='movimientos_recibidos',
      null=True,
      blank=True
  )

  # Para depósitos grandes
  requiere_autorizacion = models.BooleanField(default=False)
  clave_autorizacion = models.CharField(max_length=50, null=True, blank=True)
  origen_fondos = models.TextField(null=True, blank=True)

  class Meta:
    db_table = 'movimientos'
    verbose_name = 'Movimiento'
    verbose_name_plural = 'Movimientos'
    ordering = ['-fecha_hora']
    indexes = [
      models.Index(fields=['-fecha_hora']),
      models.Index(fields=['cuenta', '-fecha_hora']),
    ]

  def __str__(self):
    return f"{self.get_tipo_movimiento_display()} - {self.cuenta.numero_cuenta} - {self.monto}"


class Deposito(models.Model):
  """Modelo específico para depósitos"""
  cuenta = models.ForeignKey(
      Cuenta,
      on_delete=models.PROTECT,
      related_name='depositos'
  )
  monto = models.DecimalField(max_digits=15, decimal_places=2)
  fecha_hora = models.DateTimeField(auto_now_add=True)
  usuario = models.ForeignKey(
      Usuario,
      on_delete=models.PROTECT,
      related_name='depositos_realizados'
  )
  requiere_autorizacion = models.BooleanField(default=False)
  clave_autorizacion = models.CharField(max_length=50, null=True, blank=True)
  origen_fondos = models.TextField(null=True, blank=True)
  movimiento = models.OneToOneField(
      Movimiento,
      on_delete=models.CASCADE,
      related_name='deposito',
      null=True
  )

  class Meta:
    db_table = 'depositos'
    verbose_name = 'Depósito'
    verbose_name_plural = 'Depósitos'
    ordering = ['-fecha_hora']

  def __str__(self):
    return f"Depósito {self.monto} - {self.cuenta.numero_cuenta}"

  def clean(self):
    """Validación de depósitos"""
    if self.monto <= 0:
      raise ValidationError(
          {'monto': 'El monto del depósito debe ser mayor a 0'})

    from django.conf import settings
    limite = Decimal(str(settings.DEPOSITO_LIMITE_AUTORIZACION))

    # Convertir a soles si es necesario para comparar
    monto_comparacion = self.monto
    if self.cuenta.moneda == 'DOLARES':
      from core.models import TipoCambio
      tc = TipoCambio.obtener_actual()
      if tc:
        monto_comparacion = self.monto * tc.venta

    if monto_comparacion > limite:
      self.requiere_autorizacion = True
      if not self.clave_autorizacion or not self.origen_fondos:
        raise ValidationError(
            'Para depósitos mayores a S/ 2000 se requiere clave de autorización y origen de fondos'
        )


class Retiro(models.Model):
  """Modelo específico para retiros"""
  cuenta = models.ForeignKey(
      Cuenta,
      on_delete=models.PROTECT,
      related_name='retiros'
  )
  monto = models.DecimalField(max_digits=15, decimal_places=2)
  fecha_hora = models.DateTimeField(auto_now_add=True)
  usuario = models.ForeignKey(
      Usuario,
      on_delete=models.PROTECT,
      related_name='retiros_realizados'
  )
  movimiento = models.OneToOneField(
      Movimiento,
      on_delete=models.CASCADE,
      related_name='retiro',
      null=True
  )

  class Meta:
    db_table = 'retiros'
    verbose_name = 'Retiro'
    verbose_name_plural = 'Retiros'
    ordering = ['-fecha_hora']

  def __str__(self):
    return f"Retiro {self.monto} - {self.cuenta.numero_cuenta}"

  def clean(self):
    """Validación de retiros"""
    if self.monto <= 0:
      raise ValidationError({'monto': 'El monto del retiro debe ser mayor a 0'})

    if self.cuenta.tipo_cuenta == 'PLAZO':
      raise ValidationError(
        'No se pueden realizar retiros de cuentas a plazo fijo')

    if not self.cuenta.puede_retirar(self.monto):
      raise ValidationError('Saldo insuficiente o cuenta embargada')


class Transferencia(models.Model):
  """Modelo para transferencias entre cuentas"""
  cuenta_origen = models.ForeignKey(
      Cuenta,
      on_delete=models.PROTECT,
      related_name='transferencias_enviadas'
  )
  cuenta_destino = models.ForeignKey(
      Cuenta,
      on_delete=models.PROTECT,
      related_name='transferencias_recibidas'
  )
  monto_origen = models.DecimalField(max_digits=15, decimal_places=2)
  monto_destino = models.DecimalField(max_digits=15, decimal_places=2)
  tipo_cambio = models.DecimalField(
      max_digits=6,
      decimal_places=3,
      null=True,
      blank=True
  )
  fecha_hora = models.DateTimeField(auto_now_add=True)
  usuario = models.ForeignKey(
      Usuario,
      on_delete=models.PROTECT,
      related_name='transferencias_realizadas'
  )
  descripcion = models.TextField(null=True, blank=True)
  movimiento_origen = models.OneToOneField(
      Movimiento,
      on_delete=models.CASCADE,
      related_name='transferencia_origen',
      null=True
  )
  movimiento_destino = models.OneToOneField(
      Movimiento,
      on_delete=models.CASCADE,
      related_name='transferencia_destino',
      null=True
  )

  class Meta:
    db_table = 'transferencias'
    verbose_name = 'Transferencia'
    verbose_name_plural = 'Transferencias'
    ordering = ['-fecha_hora']

  def __str__(self):
    return f"Transferencia {self.cuenta_origen.numero_cuenta} -> {self.cuenta_destino.numero_cuenta}"

  def clean(self):
    """Validación de transferencias"""
    if self.monto_origen <= 0:
      raise ValidationError({'monto_origen': 'El monto debe ser mayor a 0'})

    if self.cuenta_origen.tipo_cuenta == 'PLAZO':
      raise ValidationError(
        'No se pueden realizar transferencias desde cuentas a plazo')

    if not self.cuenta_origen.puede_retirar(self.monto_origen):
      raise ValidationError(
        'Saldo insuficiente en cuenta origen o cuenta embargada')

    if self.cuenta_origen == self.cuenta_destino:
      raise ValidationError('La cuenta origen y destino no pueden ser la misma')


class OperacionPlazoFijo(models.Model):
  """Modelo para operaciones de cuentas a plazo fijo"""
  TIPO_OPERACION_CHOICES = [
    ('CANCELACION', 'Cancelación'),
    ('RENOVACION', 'Renovación'),
  ]

  cuenta = models.ForeignKey(
      Cuenta,
      on_delete=models.PROTECT,
      related_name='operaciones_plazo'
  )
  tipo_operacion = models.CharField(max_length=15,
                                    choices=TIPO_OPERACION_CHOICES)
  monto_principal = models.DecimalField(max_digits=15, decimal_places=2)
  interes_generado = models.DecimalField(max_digits=15, decimal_places=2)
  monto_total = models.DecimalField(max_digits=15, decimal_places=2)
  fecha_hora = models.DateTimeField(auto_now_add=True)
  usuario = models.ForeignKey(
      Usuario,
      on_delete=models.PROTECT,
      related_name='operaciones_plazo_realizadas'
  )

  # Para renovaciones
  nueva_cuenta = models.ForeignKey(
      Cuenta,
      on_delete=models.SET_NULL,
      related_name='renovacion_desde',
      null=True,
      blank=True
  )
  nuevo_plazo_meses = models.IntegerField(null=True, blank=True)
  nueva_tasa_interes = models.DecimalField(
      max_digits=5,
      decimal_places=2,
      null=True,
      blank=True
  )

  class Meta:
    db_table = 'operaciones_plazo_fijo'
    verbose_name = 'Operación de Plazo Fijo'
    verbose_name_plural = 'Operaciones de Plazo Fijo'
    ordering = ['-fecha_hora']

  def __str__(self):
    return f"{self.get_tipo_operacion_display()} - {self.cuenta.numero_cuenta}"