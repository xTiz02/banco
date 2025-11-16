from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
import re


class RegistroClienteForm(forms.Form):
    """Formulario de registro para clientes"""
    dni = forms.CharField(
        label='DNI',
        max_length=8,
        min_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su DNI de 8 dígitos',
            'pattern': '[0-9]{8}',
        }),
        help_text='Debe tener cuentas activas en el banco'
    )

    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cree su contraseña',
        }),
        help_text='Entre 8 y 16 caracteres: mayúsculas, minúsculas, números y caracteres especiales'
    )

    confirmar_password = forms.CharField(
        label='Confirmar Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme su contraseña',
        })
    )

    palabra_recuperacion = forms.CharField(
        label='Palabra de Recuperación',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Palabra para recuperar su contraseña',
        }),
        help_text='Guarde esta palabra en un lugar seguro'
    )

    acepto_terminos = forms.BooleanField(
        label='Acepto los términos y condiciones',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        })
    )

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if not dni or not dni.isdigit() or len(dni) != 8:
            raise ValidationError('El DNI debe contener exactamente 8 dígitos numéricos')
        return dni

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirmar = cleaned_data.get('confirmar_password')

        if password and confirmar:
            if password != confirmar:
                raise ValidationError('Las contraseñas no coinciden')

            if len(password) < 8 or len(password) > 16:
                raise ValidationError('La contraseña debe tener entre 8 y 16 caracteres')

            if not re.search(r'[a-z]', password):
                raise ValidationError('La contraseña debe contener al menos una letra minúscula')

            if not re.search(r'[A-Z]', password):
                raise ValidationError('La contraseña debe contener al menos una letra mayúscula')

            if not re.search(r'\d', password):
                raise ValidationError('La contraseña debe contener al menos un número')

            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise ValidationError(
                    'La contraseña debe contener al menos un carácter especial (!@#$%^&*(),.?":{}|<>)')

        return cleaned_data


class LoginClienteForm(forms.Form):
    """Formulario de login para clientes"""
    dni = forms.CharField(
        label='DNI',
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su DNI',
            'autocomplete': 'username',
        })
    )

    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña',
            'autocomplete': 'current-password',
        })
    )

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if not dni or not dni.isdigit() or len(dni) != 8:
            raise ValidationError('DNI inválido')
        return dni


class RecuperarPasswordForm(forms.Form):
    """Formulario para recuperar contraseña"""
    dni = forms.CharField(
        label='DNI',
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su DNI',
        })
    )

    palabra_recuperacion = forms.CharField(
        label='Palabra de Recuperación',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su palabra de recuperación',
        })
    )

    def clean_dni(self):
        dni = self.cleaned_data.get('dni')
        if not dni or not dni.isdigit() or len(dni) != 8:
            raise ValidationError('DNI inválido')
        return dni


