from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
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
    representante_legal = models.CharField(max_length=200, null=True,
                                           blank=True)

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
            if len(
                self.numero_documento) != 8 or not self.numero_documento.isdigit():
                raise ValidationError(
                    {'numero_documento': 'El DNI debe tener 8 dígitos'})
            if self.tipo_cliente != 'NATURAL':
                raise ValidationError({
                                          'tipo_documento': 'El DNI solo es válido para personas naturales'})

        # Validar RUC
        if self.tipo_documento == 'RUC':
            if len(
                self.numero_documento) != 11 or not self.numero_documento.isdigit():
                raise ValidationError(
                    {'numero_documento': 'El RUC debe tener 11 dígitos'})
            if self.tipo_cliente != 'JURIDICA':
                raise ValidationError({
                                          'tipo_documento': 'El RUC solo es válido para personas jurídicas'})

        # Validar datos según tipo de cliente
        if self.tipo_cliente == 'NATURAL':
            if not all(
                [self.nombres, self.apellido_paterno, self.apellido_materno]):
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

    def tiene_cuentas_activas(self):
        """Verifica si el cliente tiene al menos una cuenta activa"""
        return self.cuentas.filter(esta_activa=True, estado='ACTIVA').exists()


class UsuarioCliente(models.Model):
    """Modelo para usuarios clientes del portal web"""
    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        related_name='usuario_web'
    )
    # El username siempre será el DNI
    username = models.CharField(max_length=8, unique=True)  # DNI
    password = models.CharField(max_length=255)  # Hasheada
    palabra_recuperacion = models.CharField(max_length=100)  # Para recuperación

    # Historial de contraseñas (para validar que no repita)
    historial_passwords = models.TextField(default='[]')  # JSON con hashes

    # Control de seguridad
    intentos_fallidos = models.IntegerField(default=0)
    bloqueado = models.BooleanField(default=False)
    fecha_bloqueo = models.DateTimeField(null=True, blank=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)

    # Control
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    esta_activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'usuarios_clientes'
        verbose_name = 'Usuario Cliente'
        verbose_name_plural = 'Usuarios Clientes'

    def __str__(self):
        return f"{self.username} - {self.cliente.get_nombre_completo()}"

    def set_password(self, raw_password):
        """Establece la contraseña hasheada"""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifica la contraseña"""
        return check_password(raw_password, self.password)

    def validar_password(self, password):
        """Valida que la contraseña cumpla los requisitos"""
        if len(password) < 8 or len(password) > 16:
            raise ValidationError(
                'La contraseña debe tener entre 8 y 16 caracteres')

        if not re.search(r'[a-z]', password):
            raise ValidationError(
                'La contraseña debe contener al menos una letra minúscula')

        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                'La contraseña debe contener al menos una letra mayúscula')

        if not re.search(r'\d', password):
            raise ValidationError(
                'La contraseña debe contener al menos un número')

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                'La contraseña debe contener al menos un carácter especial')

        return True

    def password_en_historial(self, raw_password):
        """Verifica si la contraseña ya fue usada antes"""
        import json
        historial = json.loads(self.historial_passwords)

        for hash_anterior in historial:
            if check_password(raw_password, hash_anterior):
                return True
        return False

    def agregar_password_historial(self):
        """Agrega la contraseña actual al historial"""
        import json
        historial = json.loads(self.historial_passwords)
        historial.append(self.password)

        # Mantener solo las últimas 5 contraseñas
        if len(historial) > 5:
            historial = historial[-5:]

        self.historial_passwords = json.dumps(historial)

    def incrementar_intentos_fallidos(self):
        """Incrementa los intentos fallidos"""
        self.intentos_fallidos += 1

        if self.intentos_fallidos >= 3:
            self.bloqueado = True
            self.fecha_bloqueo = timezone.now()

        self.save()

    def resetear_intentos_fallidos(self):
        """Resetea los intentos fallidos"""
        self.intentos_fallidos = 0
        self.save()

    def puede_acceder(self):
        """Verifica si el usuario puede acceder"""
        return (self.esta_activo and
                not self.bloqueado and
                self.cliente.esta_activo and
                self.cliente.tiene_cuentas_activas())


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
    representante_legal = models.CharField(max_length=200, null=True,
                                           blank=True)

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
            if len(
                self.numero_documento) != 8 or not self.numero_documento.isdigit():
                raise ValidationError(
                    {'numero_documento': 'El DNI debe tener 8 dígitos'})
            if self.tipo_cliente != 'NATURAL':
                raise ValidationError({
                                          'tipo_documento': 'El DNI solo es válido para personas naturales'})

        # Validar RUC
        if self.tipo_documento == 'RUC':
            if len(
                self.numero_documento) != 11 or not self.numero_documento.isdigit():
                raise ValidationError(
                    {'numero_documento': 'El RUC debe tener 11 dígitos'})
            if self.tipo_cliente != 'JURIDICA':
                raise ValidationError({
                                          'tipo_documento': 'El RUC solo es válido para personas jurídicas'})

        # Validar datos según tipo de cliente
        if self.tipo_cliente == 'NATURAL':
            if not all(
                [self.nombres, self.apellido_paterno, self.apellido_materno]):
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