from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field
from decimal import Decimal

from .models import Cuenta, Embargo
from clientes.models import Cliente


class CuentaForm(forms.ModelForm):
  """Formulario para aperturar cuenta"""

  class Meta:
    model = Cuenta
    fields = [
      'cliente',
      'tipo_cuenta',
      'moneda',
      'saldo',
      'monto_sobregiro',
      'monto_inicial',
      'plazo_meses',
      'tasa_interes_mensual',
    ]
    widgets = {
      'cliente': forms.Select(attrs={
        'class': 'form-select',
      }),
      'tipo_cuenta': forms.Select(attrs={
        'class': 'form-select',
        'onchange': 'toggleTipoCuenta()',
      }),
      'moneda': forms.Select(attrs={
        'class': 'form-select',
      }),
      'saldo': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '0.00',
        'step': '0.01',
        'min': '0',
      }),
      'monto_sobregiro': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '0.00',
        'step': '0.01',
        'min': '0',
      }),
      'monto_inicial': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '1000.00',
        'step': '0.01',
        'min': '0.01',
      }),
      'plazo_meses': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '12',
        'min': '1',
      }),
      'tasa_interes_mensual': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '0.50',
        'step': '0.01',
        'min': '0.01',
      }),
    }
    labels = {
      'cliente': 'Cliente',
      'tipo_cuenta': 'Tipo de Cuenta',
      'moneda': 'Moneda',
      'saldo': 'Saldo Inicial (Ahorro/Corriente)',
      'monto_sobregiro': 'Monto de Sobregiro (solo Cuenta Corriente)',
      'monto_inicial': 'Monto Inicial (solo Cuenta a Plazo)',
      'plazo_meses': 'Plazo en Meses (solo Cuenta a Plazo)',
      'tasa_interes_mensual': 'Tasa de Interés Mensual % (solo Cuenta a Plazo)',
    }
    help_texts = {
      'saldo': 'Puede ser 0 para cuentas de ahorro y corriente',
      'monto_sobregiro': 'Monto máximo permitido en sobregiro',
      'monto_inicial': 'Monto obligatorio para cuentas a plazo',
      'plazo_meses': 'Cantidad de meses del plazo fijo',
      'tasa_interes_mensual': 'Tasa de interés mensual en porcentaje',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields['cliente'].queryset = Cliente.objects.filter(esta_activo=True)
    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Aperturar Cuenta', css_class='btn btn-primary'))

  def clean(self):
    cleaned_data = super().clean()
    tipo_cuenta = cleaned_data.get('tipo_cuenta')

    if tipo_cuenta == 'PLAZO':
      if not all([
        cleaned_data.get('monto_inicial'),
        cleaned_data.get('plazo_meses'),
        cleaned_data.get('tasa_interes_mensual')
      ]):
        raise ValidationError(
            'Las cuentas a plazo requieren monto inicial, plazo y tasa de interés'
        )

    return cleaned_data


class EmbargoForm(forms.ModelForm):
  """Formulario para registrar embargo"""

  class Meta:
    model = Embargo
    fields = [
      'numero_oficio',
      'juzgado',
      'monto_embargado',
      'es_total',
      'observaciones',
    ]
    widgets = {
      'numero_oficio': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Número de oficio judicial',
      }),
      'juzgado': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombre del juzgado',
      }),
      'monto_embargado': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '0.00',
        'step': '0.01',
        'min': '0.01',
      }),
      'es_total': forms.CheckboxInput(attrs={
        'class': 'form-check-input',
        'onchange': 'toggleEmbargoTotal()',
      }),
      'observaciones': forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 3,
        'placeholder': 'Observaciones adicionales',
      }),
    }
    labels = {
      'numero_oficio': 'Número de Oficio',
      'juzgado': 'Juzgado',
      'monto_embargado': 'Monto Embargado',
      'es_total': '¿Embargo Total?',
      'observaciones': 'Observaciones',
    }
    help_texts = {
      'monto_embargado': 'Monto a embargar (se deshabilitará si es embargo total)',
      'es_total': 'Marque si el embargo es sobre el total del saldo',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Registrar Embargo', css_class='btn btn-danger'))

  def clean_numero_oficio(self):
    numero_oficio = self.cleaned_data.get('numero_oficio')

    if Embargo.objects.filter(numero_oficio=numero_oficio).exists():
      raise ValidationError('Ya existe un embargo con este número de oficio')

    return numero_oficio


class BuscarCuentaForm(forms.Form):
  """Formulario para buscar cuentas"""
  busqueda = forms.CharField(
      required=False,
      widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Buscar por número de cuenta, cliente o documento...',
      })
  )
  tipo_cuenta = forms.ChoiceField(
      required=False,
      choices=[('', 'Todos')] + Cuenta.TIPO_CUENTA_CHOICES,
      widget=forms.Select(attrs={
        'class': 'form-select',
      })
  )
  estado = forms.ChoiceField(
      required=False,
      choices=[('', 'Todos')] + Cuenta.ESTADO_CHOICES,
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


class CerrarCuentaForm(forms.Form):
  """Formulario para confirmar cierre de cuenta"""
  confirmar = forms.BooleanField(
      required=True,
      label='Confirmo que deseo cerrar esta cuenta',
      widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input',
      }),
      help_text='Esta acción no se puede deshacer'
  )