class CambiarPasswordForm(forms.Form):
    """Formulario para cambiar contraseña"""
    nueva_password = forms.CharField(
        label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su nueva contraseña',
        }),
        help_text='Entre 8 y 16 caracteres: mayúsculas, minúsculas, números y caracteres especiales'
    )

    confirmar_password = forms.CharField(
        label='Confirmar Nueva Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme su nueva contraseña',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('nueva_password')
        confirmar = cleaned_data.get('confirmar_password')

        if password and confirmar:
            if password != confirmar:
                raise ValidationError('Las contraseñas no coinciden')

            if len(password) < 8 or len(password) > 16:
                raise ValidationError('La contraseña debe tener entre 8 y 16 caracteres')

            if not re.search(r'[a-z]', password):
                raise ValidationError('Debe contener al menos una letra minúscula')

            if not re.search(r'[A-Z]', password):
                raise ValidationError('Debe contener al menos una letra mayúscula')

            if not re.search(r'\d', password):
                raise ValidationError('Debe contener al menos un número')

            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise ValidationError('Debe contener al menos un carácter especial')

        return cleaned_data


class AperturaCuentaClienteForm(forms.Form):
    """Formulario para apertura de cuentas por el cliente"""
    TIPO_CUENTA_CHOICES = [
        ('', 'Seleccione tipo de cuenta'),
        ('AHORRO', 'Cuenta de Ahorro'),
        ('CORRIENTE', 'Cuenta Corriente'),
        ('PLAZO', 'Cuenta a Plazo Fijo'),
    ]

    MONEDA_CHOICES = [
        ('', 'Seleccione moneda'),
        ('SOLES', 'Soles (S/)'),
        ('DOLARES', 'Dólares ($)'),
    ]

    tipo_cuenta = forms.ChoiceField(
        label='Tipo de Cuenta',
        choices=TIPO_CUENTA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'tipoCuenta'
        })
    )

    moneda = forms.ChoiceField(
        label='Moneda',
        choices=MONEDA_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    # Campos específicos para cuenta a plazo
    monto_inicial = forms.DecimalField(
        label='Monto Inicial',
        max_digits=15,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'id': 'montoInicial'
        }),
        help_text='Requerido solo para Cuentas a Plazo'
    )

    plazo_meses = forms.IntegerField(
        label='Plazo (meses)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 12',
            'id': 'plazoMeses'
        }),
        help_text='Requerido solo para Cuentas a Plazo'
    )

    tasa_interes_mensual = forms.DecimalField(
        label='Tasa de Interés Mensual (%)',
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 1.5',
            'step': '0.01',
            'id': 'tasaInteres'
        }),
        help_text='Requerido solo para Cuentas a Plazo'
    )

    def clean(self):
        cleaned_data = super().clean()
        tipo_cuenta = cleaned_data.get('tipo_cuenta')
        monto_inicial = cleaned_data.get('monto_inicial')
        plazo_meses = cleaned_data.get('plazo_meses')
        tasa_interes = cleaned_data.get('tasa_interes_mensual')

        if tipo_cuenta == 'PLAZO':
            if not monto_inicial or monto_inicial <= 0:
                raise ValidationError('El monto inicial es requerido y debe ser mayor a 0 para cuentas a plazo')

            if not plazo_meses or plazo_meses <= 0:
                raise ValidationError('El plazo en meses es requerido y debe ser mayor a 0')

            if not tasa_interes or tasa_interes <= 0:
                raise ValidationError('La tasa de interés es requerida y debe ser mayor a 0')

        return cleaned_data


class DepositoClienteForm(forms.Form):
    """Formulario para depósitos del cliente"""

    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop('cliente', None)
        super().__init__(*args, **kwargs)

        if self.cliente:
            # Filtrar cuentas activas que permitan depósitos
            cuentas = self.cliente.cuentas.filter(
                esta_activa=True,
                estado='ACTIVA'
            ).exclude(tipo_cuenta='PLAZO')

            choices = [('', 'Seleccione una cuenta')]
            for cuenta in cuentas:
                choices.append((
                    cuenta.id,
                    f'{cuenta.numero_cuenta} - {cuenta.get_tipo_cuenta_display()} - {cuenta.get_moneda_display()} - Saldo: {cuenta.saldo}'
                ))

            self.fields['cuenta'].choices = choices

    cuenta = forms.ChoiceField(
        label='Cuenta',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    monto = forms.DecimalField(
        label='Monto a Depositar',
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'id': 'montoDeposito'
        })
    )

    origen_fondos = forms.CharField(
        label='Origen de Fondos',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Requerido para depósitos mayores a S/ 2000',
            'id': 'origenFondos'
        }),
        help_text='Requerido para depósitos superiores a S/ 2000'
    )

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor a 0')
        return monto


