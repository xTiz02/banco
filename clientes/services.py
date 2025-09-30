import requests
from typing import Dict, Optional
from django.core.exceptions import ValidationError


class ReniecService:
  """Servicio para consultar datos de RENIEC"""

  def __init__(self):
    # En producción, estas URLs y tokens deben venir de variables de entorno
    self.base_url = "https://dniruc.apisperu.com/api/v1/dni"
    self.token = "TU_TOKEN_AQUI"  # Debe configurarse en .env

  def consultar_dni(self, dni: str) -> Optional[Dict]:
    """
    Consulta los datos de una persona por DNI

    Args:
        dni: Número de DNI de 8 dígitos

    Returns:
        Diccionario con los datos de la persona o None si no se encuentra

    Raises:
        ValidationError: Si hay un error en la consulta
    """
    try:
      # Validar formato de DNI
      if not dni or len(dni) != 8 or not dni.isdigit():
        raise ValidationError("El DNI debe tener 8 dígitos numéricos")

      # Realizar consulta a la API
      url = f"{self.base_url}/{dni}"
      headers = {
        'Authorization': f'Bearer {self.token}',
        'Content-Type': 'application/json'
      }

      response = requests.get(url, headers=headers, timeout=10)

      if response.status_code == 200:
        data = response.json()
        return self._procesar_respuesta_reniec(data)
      elif response.status_code == 404:
        raise ValidationError("DNI no encontrado en RENIEC")
      else:
        raise ValidationError(
          f"Error al consultar RENIEC: {response.status_code}")

    except requests.RequestException as e:
      # En caso de error de conexión, permitir registro manual
      raise ValidationError(f"Error de conexión con RENIEC: {str(e)}")
    except Exception as e:
      raise ValidationError(f"Error inesperado: {str(e)}")

  def _procesar_respuesta_reniec(self, data: Dict) -> Dict:
    """Procesa la respuesta de RENIEC y retorna datos estructurados"""
    return {
      'dni': data.get('dni', ''),
      'nombres': data.get('nombres', ''),
      'apellido_paterno': data.get('apellidoPaterno', ''),
      'apellido_materno': data.get('apellidoMaterno', ''),
      'fecha_nacimiento': data.get('fechaNacimiento', ''),
      'ubigeo': data.get('ubigeo', ''),
      'direccion': data.get('direccion', ''),
    }

  def consultar_dni_mock(self, dni: str) -> Dict:
    """
    Método mock para pruebas sin conexión real a RENIEC
    Úsalo en desarrollo cuando no tengas acceso a la API real
    """
    if not dni or len(dni) != 8 or not dni.isdigit():
      raise ValidationError("El DNI debe tener 8 dígitos numéricos")

    # Datos de prueba
    return {
      'dni': dni,
      'nombres': 'JUAN CARLOS',
      'apellido_paterno': 'PEREZ',
      'apellido_materno': 'GARCIA',
      'fecha_nacimiento': '1990-01-15',
      'ubigeo': '150101',
      'direccion': 'AV. EJEMPLO 123, LIMA',
    }


class SunatService:
  """Servicio para consultar datos de SUNAT"""

  def __init__(self):
    # En producción, estas URLs y tokens deben venir de variables de entorno
    self.base_url = "https://dniruc.apisperu.com/api/v1/ruc"
    self.token = "TU_TOKEN_AQUI"  # Debe configurarse en .env

  def consultar_ruc(self, ruc: str) -> Optional[Dict]:
    """
    Consulta los datos de una empresa por RUC

    Args:
        ruc: Número de RUC de 11 dígitos

    Returns:
        Diccionario con los datos de la empresa o None si no se encuentra

    Raises:
        ValidationError: Si hay un error en la consulta
    """
    try:
      # Validar formato de RUC
      if not ruc or len(ruc) != 11 or not ruc.isdigit():
        raise ValidationError("El RUC debe tener 11 dígitos numéricos")

      # Realizar consulta a la API
      url = f"{self.base_url}/{ruc}"
      headers = {
        'Authorization': f'Bearer {self.token}',
        'Content-Type': 'application/json'
      }

      response = requests.get(url, headers=headers, timeout=10)

      if response.status_code == 200:
        data = response.json()
        return self._procesar_respuesta_sunat(data)
      elif response.status_code == 404:
        raise ValidationError("RUC no encontrado en SUNAT")
      else:
        raise ValidationError(
          f"Error al consultar SUNAT: {response.status_code}")

    except requests.RequestException as e:
      # En caso de error de conexión, permitir registro manual
      raise ValidationError(f"Error de conexión con SUNAT: {str(e)}")
    except Exception as e:
      raise ValidationError(f"Error inesperado: {str(e)}")

  def _procesar_respuesta_sunat(self, data: Dict) -> Dict:
    """Procesa la respuesta de SUNAT y retorna datos estructurados"""
    return {
      'ruc': data.get('ruc', ''),
      'razon_social': data.get('razonSocial', ''),
      'nombre_comercial': data.get('nombreComercial', ''),
      'tipo_contribuyente': data.get('tipoContribuyente', ''),
      'estado': data.get('estado', ''),
      'condicion': data.get('condicion', ''),
      'direccion': data.get('direccion', ''),
      'departamento': data.get('departamento', ''),
      'provincia': data.get('provincia', ''),
      'distrito': data.get('distrito', ''),
    }

  def consultar_ruc_mock(self, ruc: str) -> Dict:
    """
    Método mock para pruebas sin conexión real a SUNAT
    Úsalo en desarrollo cuando no tengas acceso a la API real
    """
    if not ruc or len(ruc) != 11 or not ruc.isdigit():
      raise ValidationError("El RUC debe tener 11 dígitos numéricos")

    # Datos de prueba
    return {
      'ruc': ruc,
      'razon_social': 'EMPRESA DE PRUEBA S.A.C.',
      'nombre_comercial': 'PRUEBA COMERCIAL',
      'tipo_contribuyente': 'SOCIEDAD ANONIMA CERRADA',
      'estado': 'ACTIVO',
      'condicion': 'HABIDO',
      'direccion': 'AV. EMPRESARIAL 456',
      'departamento': 'LIMA',
      'provincia': 'LIMA',
      'distrito': 'MIRAFLORES',
    }


# Funciones de utilidad para usar en las vistas
def obtener_datos_reniec(dni: str, usar_mock: bool = False) -> Dict:
  """
  Función de utilidad para obtener datos de RENIEC

  Args:
      dni: Número de DNI
      usar_mock: Si True, usa datos de prueba en lugar de la API real

  Returns:
      Diccionario con los datos de la persona
  """
  service = ReniecService()
  if usar_mock:
    return service.consultar_dni_mock(dni)
  return service.consultar_dni(dni)


def obtener_datos_sunat(ruc: str, usar_mock: bool = False) -> Dict:
  """
  Función de utilidad para obtener datos de SUNAT

  Args:
      ruc: Número de RUC
      usar_mock: Si True, usa datos de prueba en lugar de la API real

  Returns:
      Diccionario con los datos de la empresa
  """
  service = SunatService()
  if usar_mock:
    return service.consultar_ruc_mock(ruc)
  return service.consultar_ruc(ruc)