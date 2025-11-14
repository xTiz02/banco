from django import forms
from django.core.exceptions import ValidationError
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
            raise ValidationError(
                'El DNI debe contener exactamente 8 dígitos numéricos')
        return dni

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirmar = cleaned_data.get('confirmar_password')

        if password and confirmar:
            if password != confirmar:
                raise ValidationError('Las contraseñas no coinciden')

            # Validar requisitos de contraseña
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

            # Validar requisitos
            if len(password) < 8 or len(password) > 16:
                raise ValidationError(
                    'La contraseña debe tener entre 8 y 16 caracteres')

            if not re.search(r'[a-z]', password):
                raise ValidationError(
                    'Debe contener al menos una letra minúscula')

            if not re.search(r'[A-Z]', password):
                raise ValidationError(
                    'Debe contener al menos una letra mayúscula')

            if not re.search(r'\d', password):
                raise ValidationError('Debe contener al menos un número')

            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise ValidationError(
                    'Debe contener al menos un carácter especial')

        return cleaned_data