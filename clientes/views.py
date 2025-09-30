from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q

from .models import Cliente, DatosReniec, DatosSunat
from .forms import ClienteForm, BuscarClienteForm
from .services import obtener_datos_reniec, obtener_datos_sunat


@login_required
def lista_clientes(request):
  """Vista para listar clientes"""
  clientes = Cliente.objects.all().order_by('-fecha_registro')

  # Búsqueda
  form = BuscarClienteForm(request.GET)
  if form.is_valid():
    busqueda = form.cleaned_data.get('busqueda')
    tipo_cliente = form.cleaned_data.get('tipo_cliente')

    if busqueda:
      clientes = clientes.filter(
          Q(codigo__icontains=busqueda) |
          Q(numero_documento__icontains=busqueda) |
          Q(nombres__icontains=busqueda) |
          Q(apellido_paterno__icontains=busqueda) |
          Q(apellido_materno__icontains=busqueda) |
          Q(razon_social__icontains=busqueda)
      )

    if tipo_cliente:
      clientes = clientes.filter(tipo_cliente=tipo_cliente)

  context = {
    'clientes': clientes,
    'form': form,
  }

  return render(request, 'clientes/lista.html', context)


@login_required
def crear_cliente(request):
  """Vista para registrar cliente"""
  if request.method == 'POST':
    form = ClienteForm(request.POST)
    if form.is_valid():
      try:
        with transaction.atomic():
          cliente = form.save(commit=False)
          tipo_documento = form.cleaned_data['tipo_documento']
          numero_documento = form.cleaned_data['numero_documento']

          # Consultar API según tipo de documento
          usar_mock = True  # Cambiar a False cuando tengas acceso a las APIs reales

          if tipo_documento == 'DNI':
            # Consultar RENIEC
            try:
              datos_reniec = obtener_datos_reniec(numero_documento, usar_mock)

              # Asignar datos de RENIEC al cliente
              cliente.nombres = datos_reniec['nombres']
              cliente.apellido_paterno = datos_reniec['apellido_paterno']
              cliente.apellido_materno = datos_reniec['apellido_materno']

              if not cliente.direccion:
                cliente.direccion = datos_reniec.get('direccion',
                                                     'No especificado')

              cliente.save()

              # Guardar datos de RENIEC
              DatosReniec.objects.create(
                  cliente=cliente,
                  dni=datos_reniec['dni'],
                  nombres=datos_reniec['nombres'],
                  apellido_paterno=datos_reniec['apellido_paterno'],
                  apellido_materno=datos_reniec['apellido_materno'],
                  fecha_nacimiento=datos_reniec.get('fecha_nacimiento'),
                  ubigeo=datos_reniec.get('ubigeo'),
                  direccion=datos_reniec.get('direccion')
              )

            except ValidationError as e:
              messages.warning(
                  request,
                  f'No se pudo consultar RENIEC: {str(e)}. Cliente registrado con datos manuales.'
              )
              cliente.save()

          elif tipo_documento == 'RUC':
            # Consultar SUNAT
            try:
              datos_sunat = obtener_datos_sunat(numero_documento, usar_mock)

              # Asignar datos de SUNAT al cliente
              cliente.razon_social = datos_sunat['razon_social']
              cliente.nombre_comercial = datos_sunat.get('nombre_comercial')

              if not cliente.direccion:
                cliente.direccion = datos_sunat.get('direccion',
                                                    'No especificado')

              cliente.save()

              # Guardar datos de SUNAT
              DatosSunat.objects.create(
                  cliente=cliente,
                  ruc=datos_sunat['ruc'],
                  razon_social=datos_sunat['razon_social'],
                  nombre_comercial=datos_sunat.get('nombre_comercial'),
                  tipo_contribuyente=datos_sunat.get('tipo_contribuyente'),
                  estado=datos_sunat.get('estado'),
                  condicion=datos_sunat.get('condicion'),
                  direccion=datos_sunat.get('direccion'),
                  departamento=datos_sunat.get('departamento'),
                  provincia=datos_sunat.get('provincia'),
                  distrito=datos_sunat.get('distrito')
              )

            except ValidationError as e:
              messages.warning(
                  request,
                  f'No se pudo consultar SUNAT: {str(e)}. Cliente registrado con datos manuales.'
              )
              cliente.save()

          messages.success(
              request,
              f'Cliente {cliente.get_nombre_completo()} registrado exitosamente con código {cliente.codigo}'
          )
          return redirect('clientes:detalle_cliente', cliente_id=cliente.id)

      except ValidationError as e:
        messages.error(request, f'Error al registrar cliente: {str(e)}')
      except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = ClienteForm()

  context = {
    'form': form,
    'accion': 'Registrar',
  }

  return render(request, 'clientes/form.html', context)


@login_required
def detalle_cliente(request, cliente_id):
  """Vista para ver detalles del cliente"""
  cliente = get_object_or_404(Cliente, pk=cliente_id)

  # Obtener cuentas del cliente
  cuentas = cliente.cuentas.all().order_by('-fecha_apertura')

  # Datos de RENIEC/SUNAT si existen
  datos_reniec = None
  datos_sunat = None

  if hasattr(cliente, 'datos_reniec'):
    datos_reniec = cliente.datos_reniec

  if hasattr(cliente, 'datos_sunat'):
    datos_sunat = cliente.datos_sunat

  context = {
    'cliente': cliente,
    'cuentas': cuentas,
    'datos_reniec': datos_reniec,
    'datos_sunat': datos_sunat,
  }

  return render(request, 'clientes/detalle.html', context)


@login_required
def editar_cliente(request, cliente_id):
  """Vista para editar cliente"""
  cliente = get_object_or_404(Cliente, pk=cliente_id)

  if request.method == 'POST':
    form = ClienteForm(request.POST, instance=cliente)
    if form.is_valid():
      try:
        cliente = form.save()
        messages.success(request,
                         f'Cliente {cliente.get_nombre_completo()} actualizado exitosamente.')
        return redirect('clientes:detalle_cliente', cliente_id=cliente.id)
      except ValidationError as e:
        messages.error(request, f'Error al actualizar cliente: {str(e)}')
      except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
    else:
      messages.error(request, 'Por favor corrija los errores en el formulario.')
  else:
    form = ClienteForm(instance=cliente)

  context = {
    'form': form,
    'cliente': cliente,
    'accion': 'Editar',
  }

  return render(request, 'clientes/form.html', context)


@login_required
def buscar_cliente_ajax(request):
  """Vista AJAX para buscar clientes"""
  from django.http import JsonResponse

  busqueda = request.GET.get('q', '')

  if len(busqueda) < 3:
    return JsonResponse({'clientes': []})

  clientes = Cliente.objects.filter(
      Q(codigo__icontains=busqueda) |
      Q(numero_documento__icontains=busqueda) |
      Q(nombres__icontains=busqueda) |
      Q(apellido_paterno__icontains=busqueda) |
      Q(apellido_materno__icontains=busqueda) |
      Q(razon_social__icontains=busqueda)
  ).filter(esta_activo=True)[:10]

  resultados = []
  for cliente in clientes:
    resultados.append({
      'id': cliente.id,
      'codigo': cliente.codigo,
      'nombre': cliente.get_nombre_completo(),
      'documento': f"{cliente.get_tipo_documento_display()}: {cliente.numero_documento}",
    })

  return JsonResponse({'clientes': resultados})