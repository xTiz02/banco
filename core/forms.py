from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field
from .models import Usuario, TipoCambio


class LoginForm(forms.Form):
  """Formulario de inicio de sesión"""
  username = forms.CharField(
      label='Usuario',
      max_length=150,
      widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingrese su usuario',
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

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Iniciar Sesión', css_class='btn btn-primary w-100'))


class TipoCambioForm(forms.ModelForm):
  """Formulario para configurar tipo de cambio"""

  class Meta:
    model = TipoCambio
    fields = ['compra', 'venta']
    widgets = {
      'compra': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ej: 3.750',
        'step': '0.001',
        'min': '0.001',
      }),
      'venta': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ej: 3.755',
        'step': '0.001',
        'min': '0.001',
      }),
    }
    labels = {
      'compra': 'Tipo de Cambio Compra (USD)',
      'venta': 'Tipo de Cambio Venta (USD)',
    }
    help_texts = {
      'compra': 'Precio al que el banco compra dólares',
      'venta': 'Precio al que el banco vende dólares',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Guardar Tipo de Cambio', css_class='btn btn-primary'))

  def clean(self):
    cleaned_data = super().clean()
    compra = cleaned_data.get('compra')
    venta = cleaned_data.get('venta')

    if compra and venta:
      if venta < compra:
        raise ValidationError(
          'El tipo de cambio de venta no puede ser menor al de compra')

    return cleaned_data


class UsuarioForm(forms.ModelForm):
  """Formulario para crear/editar usuarios"""
  password = forms.CharField(
      label='Contraseña',
      widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingrese la contraseña',
      }),
      required=False,
      help_text='Deje en blanco para mantener la contraseña actual (solo al editar)'
  )
  confirmar_password = forms.CharField(
      label='Confirmar Contraseña',
      widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'placeholder': 'Confirme la contraseña',
      }),
      required=False
  )

  class Meta:
    model = Usuario
    fields = [
      'username',
      'first_name',
      'last_name',
      'email',
      'tipo_usuario',
      'esta_activo',
    ]
    widgets = {
      'username': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombre de usuario',
      }),
      'first_name': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombres',
      }),
      'last_name': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Apellidos',
      }),
      'email': forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'correo@ejemplo.com',
      }),
      'tipo_usuario': forms.Select(attrs={
        'class': 'form-select',
      }),
      'esta_activo': forms.CheckboxInput(attrs={
        'class': 'form-check-input',
      }),
    }
    labels = {
      'username': 'Usuario',
      'first_name': 'Nombres',
      'last_name': 'Apellidos',
      'email': 'Correo Electrónico',
      'tipo_usuario': 'Tipo de Usuario',
      'esta_activo': '¿Usuario Activo?',
    }

  def __init__(self, *args, **kwargs):
    self.edicion = kwargs.pop('edicion', False)
    super().__init__(*args, **kwargs)

    if not self.edicion:
      self.fields['password'].required = True
      self.fields['confirmar_password'].required = True

    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Guardar', css_class='btn btn-primary'))

  def clean(self):
    cleaned_data = super().clean()
    password = cleaned_data.get('password')
    confirmar_password = cleaned_data.get('confirmar_password')

    # Validar contraseña solo si se proporciona
    if password or confirmar_password:
      if password != confirmar_password:
        raise ValidationError('Las contraseñas no coinciden')

      if len(password) < 8:
        raise ValidationError('La contraseña debe tener al menos 8 caracteres')

    # Si es creación, password es obligatorio
    if not self.edicion and not password:
      raise ValidationError('La contraseña es obligatoria al crear un usuario')

    return cleaned_data

  def clean_username(self):
    username = self.cleaned_data.get('username')

    # Verificar si el username ya existe (solo al crear o si se cambió)
    if not self.instance.pk or self.instance.username != username:
      if Usuario.objects.filter(username=username).exists():
        raise ValidationError('Este nombre de usuario ya está en uso')

    return username

  def clean_email(self):
    email = self.cleaned_data.get('email')

    if email:
      # Verificar si el email ya existe (solo al crear o si se cambió)
      if not self.instance.pk or self.instance.email != email:
        if Usuario.objects.filter(email=email).exists():
          raise ValidationError('Este correo electrónico ya está registrado')

    return email