class RetiroClienteForm(forms.Form):
    """Formulario para retiros del cliente"""

    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop('cliente', None)
        super().__init__(*args, **kwargs)

        if self.cliente:
            # Filtrar cuentas activas que permitan retiros
            cuentas = self.cliente.cuentas.filter(
                esta_activa=True,
                estado='ACTIVA'
            ).exclude(tipo_cuenta='PLAZO')

            choices = [('', 'Seleccione una cuenta')]
            for cuenta in cuentas:
                saldo_disponible = cuenta.get_saldo_disponible()
                choices.append((
                    cuenta.id,
                    f'{cuenta.numero_cuenta} - {cuenta.get_tipo_cuenta_display()} - Disponible: {saldo_disponible}'
                ))

            self.fields['cuenta'].choices = choices

    cuenta = forms.ChoiceField(
        label='Cuenta',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'cuentaRetiro'
        })
    )

    monto = forms.DecimalField(
        label='Monto a Retirar',
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor a 0')
        return monto


class TransferenciaClienteForm(forms.Form):
    """Formulario para transferencias del cliente"""

    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop('cliente', None)
        super().__init__(*args, **kwargs)

        if self.cliente:
            # Filtrar cuentas activas que permitan transferencias
            cuentas = self.cliente.cuentas.filter(
                esta_activa=True,
                estado='ACTIVA'
            ).exclude(tipo_cuenta='PLAZO')

            choices = [('', 'Seleccione cuenta origen')]
            for cuenta in cuentas:
                saldo_disponible = cuenta.get_saldo_disponible()
                choices.append((
                    cuenta.id,
                    f'{cuenta.numero_cuenta} - {cuenta.get_tipo_cuenta_display()} - Disponible: {saldo_disponible}'
                ))

            self.fields['cuenta_origen'].choices = choices

    cuenta_origen = forms.ChoiceField(
        label='Cuenta Origen',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

    numero_cuenta_destino = forms.CharField(
        label='Número de Cuenta Destino',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese número de cuenta destino'
        })
    )

    monto = forms.DecimalField(
        label='Monto a Transferir',
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )

    descripcion = forms.CharField(
        label='Descripción (opcional)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Motivo de la transferencia'
        })
    )

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor a 0')
        return monto


class CerrarCuentaForm(forms.Form):
    """Formulario para cerrar cuenta"""
    confirmacion = forms.CharField(
        label='Escriba "CONFIRMAR" para cerrar la cuenta',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'CONFIRMAR'
        })
    )

    def clean_confirmacion(self):
        confirmacion = self.cleaned_data.get('confirmacion')
        if confirmacion != 'CONFIRMAR':
            raise ValidationError('Debe escribir "CONFIRMAR" para cerrar la cuenta')
        return confirmacion


class OperacionPlazoForm(forms.Form):
    """Formulario para cancelación/renovación de plazo fijo"""
    OPERACION_CHOICES = [
        ('CANCELACION', 'Cancelar Cuenta'),
        ('RENOVACION', 'Renovar Cuenta'),
    ]

    operacion = forms.ChoiceField(
        label='Operación',
        choices=OPERACION_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )

    # Campos para renovación
    nuevo_plazo_meses = forms.IntegerField(
        label='Nuevo Plazo (meses)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 12',
            'id': 'nuevoPlazo'
        })
    )

    nueva_tasa_interes = forms.DecimalField(
        label='Nueva Tasa de Interés Mensual (%)',
        max_digits=5,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 1.5',
            'step': '0.01',
            'id': 'nuevaTasa'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        operacion = cleaned_data.get('operacion')
        nuevo_plazo = cleaned_data.get('nuevo_plazo_meses')
        nueva_tasa = cleaned_data.get('nueva_tasa_interes')

        if operacion == 'RENOVACION':
            if not nuevo_plazo or nuevo_plazo <= 0:
                raise ValidationError('El nuevo plazo es requerido para renovación')

            if not nueva_tasa or nueva_tasa <= 0:
                raise ValidationError('La nueva tasa de interés es requerida para renovación')

        return cleaned_data