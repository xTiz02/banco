🚀 Proyecto Banco - Django
📌 Requisitos previos

Tener instalado Python 3.10+

Tener instalado MySQL y crear la base de datos banco_db

Tener instalado pip para la gestión de dependencias

Editor recomendado: PyCharm

⚙️ Pasos para ejecutar el proyecto
1. Abrir el proyecto en PyCharm

Clona el repositorio y ábrelo con PyCharm para una mejor experiencia de desarrollo.

2. Crear carpeta estática

En la raíz del proyecto, crea la carpeta:

mkdir static

3. Crear la base de datos en MySQL

Ejecuta en tu MySQL local:

'CREATE DATABASE banco_db;'

4. Configurar credenciales en settings.py

Edita el archivo' banca/settings.py' y coloca las credenciales de tu MySQL local-

5. Instalar dependencias

Ejecuta en la raíz del proyecto:

'pip install -r requirements.txt'


Debe instalarse sin errores.

6. Crear migraciones
'python manage.py makemigrations'

7. Aplicar migraciones
'python manage.py migrate'

👥 Crear datos de ejemplo (opcional)
Abrir shell de Django
'python manage.py shell'

# Crear usuarios de prueba
from core.models import Usuario

admin = Usuario.objects.create(
    username='admin',
    email='admin@banco.com',
    tipo_usuario='ADMINISTRADOR',
    esta_activo=True,
    is_staff=True,
    is_superuser=True
)
admin.set_password('admin123')
admin.save()


empleado = Usuario.objects.create(
    username='empleado1',
    email='empleado1@banco.com',
    tipo_usuario='EMPLEADO',
    esta_activo=True
)
empleado.set_password('empleado123')
empleado.save()


from clientes.models import Cliente
from cuentas.models import Cuenta
from core.models import Usuario, TipoCambio
from django.utils import timezone
from decimal import Decimal

usuario = Usuario.objects.first()


TipoCambio.objects.create(
    fecha=timezone.now().date(),
    compra=Decimal('3.750'),
    venta=Decimal('3.755'),
    usuario_registro=usuario
)


cliente = Cliente.objects.create(
    tipo_cliente='NATURAL',
    tipo_documento='DNI',
    numero_documento='12345678',
    nombres='JUAN',
    apellido_paterno='PEREZ',
    apellido_materno='GARCIA',
    direccion='AV. PRUEBA 123',
    telefono='999888777',
    email='juan@example.com'
)


cuenta = Cuenta.objects.create(
    cliente=cliente,
    tipo_cuenta='AHORRO',
    moneda='SOLES',
    saldo=Decimal('1000.00'),
    usuario_apertura=usuario
)

# Ejecutar servidor
python manage.py runserver


El proyecto estará disponible en:
👉 http://localhost:8000
