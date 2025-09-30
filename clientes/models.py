from django.db import models

# Create your models here.
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import re


class Cliente(models.Model):
  """Modelo base para clientes del banco"""
  TIPO_CLIENTE_CHOICES = [
    ('NATURAL', 'Persona Natural'),
    ('JURIDICA', 'Persona Jurídica'),
  ]

  TIPO_DOCUMENTO_CHOICES = [
    ('DNI', 'DNI'),
    ('RUC', 'RUC'),
  ]

  codigo = models.CharField(max_length=20, unique=True, editable=False)
  tipo_cliente = models.CharField(max_length=10, choices=TIPO_CLIENTE_CHOICES)
  tipo_documento = models.CharField(max_length=3,
                                    choices=TIPO_DOCUMENTO_CHOICES)
  numero_documento = models.CharField(max_length=11, unique=True)

  # Datos para Persona Natural
  nombres = models.CharField(max_length=100, null=True, blank=True)
  apellido_paterno = models.CharField(max_length=100, null=True, blank=True)
  apellido_materno = models.CharField(max_length=100, null=True, blank=True)
  fecha_nacimiento = models.DateField(null=True, blank=True)

  # Datos para Persona Jurídica
  razon_social = models.CharField(max_length=200, null=True, blank=True)
  nombre_comercial = models.CharField(max_length=200, null=True, blank=True)
  representante_legal = models.CharField(max_length=200, null=True, blank=True)

  # Datos Comunes
  direccion = models.TextField()
  telefono = models.CharField(max_length=20, null=True, blank=True)
  email = models.EmailField(null=True, blank=True)

  # Control
  fecha_registro = models.DateTimeField(auto_now_add=True)
  fecha_actualizacion = models.DateTimeField(auto_now=True)
  esta_activo = models.BooleanField(default=True)

  class Meta:
    db_table = 'clientes'
    verbose_name = 'Cliente'
    verbose_name_plural = 'Clientes'
    ordering = ['-fecha_registro']

  def __str__(self):
    if self.tipo_cliente == 'NATURAL':
      return f"{self.codigo} - {self.get_nombre_completo()}"
    return f"{self.codigo} - {self.razon_social}"

  def clean(self):
    """Validación de datos del cliente"""
    # Validar DNI
    if self.tipo_documento == 'DNI':
      if len(self.numero_documento) != 8 or not self.numero_documento.isdigit():
        raise ValidationError(
            {'numero_documento': 'El DNI debe tener 8 dígitos'})
      if self.tipo_cliente != 'NATURAL':
        raise ValidationError(
            {'tipo_documento': 'El DNI solo es válido para personas naturales'})

    # Validar RUC
    if self.tipo_documento == 'RUC':
      if len(
          self.numero_documento) != 11 or not self.numero_documento.isdigit():
        raise ValidationError(
            {'numero_documento': 'El RUC debe tener 11 dígitos'})
      if self.tipo_cliente != 'JURIDICA':
        raise ValidationError(
            {'tipo_documento': 'El RUC solo es válido para personas jurídicas'})

    # Validar datos según tipo de cliente
    if self.tipo_cliente == 'NATURAL':
      if not all([self.nombres, self.apellido_paterno, self.apellido_materno]):
        raise ValidationError(
          'Debe completar nombres y apellidos para persona natural')
    else:
      if not self.razon_social:
        raise ValidationError({
                                'razon_social': 'Debe completar la razón social para persona jurídica'})

  def save(self, *args, **kwargs):
    """Genera código automático al crear cliente"""
    if not self.codigo:
      self.codigo = self.generar_codigo()
    self.full_clean()
    super().save(*args, **kwargs)

  def generar_codigo(self):
    """Genera código único para el cliente"""
    prefijo = 'CLI'
    fecha_actual = timezone.now()
    anio = fecha_actual.strftime('%Y')

    ultimo_cliente = Cliente.objects.filter(
        codigo__startswith=f"{prefijo}{anio}"
    ).order_by('-codigo').first()

    if ultimo_cliente:
      ultimo_numero = int(ultimo_cliente.codigo[-6:])
      nuevo_numero = ultimo_numero + 1
    else:
      nuevo_numero = 1

    return f"{prefijo}{anio}{nuevo_numero:06d}"

  def get_nombre_completo(self):
    """Retorna el nombre completo del cliente"""
    if self.tipo_cliente == 'NATURAL':
      return f"{self.nombres} {self.apellido_paterno} {self.apellido_materno}"
    return self.razon_social

  def get_cuentas_activas(self):
    """Retorna las cuentas activas del cliente"""
    return self.cuentas.filter(esta_activa=True)

  def tiene_cuentas(self):
    """Verifica si el cliente tiene cuentas"""
    return self.cuentas.exists()


class DatosReniec(models.Model):
  """Almacena datos obtenidos de RENIEC"""
  cliente = models.OneToOneField(
      Cliente,
      on_delete=models.CASCADE,
      related_name='datos_reniec'
  )
  dni = models.CharField(max_length=8)
  nombres = models.CharField(max_length=100)
  apellido_paterno = models.CharField(max_length=100)
  apellido_materno = models.CharField(max_length=100)
  fecha_nacimiento = models.DateField()
  ubigeo = models.CharField(max_length=6, null=True, blank=True)
  direccion = models.TextField(null=True, blank=True)
  fecha_consulta = models.DateTimeField(auto_now_add=True)

  class Meta:
    db_table = 'datos_reniec'
    verbose_name = 'Datos RENIEC'
    verbose_name_plural = 'Datos RENIEC'

  def __str__(self):
    return f"RENIEC - {self.dni}"


class DatosSunat(models.Model):
  """Almacena datos obtenidos de SUNAT"""
  cliente = models.OneToOneField(
      Cliente,
      on_delete=models.CASCADE,
      related_name='datos_sunat'
  )
  ruc = models.CharField(max_length=11)
  razon_social = models.CharField(max_length=200)
  nombre_comercial = models.CharField(max_length=200, null=True, blank=True)
  tipo_contribuyente = models.CharField(max_length=100, null=True, blank=True)
  estado = models.CharField(max_length=50, null=True, blank=True)
  condicion = models.CharField(max_length=50, null=True, blank=True)
  direccion = models.TextField(null=True, blank=True)
  departamento = models.CharField(max_length=100, null=True, blank=True)
  provincia = models.CharField(max_length=100, null=True, blank=True)
  distrito = models.CharField(max_length=100, null=True, blank=True)
  fecha_consulta = models.DateTimeField(auto_now_add=True)

  class Meta:
    db_table = 'datos_sunat'
    verbose_name = 'Datos SUNAT'
    verbose_name_plural = 'Datos SUNAT'

  def __str__(self):
    return f"SUNAT - {self.ruc}"