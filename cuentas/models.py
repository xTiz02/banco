from django.db import models

# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from clientes.models import Cliente
from core.models import Usuario


class Cuenta(models.Model):
  """Modelo base para cuentas bancarias"""
  TIPO_CUENTA_CHOICES = [
    ('AHORRO', 'Cuenta de Ahorro'),
    ('CORRIENTE', 'Cuenta Corriente'),
    ('PLAZO', 'Cuenta a Plazo Fijo'),
  ]

  MONEDA_CHOICES = [
    ('SOLES', 'Soles'),
    ('DOLARES', 'Dólares'),
  ]

  ESTADO_CHOICES = [
    ('ACTIVA', 'Activa'),
    ('INACTIVA', 'Inactiva'),
    ('CERRADA', 'Cerrada'),
    ('EMBARGADA', 'Embargada'),
  ]

  numero_cuenta = models.CharField(max_length=20, unique=True, editable=False)
  cliente = models.ForeignKey(
      Cliente,
      on_delete=models.PROTECT,
      related_name='cuentas'
  )
  tipo_cuenta = models.CharField(max_length=10, choices=TIPO_CUENTA_CHOICES)
  moneda = models.CharField(max_length=10, choices=MONEDA_CHOICES)
  saldo = models.DecimalField(max_digits=15, decimal_places=2, default=0)
  estado = models.CharField(max_length=10, choices=ESTADO_CHOICES,
                            default='ACTIVA')

  # Específico para Cuenta Corriente
  monto_sobregiro = models.DecimalField(
      max_digits=15,
      decimal_places=2,
      default=0,
      help_text='Monto máximo de sobregiro permitido'
  )

  # Específico para Cuenta a Plazo
  monto_inicial = models.DecimalField(
      max_digits=15,
      decimal_places=2,
      null=True,
      blank=True
  )
  plazo_meses = models.IntegerField(
      null=True,
      blank=True,
      help_text='Plazo en meses'
  )
  tasa_interes_mensual = models.DecimalField(
      max_digits=5,
      decimal_places=2,
      null=True,
      blank=True,
      help_text='Tasa de interés mensual en porcentaje'
  )
  fecha_vencimiento = models.DateField(null=True, blank=True)

  # Embargo
  monto_embargado = models.DecimalField(max_digits=15, decimal_places=2,
                                        default=0)
  embargo_total = models.BooleanField(default=False)

  # Control
  fecha_apertura = models.DateTimeField(auto_now_add=True)
  fecha_ultimo_movimiento = models.DateTimeField(auto_now_add=True)
  fecha_cierre = models.DateTimeField(null=True, blank=True)
  usuario_apertura = models.ForeignKey(
      Usuario,
      on_delete=models.PROTECT,
      related_name='cuentas_aperturadas'
  )
  esta_activa = models.BooleanField(default=True)

  class Meta:
    db_table = 'cuentas'
    verbose_name = 'Cuenta'
    verbose_name_plural = 'Cuentas'
    ordering = ['-fecha_apertura']

  def __str__(self):
    return f"{self.numero_cuenta} - {self.get_tipo_cuenta_display()} - {self.cliente.get_nombre_completo()}"

  def clean(self):
    """Validación de datos de la cuenta"""
    if self.tipo_cuenta == 'PLAZO':
      if not all(
          [self.monto_inicial, self.plazo_meses, self.tasa_interes_mensual]):
        raise ValidationError(
          'Las cuentas a plazo requieren monto inicial, plazo y tasa de interés')
      if self.monto_inicial <= 0:
        raise ValidationError(
            {'monto_inicial': 'El monto inicial debe ser mayor a 0'})
      if self.plazo_meses <= 0:
        raise ValidationError(
            {'plazo_meses': 'El plazo debe ser mayor a 0 meses'})
      if self.tasa_interes_mensual <= 0:
        raise ValidationError(
            {'tasa_interes_mensual': 'La tasa de interés debe ser mayor a 0'})

    if self.tipo_cuenta == 'CORRIENTE' and self.monto_sobregiro < 0:
      raise ValidationError(
          {'monto_sobregiro': 'El monto de sobregiro no puede ser negativo'})

  def save(self, *args, **kwargs):
    """Genera número de cuenta y calcula fecha de vencimiento"""
    if not self.numero_cuenta:
      self.numero_cuenta = self.generar_numero_cuenta()

    if self.tipo_cuenta == 'PLAZO' and self.plazo_meses and not self.fecha_vencimiento:
      from dateutil.relativedelta import relativedelta
      self.fecha_vencimiento = timezone.now().date() + relativedelta(
        months=self.plazo_meses)

    if self.tipo_cuenta == 'PLAZO' and self.monto_inicial and self.saldo == 0:
      self.saldo = self.monto_inicial

    self.full_clean()
    super().save(*args, **kwargs)

  def generar_numero_cuenta(self):
    """Genera número de cuenta único"""
    prefijo_tipo = {
      'AHORRO': '001',
      'CORRIENTE': '002',
      'PLAZO': '003',
    }
    prefijo_moneda = {
      'SOLES': '1',
      'DOLARES': '2',
    }

    prefijo = prefijo_tipo[self.tipo_cuenta] + prefijo_moneda[self.moneda]

    ultima_cuenta = Cuenta.objects.filter(
        numero_cuenta__startswith=prefijo
    ).order_by('-numero_cuenta').first()

    if ultima_cuenta:
      ultimo_numero = int(ultima_cuenta.numero_cuenta[-10:])
      nuevo_numero = ultimo_numero + 1
    else:
      nuevo_numero = 1

    return f"{prefijo}{nuevo_numero:010d}"

  def get_saldo_disponible(self):
    """Retorna el saldo disponible considerando embargos"""
    if self.embargo_total:
      return Decimal('0.00')
    return max(self.saldo - self.monto_embargado, Decimal('0.00'))

  def puede_retirar(self, monto):
    """Verifica si se puede retirar el monto solicitado"""
    if self.tipo_cuenta == 'PLAZO':
      return False

    if self.embargo_total:
      return False

    saldo_disponible = self.get_saldo_disponible()

    if self.tipo_cuenta == 'AHORRO':
      return monto <= saldo_disponible

    if self.tipo_cuenta == 'CORRIENTE':
      return monto <= (saldo_disponible + self.monto_sobregiro)

    return False

  def actualizar_ultimo_movimiento(self):
    """Actualiza la fecha del último movimiento"""
    self.fecha_ultimo_movimiento = timezone.now()
    self.save(update_fields=['fecha_ultimo_movimiento'])

  def puede_cerrarse(self):
    """Verifica si la cuenta puede cerrarse"""
    return self.saldo == 0 and self.monto_embargado == 0

  def debe_inactivarse_automaticamente(self):
    """Verifica si la cuenta debe inactivarse por inactividad"""
    if self.tipo_cuenta == 'PLAZO':
      return False

    if self.saldo != 0:
      return False

    tres_meses_atras = timezone.now() - timezone.timedelta(days=90)
    return self.fecha_ultimo_movimiento < tres_meses_atras

  def calcular_interes_generado(self):
    """Calcula el interés generado hasta la fecha actual para cuentas a plazo"""
    if self.tipo_cuenta != 'PLAZO':
      return Decimal('0.00')

    fecha_actual = timezone.now().date()
    fecha_apertura = self.fecha_apertura.date()

    dias_transcurridos = (fecha_actual - fecha_apertura).days
    meses_transcurridos = Decimal(dias_transcurridos) / Decimal('30')

    tasa_decimal = self.tasa_interes_mensual / Decimal('100')
    interes = self.monto_inicial * tasa_decimal * meses_transcurridos

    return interes.quantize(Decimal('0.01'))

  def cerrar_cuenta(self):
    """Cierra la cuenta"""
    if not self.puede_cerrarse():
      raise ValidationError(
        'La cuenta no puede cerrarse porque tiene saldo o embargos')

    self.estado = 'CERRADA'
    self.esta_activa = False
    self.fecha_cierre = timezone.now()
    self.save()

  def inactivar_cuenta(self):
    """Inactiva la cuenta"""
    self.estado = 'INACTIVA'
    self.esta_activa = False
    self.save()

  def activar_cuenta(self):
    """Activa la cuenta"""
    self.estado = 'ACTIVA'
    self.esta_activa = True
    self.save()


