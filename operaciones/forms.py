from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field
from decimal import Decimal
from django.conf import settings

from .models import Deposito, Retiro, Transferencia
from cuentas.models import Cuenta


class DepositoForm(forms.ModelForm):
  """Formulario para realizar depósito"""

  class Meta:
    model = Deposito
    fields = [
      'cuenta',
      'monto',
      'clave_autorizacion',
      'origen_fondos',
    ]
    widgets = {
      'cuenta': forms.Select(attrs={
        'class': 'form-select',
      }),
      'monto': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '0.00',
        'step': '0.01',
        'min': '0.01',
        'onchange': 'checkMontoDeposito()',
      }),
      'clave_autorizacion': forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Clave de autorización',
      }),
      'origen_fondos': forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 3,
        'placeholder': 'Describa el origen de los fondos',
      }),
    }
    labels = {
      'cuenta': 'Cuenta',
      'monto': 'Monto a Depositar',
      'clave_autorizacion': 'Clave de Autorización (requerida para montos > S/ 2000)',
      'origen_fondos': 'Origen de Fondos (requerido para montos > S/ 2000)',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Solo mostrar cuentas activas de ahorro y corriente
    self.fields['cuenta'].queryset = Cuenta.objects.filter(
        esta_activa=True,
        tipo_cuenta__in=['AHORRO', 'CORRIENTE']
    ).exclude(estado='CERRADA')

    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Realizar Depósito', css_class='btn btn-success'))


class RetiroForm(forms.ModelForm):
  """Formulario para realizar retiro"""

  class Meta:
    model = Retiro
    fields = [
      'cuenta',
      'monto',
    ]
    widgets = {
      'cuenta': forms.Select(attrs={
        'class': 'form-select',
        'onchange': 'mostrarSaldoDisponible()',
      }),
      'monto': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '0.00',
        'step': '0.01',
        'min': '0.01',
      }),
    }
    labels = {
      'cuenta': 'Cuenta',
      'monto': 'Monto a Retirar',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Solo mostrar cuentas activas de ahorro y corriente
    self.fields['cuenta'].queryset = Cuenta.objects.filter(
        esta_activa=True,
        tipo_cuenta__in=['AHORRO', 'CORRIENTE']
    ).exclude(estado='CERRADA')

    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Realizar Retiro', css_class='btn btn-warning'))


class TransferenciaForm(forms.ModelForm):
  """Formulario para realizar transferencia"""

  class Meta:
    model = Transferencia
    fields = [
      'cuenta_origen',
      'cuenta_destino',
      'monto_origen',
      'descripcion',
    ]
    widgets = {
      'cuenta_origen': forms.Select(attrs={
        'class': 'form-select',
        'onchange': 'mostrarSaldoOrigen()',
      }),
      'cuenta_destino': forms.Select(attrs={
        'class': 'form-select',
      }),
      'monto_origen': forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '0.00',
        'step': '0.01',
        'min': '0.01',
      }),
      'descripcion': forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 2,
        'placeholder': 'Descripción de la transferencia (opcional)',
      }),
    }
    labels = {
      'cuenta_origen': 'Cuenta Origen',
      'cuenta_destino': 'Cuenta Destino',
      'monto_origen': 'Monto a Transferir',
      'descripcion': 'Descripción',
    }

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Solo mostrar cuentas activas de ahorro y corriente
    queryset_cuentas = Cuenta.objects.filter(
        esta_activa=True,
        tipo_cuenta__in=['AHORRO', 'CORRIENTE']
    ).exclude(estado='CERRADA').select_related('cliente')

    self.fields['cuenta_origen'].queryset = queryset_cuentas
    self.fields['cuenta_destino'].queryset = queryset_cuentas

    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Realizar Transferencia', css_class='btn btn-primary'))

  def clean(self):
    cleaned_data = super().clean()
    cuenta_origen = cleaned_data.get('cuenta_origen')
    cuenta_destino = cleaned_data.get('cuenta_destino')

    if cuenta_origen and cuenta_destino:
      if cuenta_origen == cuenta_destino:
        raise ValidationError(
          'La cuenta origen y destino no pueden ser la misma')

    return cleaned_data


class CancelarPlazoForm(forms.Form):
  """Formulario para confirmar cancelación de plazo fijo"""
  confirmar = forms.BooleanField(
      required=True,
      label='Confirmo que deseo cancelar este plazo fijo',
      widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input',
      }),
      help_text='Se calculará el interés generado hasta la fecha y se cerrará la cuenta'
  )


class RenovarPlazoForm(forms.Form):
  """Formulario para renovar plazo fijo"""
  nuevo_plazo_meses = forms.IntegerField(
      label='Nuevo Plazo (meses)',
      min_value=1,
      widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '12',
      }),
      help_text='Cantidad de meses del nuevo plazo'
  )
  nueva_tasa_interes = forms.DecimalField(
      label='Nueva Tasa de Interés Mensual (%)',
      max_digits=5,
      decimal_places=2,
      min_value=Decimal('0.01'),
      widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': '0.50',
        'step': '0.01',
      }),
      help_text='Tasa de interés mensual en porcentaje'
  )

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.helper = FormHelper()
    self.helper.form_method = 'post'
    self.helper.add_input(
      Submit('submit', 'Renovar Plazo Fijo', css_class='btn btn-success'))