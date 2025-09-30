from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone


class Usuario(AbstractUser):
  """Modelo extendido de usuario para empleados y administradores"""
  TIPO_USUARIO_CHOICES = [
    ('EMPLEADO', 'Empleado'),
    ('ADMINISTRADOR', 'Administrador'),
  ]

  tipo_usuario = models.CharField(
      max_length=20,
      choices=TIPO_USUARIO_CHOICES,
      default='EMPLEADO'
  )
  esta_activo = models.BooleanField(default=True)
  fecha_creacion = models.DateTimeField(auto_now_add=True)
  fecha_modificacion = models.DateTimeField(auto_now=True)
  bloqueado = models.BooleanField(default=False)
  fecha_bloqueo = models.DateTimeField(null=True, blank=True)
  intentos_fallidos = models.IntegerField(default=0)
  ultimo_intento_fallido = models.DateTimeField(null=True, blank=True)

  class Meta:
    db_table = 'usuarios'
    verbose_name = 'Usuario'
    verbose_name_plural = 'Usuarios'

  def __str__(self):
    return f"{self.username} - {self.get_tipo_usuario_display()}"

  def es_administrador(self):
    """Verifica si el usuario es administrador"""
    return self.tipo_usuario == 'ADMINISTRADOR'

  def es_empleado(self):
    """Verifica si el usuario es empleado"""
    return self.tipo_usuario == 'EMPLEADO'

  def puede_operar(self):
    """Verifica si el usuario puede realizar operaciones"""
    return self.esta_activo and not self.bloqueado and self.is_active

  def incrementar_intentos_fallidos(self):
    """Incrementa los intentos fallidos de login"""
    self.intentos_fallidos += 1
    self.ultimo_intento_fallido = timezone.now()

    if self.intentos_fallidos >= 3:
      self.bloqueado = True
      self.fecha_bloqueo = timezone.now()

    self.save()

  def resetear_intentos_fallidos(self):
    """Resetea los intentos fallidos después de login exitoso"""
    self.intentos_fallidos = 0
    self.ultimo_intento_fallido = None
    self.save()

  def desbloquear(self):
    """Desbloquea el usuario (solo administrador)"""
    self.bloqueado = False
    self.fecha_bloqueo = None
    self.intentos_fallidos = 0
    self.ultimo_intento_fallido = None
    self.save()


class TipoCambio(models.Model):
  """Modelo para almacenar el tipo de cambio diario"""
  fecha = models.DateField(unique=True)
  compra = models.DecimalField(max_digits=6, decimal_places=3)
  venta = models.DecimalField(max_digits=6, decimal_places=3)
  usuario_registro = models.ForeignKey(
      Usuario,
      on_delete=models.PROTECT,
      related_name='tipos_cambio_registrados'
  )
  fecha_registro = models.DateTimeField(auto_now_add=True)

  class Meta:
    db_table = 'tipos_cambio'
    verbose_name = 'Tipo de Cambio'
    verbose_name_plural = 'Tipos de Cambio'
    ordering = ['-fecha']

  def __str__(self):
    return f"TC {self.fecha}: C={self.compra} V={self.venta}"

  def clean(self):
    """Validación de datos"""
    if self.compra <= 0:
      raise ValidationError(
          {'compra': 'El tipo de cambio de compra debe ser mayor a 0'})
    if self.venta <= 0:
      raise ValidationError(
          {'venta': 'El tipo de cambio de venta debe ser mayor a 0'})
    if self.venta < self.compra:
      raise ValidationError({
                              'venta': 'El tipo de cambio de venta no puede ser menor al de compra'})

  @classmethod
  def obtener_actual(cls):
    """Obtiene el tipo de cambio de hoy"""
    hoy = timezone.now().date()
    try:
      return cls.objects.get(fecha=hoy)
    except cls.DoesNotExist:
      return None

  @classmethod
  def tipo_cambio_configurado_hoy(cls):
    """Verifica si ya se configuró el tipo de cambio del día"""
    return cls.obtener_actual() is not None


class AuditoriaAcceso(models.Model):
  """Modelo para auditar accesos al sistema"""
  usuario = models.ForeignKey(
      Usuario,
      on_delete=models.CASCADE,
      related_name='auditorias_acceso'
  )
  fecha_hora = models.DateTimeField(auto_now_add=True)
  tipo_evento = models.CharField(max_length=50)
  ip_address = models.GenericIPAddressField(null=True, blank=True)
  user_agent = models.TextField(null=True, blank=True)
  exitoso = models.BooleanField(default=True)
  detalle = models.TextField(null=True, blank=True)

  class Meta:
    db_table = 'auditoria_accesos'
    verbose_name = 'Auditoría de Acceso'
    verbose_name_plural = 'Auditorías de Accesos'
    ordering = ['-fecha_hora']

  def __str__(self):
    return f"{self.usuario.username} - {self.tipo_evento} - {self.fecha_hora}"