class Embargo(models.Model):
  """Modelo para registrar embargos judiciales"""
  cuenta = models.ForeignKey(
      Cuenta,
      on_delete=models.PROTECT,
      related_name='embargos'
  )
  numero_oficio = models.CharField(max_length=50, unique=True)
  juzgado = models.CharField(max_length=200)
  monto_embargado = models.DecimalField(max_digits=15, decimal_places=2)
  es_total = models.BooleanField(default=False)
  fecha_embargo = models.DateTimeField(auto_now_add=True)
  fecha_levantamiento = models.DateTimeField(null=True, blank=True)
  esta_vigente = models.BooleanField(default=True)
  observaciones = models.TextField(null=True, blank=True)
  usuario_registro = models.ForeignKey(
      Usuario,
      on_delete=models.PROTECT,
      related_name='embargos_registrados'
  )

  class Meta:
    db_table = 'embargos'
    verbose_name = 'Embargo'
    verbose_name_plural = 'Embargos'
    ordering = ['-fecha_embargo']

  def __str__(self):
    return f"Embargo {self.numero_oficio} - Cuenta {self.cuenta.numero_cuenta}"

  def levantar_embargo(self):
    """Levanta el embargo"""
    self.esta_vigente = False
    self.fecha_levantamiento = timezone.now()
    self.save()

    # Actualizar cuenta
    self.cuenta.monto_embargado -= self.monto_embargado
    if self.es_total:
      self.cuenta.embargo_total = False

    # Verificar si hay otros embargos totales
    if self.cuenta.embargos.filter(esta_vigente=True, es_total=True).exists():
      self.cuenta.embargo_total = True

    self.cuenta.save()