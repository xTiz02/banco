from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field, Row, Column
from .models import Cliente


class ClienteForm(forms.ModelForm):
  """Formulario para registrar/editar clientes"""

  class Meta:
    model = Cliente
    fields = [
      'tipo_cliente',
      'tipo_documento',
      'numero_documento',
      'nombres',
      'apellido_paterno',
      'apellido_materno',
      'fecha_nacimiento',
      'razon_social',
      'nombre_comercial',
      'representante_legal',
      'direccion',
      'telefono',
      'email',
    ]
    widgets = {
      'tipo_cliente': forms.Select(attrs={
        'class': 'form-select',
        'onchange': 'toggleTipoCliente()',
      }),
      'tipo_documento': forms.Select(attrs={
        'class': 'form-select',
        'onchange': 'toggleTipoDocumento()',
      }),
      'numero_documento': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Ingrese número de documento',
      }),
      'nombres': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombres',
      }),
      'apellido_paterno': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Apellido Paterno',
      }),
      'apellido_materno': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Apellido Materno',
      }),
      'fecha_nacimiento': forms.DateInput(attrs={
        'class': 'form-control',
        'type': 'date',
      }),
      'razon_social': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Razón Social',
      }),
      'nombre_comercial': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombre Comercial',
      }),
      'representante_legal': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Representante Legal',
      }),
      'direccion': forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 3,
        'placeholder': 'Dirección completa',
      }),
      'telefono': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Teléfono',
      }),
      'email': forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'correo@ejemplo.com',
      }),
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Guardar Cliente', css_class='btn btn-primary'))

  def clean_numero_documento(self):
    numero_documento = self.cleaned_data.get('numero_documento')
    tipo_documento = self.cleaned_data.get('tipo_documento')

    if not numero_documento:
      raise ValidationError('El número de documento es obligatorio')

    # Verificar si ya existe (solo al crear o si se cambió)
    if not self.instance.pk or self.instance.numero_documento != numero_documento:
      if Cliente.objects.filter(numero_documento=numero_documento).exists():
        raise ValidationError(
          'Ya existe un cliente con este número de documento')

    return numero_documento

  def clean(self):
    cleaned_data = super().clean()
    tipo_cliente = cleaned_data.get('tipo_cliente')
    tipo_documento = cleaned_data.get('tipo_documento')

    # Validaciones según tipo de cliente
    if tipo_cliente == 'NATURAL':
      if tipo_documento != 'DNI':
        raise ValidationError('Las personas naturales deben usar DNI')

      if not all([
        cleaned_data.get('nombres'),
        cleaned_data.get('apellido_paterno'),
        cleaned_data.get('apellido_materno')
      ]):
        raise ValidationError(
          'Debe completar nombres y apellidos para persona natural')

    elif tipo_cliente == 'JURIDICA':
      if tipo_documento != 'RUC':
        raise ValidationError('Las personas jurídicas deben usar RUC')

      if not cleaned_data.get('razon_social'):
        raise ValidationError(
          'Debe completar la razón social para persona jurídica')

    return cleaned_data


class BuscarClienteForm(forms.Form):
  """Formulario para buscar clientes"""
  busqueda = forms.CharField(
      required=False,
      widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Buscar por código, documento, nombre o razón social...',
      })
  )
  tipo_cliente = forms.ChoiceField(
      required=False,
      choices=[('', 'Todos')] + Cliente.TIPO_CLIENTE_CHOICES,
      widget=forms.Select(attrs={
        'class': 'form-select',
      })
  )

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.helper = FormHelper()
    self.helper.form_method = 'get'
    self.helper.add_input(
      Submit('submit', 'Buscar', css_class='btn btn-primary'))