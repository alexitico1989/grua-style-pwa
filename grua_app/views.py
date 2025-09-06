# Agregar estos imports después de los imports existentes
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.admin.views.decorators import staff_member_required
import uuid
import traceback
import json

# Imports de Transbank
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.integration_type import IntegrationType
from datetime import timedelta


try:
    from transbank.common.options import WebpayOptions
    WEBPAY_OPTIONS_AVAILABLE = True
except ImportError:
    print("⚠️ WebpayOptions no disponible")
    WEBPAY_OPTIONS_AVAILABLE = False

# Imports de modelos y email - ACTUALIZADO CON EditarPerfilForm y MEMBRESÍAS
from .forms import SolicitudServicioForm, CustomUserCreationForm, EditarPerfilForm
from .models import SolicitudServicio, CodigoVerificacion, TipoMembresia, Membresia, PagoMembresia

# 🆕 IMPORTS MERCADO PAGO - AGREGAR DESPUÉS DE LA LÍNEA 25
try:
    from .models import MercadoPagoPayment
    MERCADOPAGO_MODELS_AVAILABLE = True
except ImportError:
    print("⚠️ MercadoPagoPayment model no disponible")
    MERCADOPAGO_MODELS_AVAILABLE = False

# Imports de email - con manejo de errores
try:
    from .email_utils import enviar_email_bienvenida, enviar_codigo_reset_password, verificar_codigo_reset, enviar_comprobante_solicitud, enviar_actualizacion_estado, format_local_datetime, format_service_datetime
    EMAIL_UTILS_AVAILABLE = True
except ImportError:
    print("⚠️ email_utils no disponible")
    EMAIL_UTILS_AVAILABLE = False

# Imports de PDF
try:
    from .pdf_utils import generar_pdf_solicitud, generar_pdf_comprobante
    PDF_UTILS_AVAILABLE = True
except ImportError:
    print("⚠️ pdf_utils no disponible")
    PDF_UTILS_AVAILABLE = False

try:
    from .models import HistorialPago
    HISTORIAL_PAGO_AVAILABLE = True
except ImportError:
    print("⚠️ HistorialPago no encontrado")
    HISTORIAL_PAGO_AVAILABLE = False

def obtener_tarifas_usuario(user):
    """
    Obtiene las tarifas aplicables según la membresía activa del usuario
    Retorna: dict con tarifa_base, tarifa_por_km, tarifa_minima
    """
    # Tarifas por defecto (sin membresía)
    tarifas_default = {
        'tarifa_base': 30000,
        'tarifa_por_km': 1500,
        'tarifa_minima': 30000,
        'tiene_membresia': False,
        'tipo_membresia': None
    }
    
    try:
        # Buscar membresía activa del usuario
        membresia_activa = Membresia.objects.filter(
            usuario=user,
            estado='activa'
        ).first()
        
        if membresia_activa and membresia_activa.esta_activa:
            # Definir tarifas según tipo de membresía
            tarifas_membresias = {
                'basica': {
                    'tarifa_base': 25000,
                    'tarifa_por_km': 1300,
                    'tarifa_minima': 25000,
                },
                'pro': {
                    'tarifa_base': 20000,
                    'tarifa_por_km': 1300,
                    'tarifa_minima': 0,  # Sin tarifa mínima
                },
                'premium': {
                    'tarifa_base': 20000,
                    'tarifa_por_km': 1200,
                    'tarifa_minima': 0,  # Sin tarifa mínima
                }
            }
            
            tipo_membresia = membresia_activa.tipo_membresia.nombre
            
            if tipo_membresia in tarifas_membresias:
                tarifas = tarifas_membresias[tipo_membresia].copy()
                tarifas['tiene_membresia'] = True
                tarifas['tipo_membresia'] = tipo_membresia
                tarifas['membresia'] = membresia_activa
                
                print(f"✅ Tarifas de membresía aplicadas para {user.username}: {tipo_membresia}")
                print(f"   Base: ${tarifas['tarifa_base']}, Km: ${tarifas['tarifa_por_km']}, Mín: ${tarifas['tarifa_minima']}")
                
                return tarifas
                
    except Exception as e:
        print(f"❌ Error obteniendo tarifas de usuario {user.username}: {e}")
    
    print(f"🔄 Usando tarifas estándar para {user.username}")
    return tarifas_default

def formatear_fechas_solicitud(solicitud):
    """Formatea las fechas de una solicitud para mostrar correctamente"""
    fecha_servicio_corregida = solicitud.fecha_servicio - timedelta(hours=4)
    solicitud.fecha_servicio_formateada = fecha_servicio_corregida.strftime('%d/%m/%Y %H:%M')
    solicitud.fecha_solicitud_formateada = format_local_datetime(solicitud.fecha_solicitud)
    return solicitud

def get_webpay_options():
    try:
        if WEBPAY_OPTIONS_AVAILABLE:
            if settings.TRANSBANK_ENVIRONMENT == 'integration':
                return WebpayOptions(
                    commerce_code='597055555532',
                    api_key='579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C',
                    integration_type=IntegrationType.TEST
                )
            else:
                return WebpayOptions(
                    commerce_code=settings.TRANSBANK_COMMERCE_CODE,
                    api_key=settings.TRANSBANK_API_KEY,
                    integration_type=IntegrationType.LIVE
                )
        else:
            print("🔄 Usando configuración manual")
            return None
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return None
def home(request):
    """Vista home con datos de membresías para el popup"""
    # Obtener membresía activa del usuario si está autenticado
    membresia_activa = None
    if request.user.is_authenticated:
        try:
            membresia_activa = Membresia.objects.filter(
                usuario=request.user,
                estado='activa'
            ).first()
        except Exception as e:
            print(f"❌ Error obteniendo membresía en home: {e}")
    
    # Definir datos de planes con estructura completa (igual que en pago_membresia)
    planes_data = {
        'basica': {
            'nombre': 'Básica',
            'duraciones': {
                '3': {
                    'precio': 59990,
                    'precio_mensual': 19997,  # 59990 / 3
                    'detalles': [
                        'Servicio 24/7',
                        '2 servicios incluidos por mes',
                        'Descuento 10% en servicios extra',
                        'Soporte básico',
                        'Tarifa base: $25.000',
                        'Tarifa x Km: $1.300'
                    ],
                    'periodo': '3 meses'
                },
                '6': {
                    'precio': 109990,
                    'precio_mensual': 18332,  # 109990 / 6
                    'detalles': [
                        'Servicio 24/7',
                        '1 Viaje Gratis región metropolitana',
                        '2 servicios incluidos por mes', 
                        'Descuento 10% en servicios extra',
                        'Soporte básico',
                        'Tarifa base: $25.000',
                        'Tarifa x Km: $1.300'
                    ],
                    'periodo': '6 meses'
                },
                '12': {
                    'precio': 199990,
                    'precio_mensual': 16666,  # 199990 / 12
                    'detalles': [
                        'Servicio 24/7',
                        '3 Viajes Gratis región metropolitana',
                        '2 servicios incluidos por mes',
                        'Descuento 10% en servicios extra', 
                        'Soporte básico',
                        'Tarifa base: $25.000',
                        'Tarifa x Km: $1.300'
                    ],
                    'periodo': '1 año'
                }
            }
        },
        'pro': {
            'nombre': 'Pro',
            'duraciones': {
                '3': {
                    'precio': 99990,
                    'precio_mensual': 33330,  # 99990 / 3
                    'detalles': [
                        'Servicio 24/7 prioritario',
                        '1 Viaje a mitad de precio región metropolitana',
                        '5 servicios incluidos por mes',
                        'Descuento 20% en servicios extra',
                        'Soporte premium',
                        'Tarifa base: $20.000',
                        'Tarifa x Km: $1.300',
                        'Sin tarifa mínima'
                    ],
                    'periodo': '3 meses'
                },
                '6': {
                    'precio': 189990,
                    'precio_mensual': 31665,  # 189990 / 6
                    'detalles': [
                        'Servicio 24/7 prioritario',
                        '2 viajes gratis región metropolitana',
                        '5 servicios incluidos por mes',
                        'Descuento 20% en servicios extra',
                        'Soporte premium',
                        'Tarifa base: $20.000',
                        'Tarifa x Km: $1.300',
                        'Sin tarifa mínima'
                    ],
                    'periodo': '6 meses'
                },
                '12': {
                    'precio': 349000,
                    'precio_mensual': 29083,  # 349000 / 12
                    'detalles': [
                        'Servicio 24/7 prioritario',
                        '5 viajes gratis región metropolitana',
                        'Un servicio de revisión técnica a domicilio',
                        '5 servicios incluidos por mes',
                        'Descuento 20% en servicios extra',
                        'Soporte premium',
                        'Taza de regalo',
                        'Tarifa base: $20.000',
                        'Tarifa x Km: $1.300',
                        'Sin tarifa mínima'
                    ],
                    'periodo': '1 año'
                }
            }
        },
        'premium': {
            'nombre': 'Premium',
            'duraciones': {
                '3': {
                    'precio': 299000,
                    'precio_mensual': 99667,  # 299000 / 3
                    'detalles': [
                        'Servicio exclusivo 24/7',
                        '2 viajes gratis región metropolitana',
                        '2 viajes precio fijo $20.000 toda RM',
                        'Servicios ilimitados por mes',
                        'Descuento 30% en servicios extra',
                        'Soporte VIP dedicado',
                        'Seguimiento GPS avanzado',
                        'Tarifa base: $20.000',
                        'Tarifa x Km: $1.200',
                        'Sin tarifa mínima'
                    ],
                    'periodo': '3 meses'
                },
                '6': {
                    'precio': 549000,
                    'precio_mensual': 91500,  # 549000 / 6
                    'detalles': [
                        'Servicio exclusivo 24/7',
                        '4 viajes gratis región metropolitana',
                        '3 viajes precio fijo $20.000 toda RM',
                        'Servicios ilimitados por mes',
                        'Descuento 30% en servicios extra',
                        'Soporte VIP dedicado',
                        'Seguimiento GPS avanzado',
                        'Tarifa base: $20.000',
                        'Tarifa x Km: $1.200',
                        'Sin tarifa mínima'
                    ],
                    'periodo': '6 meses'
                },
                '12': {
                    'precio': 999000,
                    'precio_mensual': 83250,  # 999000 / 12
                    'detalles': [
                        'Servicio exclusivo 24/7',
                        '10 viajes gratis región metropolitana',
                        '10 viajes precio fijo $20.000 toda RM',
                        'Un servicio de revisión técnica a domicilio',
                        'Servicios ilimitados por mes',
                        'Descuento 30% en servicios extra',
                        'Soporte VIP dedicado',
                        'Beneficios exclusivos',
                        'Seguimiento GPS avanzado',
                        'Taza de regalo',
                        'Asistencia prioritaria',
                        'Tarifa base: $20.000',
                        'Tarifa x Km: $1.200',
                        'Sin tarifa mínima'
                    ],
                    'periodo': '1 año'
                }
            }
        }
    }
    
    context = {
        'membresia_activa': membresia_activa,
        'planes_data': json.dumps(planes_data)  # Convertir a JSON para JavaScript
    }
    
    return render(request, 'grua_app/home.html', context)
# ===== NUEVAS VISTAS PARA LAS PÁGINAS ADICIONALES =====

def servicios(request):
    """Vista para la página de servicios"""
    return render(request, 'grua_app/servicios.html')


def precios(request):
    """Vista para la página de precios"""
    return render(request, 'grua_app/precios.html')


def contacto(request):
    """Vista para la página de contacto"""
    return render(request, 'grua_app/contacto.html')


# ===== RESTO DE VISTAS EXISTENTES (SIN MODIFICAR) =====

def custom_logout(request):
    from django.contrib.auth import logout
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'Sesión cerrada')
    return redirect('home')


def custom_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenido {user.username}')
            return redirect('dashboard')
        else:
            messages.error(request, 'Credenciales incorrectas')

    from django.contrib.auth.forms import AuthenticationForm
    form = AuthenticationForm()
    context = {'form': form}
    return render(request, 'grua_app/login.html', context)


def registro(request):
    """Vista de registro de usuarios con email de bienvenida"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            email = form.cleaned_data.get('email')
            telefono = form.cleaned_data.get('telefono')

            print(f"✅ Usuario creado exitosamente: {username}")
            print(f"   Email: {email}")
            print(f"   Teléfono: {telefono}")

            # Enviar email de bienvenida
            if user.email and EMAIL_UTILS_AVAILABLE:
                try:
                    email_enviado = enviar_email_bienvenida(user)
                    if email_enviado:
                        messages.success(
                            request, f'✅ Cuenta creada exitosamente! Te hemos enviado un email de bienvenida a {user.email}')
                    else:
                        messages.success(
                            request, f'✅ Cuenta creada exitosamente para {username}!')
                        messages.info(
                            request, '📧 El email de bienvenida se enviará próximamente.')
                except Exception as e:
                    print(f"⚠️ Error enviando email: {e}")
                    messages.success(
                        request, f'✅ Cuenta creada exitosamente para {username}!')
                    messages.info(
                        request, '📧 El email de bienvenida se enviará próximamente.')
            else:
                messages.success(
                    request, f'✅ Cuenta creada exitosamente para {username}!')

            # Autenticar automáticamente al usuario
            login(request, user)
            return redirect('dashboard')
        else:
            print("❌ Errores en formulario de registro:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'grua_app/registro.html', {'form': form})


@login_required
def dashboard(request):
   try:
       from .models import Cliente
       from .email_utils import format_local_datetime
       
       cliente, created = Cliente.objects.get_or_create(
           user=request.user,
           defaults={'telefono': ''}
       )
       
       solicitudes_raw = SolicitudServicio.objects.filter(
           cliente=request.user).order_by('-fecha_solicitud')[:5]
       
       # Formatear fechas para mostrar correctamente en el template
       solicitudes = []
       for solicitud in solicitudes_raw:
           solicitud = formatear_fechas_solicitud(solicitud)
           # Corregir desfase de fecha_servicio restando 4 horas
           fecha_servicio_corregida = solicitud.fecha_servicio - timedelta(hours=4)
           solicitud.fecha_servicio_formateada = fecha_servicio_corregida.strftime('%d/%m/%Y %H:%M')
           solicitud.fecha_solicitud_formateada = format_local_datetime(solicitud.fecha_solicitud)
           
           # Calcular precio usando tarifas de membresía actual del usuario
           if not hasattr(solicitud, 'costo_total') or not solicitud.costo_total:
               tarifas = obtener_tarifas_usuario(request.user)
               tarifa_base = tarifas['tarifa_base']
               tarifa_por_km = tarifas['tarifa_por_km']
               tarifa_minima = tarifas['tarifa_minima']
               
               if solicitud.distancia_km:
                   costo_km = float(solicitud.distancia_km) * tarifa_por_km
                   solicitud.total = max(tarifa_base + costo_km, tarifa_minima)
               else:
                   solicitud.total = tarifa_minima
           else:
               solicitud.total = solicitud.costo_total
           
           solicitudes.append(solicitud)
           
   except:
       solicitudes = []
   
   # AGREGAR ESTA PARTE - obtener membresía activa
   membresia_activa = None
   try:
       membresia_activa = Membresia.objects.filter(
           usuario=request.user,
           estado='activa'
       ).first()
   except Exception as e:
       print(f"❌ Error obteniendo membresía: {e}")
   
   # Obtener tarifas según membresía del usuario para mostrar en el dashboard
   tarifas_usuario = obtener_tarifas_usuario(request.user)

   context = {
       'solicitudes': solicitudes,
       'membresia_activa': membresia_activa,
       'tarifa_base': tarifas_usuario['tarifa_base'],
       'tarifa_por_km': tarifas_usuario['tarifa_por_km'],
       'tiene_membresia': tarifas_usuario['tiene_membresia'],
       'tipo_membresia': tarifas_usuario.get('tipo_membresia', None),
   }
   return render(request, 'grua_app/dashboard.html', context)

@login_required
def historial_servicios(request):
    """Vista específica para el historial completo de servicios"""
    try:
        from .models import Cliente
        from .email_utils import format_local_datetime
        
        cliente, created = Cliente.objects.get_or_create(
            user=request.user,
            defaults={'telefono': ''}
        )
        
        # Obtener TODAS las solicitudes del usuario ordenadas por fecha
        solicitudes_raw = SolicitudServicio.objects.filter(
            cliente=request.user
        ).order_by('-fecha_solicitud')
        
        # Formatear fechas para mostrar correctamente en el template
        solicitudes = []
        for solicitud in solicitudes_raw:
            solicitud = formatear_fechas_solicitud(solicitud)
            # Corregir desfase de fecha_servicio restando 4 horas
            fecha_servicio_corregida = solicitud.fecha_servicio - timedelta(hours=4)
            solicitud.fecha_servicio_formateada = fecha_servicio_corregida.strftime('%d/%m/%Y %H:%M')
            solicitud.fecha_solicitud_formateada = format_local_datetime(solicitud.fecha_solicitud)
            
            # Calcular precio usando tarifas de membresía actual del usuario
            if not hasattr(solicitud, 'costo_total') or not solicitud.costo_total:
                tarifas = obtener_tarifas_usuario(request.user)
                tarifa_base = tarifas['tarifa_base']
                tarifa_por_km = tarifas['tarifa_por_km']
                tarifa_minima = tarifas['tarifa_minima']
                
                if solicitud.distancia_km:
                    costo_km = float(solicitud.distancia_km) * tarifa_por_km
                    solicitud.total = max(tarifa_base + costo_km, tarifa_minima)
                else:
                    solicitud.total = tarifa_minima
            else:
                solicitud.total = solicitud.costo_total
            
            solicitudes.append(solicitud)
        
        print(f"🔍 HISTORIAL DEBUG:")
        print(f"   Usuario: {request.user.username}")
        print(f"   Total solicitudes encontradas: {len(solicitudes)}")
        
        for sol in solicitudes:
            print(f"   - {sol.numero_orden}: {sol.estado} | {sol.marca_vehiculo} {sol.modelo_vehiculo}")
            
    except Exception as e:
        print(f"❌ Error en historial_servicios: {e}")
        solicitudes = []
    
    context = {
        'solicitudes': solicitudes,
        'total_solicitudes': len(solicitudes) if solicitudes else 0
    }
    return render(request, 'grua_app/historial_servicios.html', context)

@login_required
def solicitar_servicio(request):
    """Vista de solicitar servicio con procesamiento directo de pago"""
    try:
        from .models import Cliente
        cliente, created = Cliente.objects.get_or_create(
            user=request.user,
            defaults={'telefono': ''}
        )
    except Exception as e:
        messages.error(request, 'Error al acceder al perfil del cliente.')
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = SolicitudServicioForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.cliente = request.user
            solicitud.marca_vehiculo = form.cleaned_data.get('marca_vehiculo', '')
            solicitud.modelo_vehiculo = form.cleaned_data.get('modelo_vehiculo', '')
            solicitud.placa_vehiculo = form.cleaned_data.get('placa_vehiculo', '')
            solicitud.tipo_vehiculo = form.cleaned_data.get('tipo_vehiculo', '')
            # MARCAR COMO SERVICIO DE GRÚA
            solicitud.tipo_servicio_categoria = request.POST.get('tipo_servicio_categoria', 'grua')
            print(f"DEBUG FORM DATA:")
            print(f"   form.cleaned_data completo: {form.cleaned_data}")
            print(f"   POST data: {request.POST}")
            print(f"   Marca desde form: '{form.cleaned_data.get('marca_vehiculo', 'NO ENCONTRADO')}'")
            print(f"   Modelo desde form: '{form.cleaned_data.get('modelo_vehiculo', 'NO ENCONTRADO')}'")
            print(f"   Placa desde form: '{form.cleaned_data.get('placa_vehiculo', 'NO ENCONTRADO')}'")
            print(f"   Tipo desde form: '{form.cleaned_data.get('tipo_vehiculo', 'NO ENCONTRADO')}'")
                    
            # Obtener método de pago seleccionado
            metodo_pago = form.cleaned_data['metodo_pago']
            solicitud.metodo_pago = metodo_pago
            
            # Calcular costo total usando tarifas de membresía
            tarifas = obtener_tarifas_usuario(request.user)
            tarifa_base = tarifas['tarifa_base']
            tarifa_por_km = tarifas['tarifa_por_km']
            tarifa_minima = tarifas['tarifa_minima']

            print(f"🔍 Aplicando tarifas para {request.user.username}:")
            print(f"   Base: ${tarifa_base}, Km: ${tarifa_por_km}, Mín: ${tarifa_minima}")
            if tarifas['tiene_membresia']:
                print(f"   ✅ Membresía {tarifas['tipo_membresia']} aplicada")

            if solicitud.distancia_km:
                costo_km = float(solicitud.distancia_km) * tarifa_por_km
                costo_total = max(tarifa_base + costo_km, tarifa_minima)
            else:
                costo_total = tarifa_minima
            
            solicitud.costo_total = costo_total
            solicitud.save()
            # Guardar tarifas aplicadas para el desglose
            solicitud.tarifa_base_aplicada = tarifa_base
            solicitud.tarifa_km_aplicada = tarifa_por_km
            
            if solicitud.fecha_servicio:
                solicitud.fecha_servicio = solicitud.fecha_servicio - timedelta(hours=4)
                solicitud.save()
                # Enviar notificación inmediata al administrador
                try:
                    from .notifications import enviar_notificacion_nueva_solicitud
                    enviar_notificacion_nueva_solicitud(solicitud)
                except Exception as e:
                    print(f"Error enviando notificación: {e}")

            # 📧 Enviar email de comprobante
            if EMAIL_UTILS_AVAILABLE:
                try:
                    email_enviado = enviar_comprobante_solicitud(solicitud)
                    if not email_enviado:
                        print("⚠️ No se pudo enviar el comprobante por email")
                except Exception as e:
                    print(f"⚠️ Error enviando comprobante: {e}")

            # 🔄 Procesando pago - Método de pago tradicional
            print(f"🔄 Procesando pago - Método: {metodo_pago}")

            # Métodos tradicionales que funcionan
            if metodo_pago == 'efectivo':
                return procesar_efectivo_directo(request, solicitud)
            elif metodo_pago == 'transferencia':
                return procesar_transferencia_directo(request, solicitud)
            elif metodo_pago == 'mercadopago_card':
                # Marcar como procesando_pago desde el inicio
                solicitud.estado = 'procesando_pago'
                solicitud.save()
                messages.info(request, 'Redirigiendo al sistema de pago con Mercado Pago...')
                return redirect('payment_selection', solicitud_id=solicitud.id)
            elif metodo_pago == 'webpay':
                return iniciar_pago_webpay_directo(request, solicitud)
            else:
                messages.error(request, 'Método de pago no válido.')
                return redirect('dashboard')
            
        else:
            print("❌ Errores en formulario de solicitud:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
    else:
        form = SolicitudServicioForm()

    # Obtener tarifas según membresía del usuario para mostrar en el formulario
    tarifas_usuario = obtener_tarifas_usuario(request.user)

    context = {
        'form': form,
        'tarifa_base': tarifas_usuario['tarifa_base'],
        'tarifa_por_km': tarifas_usuario['tarifa_por_km'],
        'tiene_membresia': tarifas_usuario['tiene_membresia'],
        'tipo_membresia': tarifas_usuario.get('tipo_membresia', None),
    }

    return render(request, 'grua_app/solicitar_servicio.html', context)


# ===== NUEVA VISTA DE ASISTENCIA MECÁNICA =====

@login_required
def solicitar_asistencia(request):
    """Vista de solicitar asistencia mecánica con procesamiento directo de pago"""
    try:
        from .models import Cliente
        cliente, created = Cliente.objects.get_or_create(
            user=request.user,
            defaults={'telefono': ''}
        )
    except Exception as e:
        messages.error(request, 'Error al acceder al perfil del cliente.')
        return redirect('dashboard')
        
    if request.method == 'POST':
        # Usar el mismo formulario pero marcando como servicio de asistencia
        form = SolicitudServicioForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.cliente = request.user
            
            # MARCAR COMO SERVICIO DE ASISTENCIA MECÁNICA
            # MARCAR COMO SERVICIO DE ASISTENCIA MECÁNICA
            solicitud.tipo_servicio_categoria = request.POST.get('tipo_servicio_categoria', 'asistencia')

            solicitud.marca_vehiculo = form.cleaned_data.get('marca_vehiculo', '')
            solicitud.modelo_vehiculo = form.cleaned_data.get('modelo_vehiculo', '')
            solicitud.placa_vehiculo = form.cleaned_data.get('placa_vehiculo', '')
            solicitud.tipo_vehiculo = form.cleaned_data.get('tipo_vehiculo', '')
            
            # Obtener método de pago seleccionado
            metodo_pago = form.cleaned_data['metodo_pago']
            solicitud.metodo_pago = metodo_pago
            
            # Calcular costo total para asistencia mecánica con tarifas de membresía
            tarifas = obtener_tarifas_usuario(request.user)

            # Para asistencia mecánica: tarifa fija de $30.000 sin descuentos por membresía
            costo_total = 30000
            print(f"🔧 Asistencia mecánica: Tarifa fija ${costo_total}")

            solicitud.costo_total = costo_total
            # Corregir zona horaria de fecha_servicio
            #if solicitud.fecha_servicio:
                #from datetime import timedelta
                # Restar 4 horas para corregir el desfase
                #solicitud.fecha_servicio = solicitud.fecha_servicio - timedelta(hours=4)

            solicitud.costo_total = costo_total
            solicitud.save()
            solicitud.save()
            # Para asistencia mecánica, guardar tarifas estándar
            solicitud.tarifa_base_aplicada = 30000
            solicitud.tarifa_km_aplicada = 0  # Asistencia no usa tarifa por km
        if solicitud.fecha_servicio:
            solicitud.fecha_servicio = solicitud.fecha_servicio - timedelta(hours=4)
            solicitud.save()
            # Enviar notificación inmediata al administrador
            try:
                from .notifications import enviar_notificacion_nueva_solicitud
                enviar_notificacion_nueva_solicitud(solicitud)
            except Exception as e:
                print(f"Error enviando notificación: {e}")

            # 📧 Enviar email de comprobante
            if EMAIL_UTILS_AVAILABLE:
                try:
                    email_enviado = enviar_comprobante_solicitud(solicitud)
                    if not email_enviado:
                        print("⚠️ No se pudo enviar el comprobante por email")
                except Exception as e:
                    print(f"⚠️ Error enviando comprobante: {e}")

            # DEBUG - Verificar estado de la solicitud de asistencia
            print(f"🔧 DEBUG ASISTENCIA - ANTES DE PAGO:")
            print(f"   ID: {solicitud.id}")
            print(f"   Orden: {solicitud.numero_orden}")
            print(f"   Estado: '{solicitud.estado}'")
            print(f"   Método: '{solicitud.metodo_pago}'")
            print(f"   Tipo: '{solicitud.tipo_servicio_categoria}'")
            print(f"   Fecha creación: {solicitud.fecha_solicitud}")

            # REDIRIGIR DIRECTAMENTE SEGÚN EL MÉTODO DE PAGO
            # 🆕 REDIRIGIR SEGÚN EL MÉTODO DE PAGO
            print(f"🔄 Procesando pago - Método: {metodo_pago}")

            # REDIRIGIR DIRECTAMENTE SEGÚN EL MÉTODO DE PAGO
                            # 🆕 REDIRIGIR SEGÚN EL MÉTODO DE PAGO
            print(f"🔄 Procesando pago - Método: {metodo_pago}")

            if metodo_pago == 'efectivo':
                # Cambiar estado a confirmada para efectivo
                solicitud.estado = 'confirmada'
                solicitud.save()
                # Redirigir a confirmación de efectivo
                return redirect('confirmacion_efectivo', solicitud_id=solicitud.id)
                
            elif metodo_pago == 'transferencia':
                # Cambiar estado a pendiente_confirmacion para transferencia
                solicitud.estado = 'pendiente_confirmacion'
                solicitud.save()
                # Redirigir a confirmación de transferencia
                return redirect('confirmacion_transferencia', solicitud_id=solicitud.id)
                
            elif metodo_pago == 'mercadopago_card':
                # Redirigir a checkout de Mercado Pago
                return redirect('mercadopago_checkout', solicitud_id=solicitud.id)
                
            elif metodo_pago == 'mercadopago_transfer':
                # Redirigir a transferencia de Mercado Pago
                return redirect('bank_transfer_mp', solicitud_id=solicitud.id)
                
            elif metodo_pago == 'webpay':
                return iniciar_pago_webpay_directo(request, solicitud)
                
            else:
                messages.error(request, 'Método de pago no válido.')
                return redirect('dashboard')
            
        else:
            print("❌ Errores en formulario de asistencia:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
    else:
        form = SolicitudServicioForm()

    return render(request, 'grua_app/solicitar_asistencia.html', {'form': form})
# ===== NUEVAS FUNCIONES DE PAGO DIRECTO PARA ASISTENCIA =====

def procesar_efectivo_directo_asistencia(request, solicitud):
    """Procesa pago en efectivo directamente para asistencia mecánica"""
    try:
        print(f"🔧💵 Procesando efectivo directo asistencia para solicitud {solicitud.numero_orden}")
        
        # Actualizar estado anterior para envío de email
        estado_anterior = solicitud.estado
        
        solicitud.estado = 'confirmada'
        solicitud.save()

        messages.success(
            request, 
            f'✅ Solicitud {solicitud.numero_orden} creada y confirmada para pago en efectivo. '
            f'Total a pagar: ${int(solicitud.costo_total):,}'
        )

        return redirect('confirmacion_efectivo', solicitud_id=solicitud.id)
        
    except Exception as e:
        print(f"❌ Error procesando efectivo directo asistencia: {e}")
        messages.error(request, 'Error al procesar el pago en efectivo.')
        return redirect('dashboard')


def procesar_transferencia_directo_asistencia(request, solicitud):
    """Procesa transferencia bancaria directamente para asistencia mecánica"""
    try:
        print(f"🔧🏦 Procesando transferencia directa asistencia para solicitud {solicitud.numero_orden}")
        
        # Actualizar estado anterior para envío de email
        estado_anterior = solicitud.estado
        
        solicitud.estado = 'pendiente_confirmacion'
        solicitud.save()
        
        # Enviar email de actualización de estado
        
        messages.success(
            request, 
            f'✅ Solicitud de asistencia mecánica {solicitud.numero_orden} creada para transferencia bancaria. '
            f'Total a transferir: ${int(solicitud.costo_total):,}'
        )
        
        return redirect('confirmacion_transferencia_asistencia', solicitud_id=solicitud.id)
        
    except Exception as e:
        print(f"❌ Error procesando transferencia directa asistencia: {e}")
        messages.error(request, 'Error al procesar la transferencia.')
        return redirect('dashboard')


def iniciar_pago_webpay_directo_asistencia(request, solicitud):
    """Inicia pago con WebPay directamente para asistencia mecánica"""
    try:
        print(f"🔧💳 Procesando WebPay directo asistencia para solicitud {solicitud.numero_orden}")
        
        # Verificar si Transbank está disponible
        if not WEBPAY_OPTIONS_AVAILABLE:
            messages.error(
                request, 
                '⚠️ Pago con tarjeta temporalmente no disponible. '
                'Contacta al administrador o solicita nuevamente con otro método de pago.'
            )
            return redirect('dashboard')
        
        monto_total = int(solicitud.costo_total)
        buy_order = f"AS{solicitud.numero_orden}{int(timezone.now().timestamp())}"  # AS = Asistencia
        session_id = str(uuid.uuid4())
        return_url = request.build_absolute_uri('/webpay/return/')
        
        print(f"🔄 Iniciando pago Transbank directo asistencia:")
        print(f"   Solicitud: {solicitud.numero_orden}")
        print(f"   Monto: ${monto_total}")
        print(f"   Orden: {buy_order}")
        
        options = get_webpay_options()
        
        if options:
            transaction = Transaction(options)
        else:
            transaction = Transaction()
        
        response = transaction.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=monto_total,
            return_url=return_url
        )
        
        if hasattr(response, 'token'):
            token = response.token
            url = response.url
        elif isinstance(response, dict):
            token = response.get('token')
            url = response.get('url')
        else:
            raise Exception("Respuesta inesperada de Transbank")
        
        if not token or not url:
            raise Exception("Token o URL no recibidos de Transbank")
        
        # Guardar datos de WebPay en la solicitud
        solicitud.webpay_token = token
        solicitud.webpay_buy_order = buy_order
        solicitud.estado = 'procesando_pago'
        solicitud.save()
        
        webpay_url = f"{url}?token_ws={token}"
        print(f"✅ Redirigiendo a WebPay: {webpay_url}")
        
        messages.info(
            request, 
            f'Redirigiendo a WebPay para procesar pago de asistencia mecánica ${monto_total:,}...'
        )
        
        return redirect(webpay_url)
        
    except Exception as e:
        print(f"❌ Error en pago WebPay directo asistencia: {e}")
        print(f"   Tipo de error: {type(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        
        messages.error(
            request, 
            f'⚠️ Error al procesar pago con tarjeta. '
            f'Por favor, solicita la asistencia nuevamente con otro método de pago.'
        )
        return redirect('dashboard')
    # ===== NUEVAS FUNCIONES DE PAGO DIRECTO =====

def procesar_efectivo_directo(request, solicitud):
    """Procesa pago en efectivo directamente desde la solicitud"""
    try:
        print(f"💵 Procesando efectivo directo para solicitud {solicitud.numero_orden}")
        
        # Actualizar estado anterior para envío de email
        estado_anterior = solicitud.estado
        
        solicitud.estado = 'confirmada'
        solicitud.save()
        solicitud = formatear_fechas_solicitud(solicitud)
        # Formatear fechas para el template
        # Corregir desfase de fecha_servicio restando 4 horas
        fecha_servicio_corregida = solicitud.fecha_servicio - timedelta(hours=4)
        solicitud.fecha_servicio_formateada = fecha_servicio_corregida.strftime('%d/%m/%Y %H:%M')
        solicitud.fecha_solicitud_formateada = format_local_datetime(solicitud.fecha_solicitud)
        
        
        messages.success(
            request, 
            f'✅ Solicitud {solicitud.numero_orden} creada y confirmada para pago en efectivo. '
            f'Total a pagar: ${int(solicitud.costo_total):,}'
        )
        
        return redirect('confirmacion_efectivo', solicitud_id=solicitud.id)
        
    except Exception as e:
        print(f"❌ Error procesando efectivo directo: {e}")
        messages.error(request, 'Error al procesar el pago en efectivo.')
        return redirect('dashboard')


def procesar_transferencia_directo(request, solicitud):
    """Procesa transferencia bancaria directamente desde la solicitud"""
    try:
        print(f"🏦 Procesando transferencia directa para solicitud {solicitud.numero_orden}")
        
        # Actualizar estado anterior para envío de email
        estado_anterior = solicitud.estado
        
        solicitud.estado = 'pendiente_confirmacion'
        solicitud.save()
        # Guardar tarifas aplicadas para el desglose
        tarifas = obtener_tarifas_usuario(request.user)
        solicitud.tarifa_base_aplicada = tarifas['tarifa_base']
        solicitud.tarifa_km_aplicada = tarifas['tarifa_por_km']
        solicitud.save()
        
        # Enviar email de actualización de estado
        
        messages.success(
            request, 
            f'✅ Solicitud {solicitud.numero_orden} creada para transferencia bancaria. '
            f'Total a transferir: ${int(solicitud.costo_total):,}'
        )
        
        return redirect('confirmacion_transferencia', solicitud_id=solicitud.id)
        
    except Exception as e:
        print(f"❌ Error procesando transferencia directa: {e}")
        messages.error(request, 'Error al procesar la transferencia.')
        return redirect('dashboard')

def iniciar_pago_webpay_directo(request, solicitud):
    """Inicia pago con WebPay directamente desde la solicitud"""
    try:
        print(f"💳 Procesando WebPay directo para solicitud {solicitud.numero_orden}")
        
        # Verificar si Transbank está disponible
        if not WEBPAY_OPTIONS_AVAILABLE:
            messages.error(
                request, 
                '⚠️ Pago con tarjeta temporalmente no disponible. '
                'Contacta al administrador o solicita nuevamente con otro método de pago.'
            )
            return redirect('dashboard')
        
        monto_total = int(solicitud.costo_total)
        buy_order = f"GR{solicitud.numero_orden}{int(timezone.now().timestamp())}"
        session_id = str(uuid.uuid4())
        return_url = request.build_absolute_uri('/webpay/return/')
        
        print(f"🔄 Iniciando pago Transbank directo:")
        print(f"   Solicitud: {solicitud.numero_orden}")
        print(f"   Monto: ${monto_total}")
        print(f"   Orden: {buy_order}")
        
        options = get_webpay_options()
        
        if options:
            transaction = Transaction(options)
        else:
            transaction = Transaction()
        
        response = transaction.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=monto_total,
            return_url=return_url
        )
        
        if hasattr(response, 'token'):
            token = response.token
            url = response.url
        elif isinstance(response, dict):
            token = response.get('token')
            url = response.get('url')
        else:
            raise Exception("Respuesta inesperada de Transbank")
        
        if not token or not url:
            raise Exception("Token o URL no recibidos de Transbank")
        
        # Guardar datos de WebPay en la solicitud
        solicitud.webpay_token = token
        solicitud.webpay_buy_order = buy_order
        # Guardar tarifas aplicadas para el desglose
        tarifas = obtener_tarifas_usuario(request.user)
        solicitud.tarifa_base_aplicada = tarifas['tarifa_base']
        solicitud.tarifa_km_aplicada = tarifas['tarifa_por_km']
        solicitud.estado = 'procesando_pago'
        solicitud.save()
        
        webpay_url = f"{url}?token_ws={token}"
        print(f"✅ Redirigiendo a WebPay: {webpay_url}")
        
        messages.info(
            request, 
            f'Redirigiendo a WebPay para procesar pago de ${monto_total:,}...'
        )
        
        return redirect(webpay_url)
        
    except Exception as e:
        print(f"❌ Error en pago WebPay directo: {e}")
        print(f"   Tipo de error: {type(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        
        messages.error(
            request, 
            f'⚠️ Error al procesar pago con tarjeta. '
            f'Por favor, solicita el servicio nuevamente con otro método de pago.'
        )
        return redirect('dashboard')
    # ===== NUEVAS VISTAS DE CONFIRMACIÓN PARA ASISTENCIA =====

@login_required
def confirmacion_efectivo_asistencia(request, solicitud_id):
    """Vista de confirmación de pago en efectivo para asistencia mecánica"""
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)
    
    context = {
        'solicitud': solicitud,
        'es_asistencia': True
    }
    return render(request, 'grua_app/confirmacion_efectivo_asistencia.html', context)


@login_required
def confirmacion_transferencia_asistencia(request, solicitud_id):
    """Vista de confirmación de transferencia para asistencia mecánica"""
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    datos_bancarios = {
        'banco': 'Banco de Chile',
        'tipo_cuenta': 'Cuenta Vista',
        'numero_cuenta': '1322825020',
        'rut_titular': '77.971.506-K',
        'nombre_titular': 'Grúas Style',
        'email_confirmacion': 'contacto@gruastyle.com'
    }

    context = {
        'solicitud': solicitud,
        'datos_bancarios': datos_bancarios,
        'es_asistencia': True
    }

    return render(request, 'grua_app/confirmacion_transferencia_asistencia.html', context)


@login_required
def confirmacion_solicitud(request, solicitud_id):
    """Vista de confirmación - YA NO NECESARIA pero mantenida por compatibilidad"""
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    # 🔍 DEBUG
    print(f"🔍 DEBUG confirmacion_solicitud: ID={solicitud.id}, metodo_pago='{solicitud.metodo_pago}', estado='{solicitud.estado}'")

    # Solo redirigir si la solicitud NO tiene método de pago asignado
    if not solicitud.metodo_pago:
        return redirect('payment_selection', solicitud_id=solicitud.id)

    # Si ya tiene método de pago, redirigir al dashboard
    return redirect('dashboard')  # ← Esta línea debe estar DENTRO de la función

@login_required
def ver_detalles_solicitud(request, solicitud_id):
    """Vista específica para ver detalles de una solicitud"""
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        solicitud = formatear_fechas_solicitud(solicitud)
        # Formatear fechas para mostrar en el template
        # Corregir desfase de fecha_servicio restando 4 horas
        fecha_servicio_corregida = solicitud.fecha_servicio - timedelta(hours=4)
        solicitud.fecha_servicio_formateada = fecha_servicio_corregida.strftime('%d/%m/%Y %H:%M')
        solicitud.fecha_solicitud_formateada = format_local_datetime(solicitud.fecha_solicitud)
        # 🔍 DEBUG - Ver qué datos del vehículo tenemos
        print(f"🚗 DEBUG VEHÍCULO:")
        print(f"   Marca: '{solicitud.marca_vehiculo}'")
        print(f"   Modelo: '{solicitud.modelo_vehiculo}'") 
        print(f"   Tipo: '{solicitud.tipo_vehiculo}'")
        print(f"   Placa: '{solicitud.placa_vehiculo}'")
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    # Usar el costo guardado al momento de crear la solicitud
    total = solicitud.costo_total

    # Usar las tarifas que se aplicaron al momento de crear la solicitud
    tarifa_base = getattr(solicitud, 'tarifa_base_aplicada', 30000)
    tarifa_por_km = getattr(solicitud, 'tarifa_km_aplicada', 1500)

    if solicitud.distancia_km:
        costo_km_referencia = float(solicitud.distancia_km) * tarifa_por_km
    else:
        costo_km_referencia = 0

    # Mapear estados a texto legible
    estados_texto = {
        'pendiente': 'Pendiente',
        'confirmada': 'Confirmada',
        'en_proceso': 'En Proceso',
        'completada': 'Completada',
        'cancelada': 'Cancelada',
        'pendiente_pago': 'Pendiente de Pago',
        'pendiente_confirmacion': 'Esperando Confirmación',
        'procesando_pago': 'Procesando Pago',
        'pago_rechazado': 'Pago Rechazado',
    }

    # Mapear métodos de pago a texto legible
    metodos_pago_texto = {
        'efectivo': 'Pago en Efectivo',
        'transferencia': 'Transferencia Bancaria',
        'webpay': 'Tarjeta de Crédito/Débito (WebPay)',
        'mercadopago_card': 'Tarjeta de Crédito/Débito (Mercado Pago)',
        'mercadopago_transfer': 'Transferencia Mercado Pago',
    }

    context = {
        'solicitud': solicitud,
        'total': total,
        'tarifa_base': tarifa_base,
        'costo_km': costo_km_referencia,
        'estado_texto': estados_texto.get(solicitud.estado, solicitud.estado),
        'metodo_pago_texto': metodos_pago_texto.get(solicitud.metodo_pago, solicitud.metodo_pago or 'No definido'),
    }

    return render(request, 'grua_app/ver_detalles_solicitud.html', context)


# ===== NUEVAS VISTAS PARA PDF =====

@login_required
def descargar_pdf_solicitud(request, solicitud_id):
    """Descarga la solicitud en formato PDF"""
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    if PDF_UTILS_AVAILABLE:
        pdf_response = generar_pdf_solicitud(solicitud)
        if pdf_response:
            return pdf_response
        else:
            messages.error(
                request, 'Error al generar el PDF. Inténtalo más tarde.')
    else:
        messages.error(
            request, 'Función de PDF no disponible. Instala xhtml2pdf.')

    return redirect('dashboard')


@login_required
def descargar_pdf_comprobante(request, solicitud_id):
    """Descarga el comprobante de pago en formato PDF"""
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    if not solicitud.pagado and solicitud.estado not in ['confirmada', 'completada']:
        messages.warning(
            request, 'El comprobante solo está disponible para servicios confirmados o pagados.')
        return redirect('dashboard')

    if PDF_UTILS_AVAILABLE:
        pdf_response = generar_pdf_comprobante(solicitud)
        if pdf_response:
            return pdf_response
        else:
            messages.error(
                request, 'Error al generar el comprobante PDF. Inténtalo más tarde.')
    else:
        messages.error(
            request, 'Función de PDF no disponible. Instala xhtml2pdf.')

    return redirect('dashboard')


@login_required
def imprimir_solicitud(request, solicitud_id):
    """Vista para imprimir la solicitud (página optimizada para impresión)"""
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    # Obtener tarifas según membresía del usuario
    tarifas = obtener_tarifas_usuario(solicitud.cliente)
    tarifa_base = tarifas['tarifa_base']
    tarifa_por_km = tarifas['tarifa_por_km']
    tarifa_minima = tarifas['tarifa_minima']

    if solicitud.distancia_km:
        costo_km = float(solicitud.distancia_km) * tarifa_por_km
        total = max(tarifa_base + costo_km, tarifa_minima)
    else:
        costo_km = 0
        total = tarifa_minima

    context = {
        'solicitud': solicitud,
        'tarifa_base': tarifa_base,
        'tarifa_por_km': tarifa_por_km,
        'costo_km': costo_km,
        'total': total,
        'fecha_generacion': timezone.now(),
    }

    return render(request, 'grua_app/imprimir_solicitud.html', context)


@login_required
def reenviar_comprobante(request, solicitud_id):
    """Reenvía el comprobante por email con debug de variables"""
    import os
    from django.conf import settings
    
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    print(f"🔍 DEBUG COMPLETO Reenviar comprobante:")
    print(f"   Solicitud ID: {solicitud.id}")
    print(f"   Usuario: {request.user.username}")
    print(f"   Email usuario: {request.user.email}")
    print(f"   EMAIL_UTILS_AVAILABLE: {EMAIL_UTILS_AVAILABLE}")
    
    # DEBUG DE VARIABLES DE ENTORNO
    print(f"📧 DEBUG EMAIL SETTINGS:")
    print(f"   EMAIL_HOST_USER (env): {os.environ.get('EMAIL_HOST_USER', 'NO_DEFINIDO')}")
    print(f"   EMAIL_HOST_PASSWORD (env): {'DEFINIDO' if os.environ.get('EMAIL_HOST_PASSWORD') else 'NO_DEFINIDO'}")
    print(f"   EMAIL_HOST (env): {os.environ.get('EMAIL_HOST', 'NO_DEFINIDO')}")
    print(f"   EMAIL_PORT (env): {os.environ.get('EMAIL_PORT', 'NO_DEFINIDO')}")
    
    # DEBUG DE SETTINGS DE DJANGO
    print(f"   settings.EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NO_DEFINIDO')}")
    print(f"   settings.EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'NO_DEFINIDO')}")
    print(f"   settings.EMAIL_PORT: {getattr(settings, 'EMAIL_PORT', 'NO_DEFINIDO')}")

    if not EMAIL_UTILS_AVAILABLE:
        print("❌ email_utils no disponible")
        messages.error(request, 'Sistema de email no disponible.')
        return redirect('dashboard')

    if not request.user.email:
        print("❌ Usuario sin email")
        messages.error(request, 'No tienes un email configurado en tu cuenta.')
        return redirect('dashboard')

    try:
        print("🔄 Intentando enviar comprobante...")
        email_enviado = enviar_comprobante_solicitud(solicitud)
        print(f"   Resultado: {email_enviado}")
        
        if email_enviado:
            print("✅ Email enviado exitosamente")
            messages.success(
                request, f'📧 Comprobante reenviado a {request.user.email}')
        else:
            print("❌ email_enviado retornó False/None")
            messages.error(
                request, 'Error al enviar el comprobante. Inténtalo más tarde.')
    except Exception as e:
        print(f"❌ Excepción al reenviar comprobante: {e}")
        print(f"   Tipo de error: {type(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        messages.error(request, 'Error al enviar el comprobante.')

    return redirect('dashboard')

# ===== VISTAS DE PAGO (MANTENIDAS PARA COMPATIBILIDAD) =====

@login_required
def procesar_pago(request, solicitud_id):
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        if metodo_pago == 'transferencia':
            return procesar_transferencia(request, solicitud_id)
        elif metodo_pago == 'efectivo':
            return procesar_efectivo(request, solicitud_id)
        elif metodo_pago == 'webpay':
            return iniciar_pago_webpay(request, solicitud_id)

    # Obtener tarifas según membresía del usuario
    tarifas = obtener_tarifas_usuario(solicitud.cliente)
    tarifa_base = tarifas['tarifa_base']
    tarifa_por_km = tarifas['tarifa_por_km']
    tarifa_minima = tarifas['tarifa_minima']

    if solicitud.distancia_km:
        costo_km = float(solicitud.distancia_km) * tarifa_por_km
        total = max(tarifa_base + costo_km, tarifa_minima)
    else:
        total = tarifa_minima

    context = {
        'solicitud': solicitud,
        'total': total,
        'tarifa_base': tarifa_base,
        'costo_km': costo_km if solicitud.distancia_km else 0,
    }

    return render(request, 'grua_app/procesar_pago.html', context)


@login_required
def procesar_transferencia(request, solicitud_id):
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    # Obtener tarifas según membresía del usuario
    tarifas = obtener_tarifas_usuario(solicitud.cliente)
    tarifa_base = tarifas['tarifa_base']
    tarifa_por_km = tarifas['tarifa_por_km']
    tarifa_minima = tarifas['tarifa_minima']

    if solicitud.distancia_km:
        costo_km = float(solicitud.distancia_km) * tarifa_por_km
        monto_total = max(tarifa_base + costo_km, tarifa_minima)
    else:
        monto_total = tarifa_minima

    # Actualizar estado anterior para envío de email
    estado_anterior = solicitud.estado

    solicitud.metodo_pago = 'transferencia'
    solicitud.estado = 'pendiente_confirmacion'
    solicitud.costo_total = monto_total
    solicitud.save()

    # Enviar email de actualización de estado

    messages.success(request, f'Solicitud {solicitud.numero_orden} registrada')
    return redirect('confirmacion_transferencia', solicitud_id=solicitud.id)


@login_required
def procesar_efectivo(request, solicitud_id):
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    # Obtener tarifas según membresía del usuario
    tarifas = obtener_tarifas_usuario(solicitud.cliente)
    tarifa_base = tarifas['tarifa_base']
    tarifa_por_km = tarifas['tarifa_por_km']
    tarifa_minima = tarifas['tarifa_minima']

    if solicitud.distancia_km:
        costo_km = float(solicitud.distancia_km) * tarifa_por_km
        monto_total = max(tarifa_base + costo_km, tarifa_minima)
    else:
        monto_total = tarifa_minima

    # Actualizar estado anterior para envío de email
    estado_anterior = solicitud.estado

    solicitud.metodo_pago = 'efectivo'
    solicitud.estado = 'confirmada'
    solicitud.costo_total = monto_total
    solicitud.save()

    # Enviar email de actualización de estado

    messages.success(request, f'Solicitud {solicitud.numero_orden} confirmada')
    return redirect('confirmacion_efectivo', solicitud_id=solicitud.id)


@login_required
def confirmacion_transferencia(request, solicitud_id):
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        # Formatear fechas para el template
        solicitud = formatear_fechas_solicitud(solicitud)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    datos_bancarios = {
        'banco': 'Banco de Chile',
        'tipo_cuenta': 'Cuenta Vista',
        'numero_cuenta': '1322825020',
        'rut_titular': '77.971.506-K',
        'nombre_titular': 'Grúas Style',
        'email_confirmacion': 'contacto@gruastyle.com'
    }

    context = {
        'solicitud': solicitud,
        'datos_bancarios': datos_bancarios,
    }

    return render(request, 'grua_app/confirmacion_transferencia.html', context)


@login_required
def confirmacion_efectivo(request, solicitud_id):
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)
        solicitud = formatear_fechas_solicitud(solicitud)
    
    # Formatear fechas para el template
    # Corregir desfase de fecha_servicio restando 4 horas
    fecha_servicio_corregida = solicitud.fecha_servicio - timedelta(hours=4)
    solicitud.fecha_servicio_formateada = fecha_servicio_corregida.strftime('%d/%m/%Y %H:%M')
    solicitud.fecha_solicitud_formateada = format_local_datetime(solicitud.fecha_solicitud)
    
    context = {'solicitud': solicitud}
    return render(request, 'grua_app/confirmacion_efectivo.html', context)

@login_required
def iniciar_pago_webpay(request, solicitud_id):
    """Inicia pago con Transbank WebPay (versión con mejor manejo de errores)"""
    try:
        try:
            from .models import Cliente
            solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        except:
            solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

        # Verificar si Transbank está disponible
        if not WEBPAY_OPTIONS_AVAILABLE:
            messages.error(
                request, '⚠️ Pago con tarjeta temporalmente no disponible. Usa efectivo o transferencia.')
            return redirect('procesar_pago', solicitud_id=solicitud.id)

        # Obtener tarifas según membresía del usuario
        tarifas = obtener_tarifas_usuario(solicitud.cliente)
        tarifa_base = tarifas['tarifa_base']
        tarifa_por_km = tarifas['tarifa_por_km']
        tarifa_minima = tarifas['tarifa_minima']

        if solicitud.distancia_km:
            costo_km = float(solicitud.distancia_km) * tarifa_por_km
            monto_total = int(max(tarifa_base + costo_km, tarifa_minima))
        else:
            monto_total = int(tarifa_minima)

        buy_order = f"GR{solicitud.numero_orden}{int(timezone.now().timestamp())}"
        session_id = str(uuid.uuid4())
        return_url = request.build_absolute_uri('/webpay/return/')

        print(f"🔄 Iniciando pago Transbank:")
        print(f"   Monto: ${monto_total}")
        print(f"   Orden: {buy_order}")
        print(f"   Return URL: {return_url}")

        options = get_webpay_options()

        if options:
            transaction = Transaction(options)
        else:
            transaction = Transaction()

        response = transaction.create(
            buy_order=buy_order,
            session_id=session_id,
            amount=monto_total,
            return_url=return_url
        )

        if hasattr(response, 'token'):
            token = response.token
            url = response.url
        elif isinstance(response, dict):
            token = response.get('token')
            url = response.get('url')
        else:
            raise Exception("Respuesta inesperada de Transbank")

        if not token or not url:
            raise Exception("Token o URL no recibidos de Transbank")

        solicitud.webpay_token = token
        solicitud.webpay_buy_order = buy_order
        solicitud.save()

        webpay_url = f"{url}?token_ws={token}"
        print(f"✅ Redirigiendo a: {webpay_url}")

        return redirect(webpay_url)

    except Exception as e:
        print(f"❌ Error en pago Transbank: {e}")
        print(f"   Tipo de error: {type(e)}")
        print(f"   Traceback: {traceback.format_exc()}")

        messages.error(
            request, f'⚠️ Error al procesar pago con tarjeta. Intenta con efectivo o transferencia.')
        return redirect('procesar_pago', solicitud_id=solicitud_id)

@login_required
def webpay_return(request):
    token_ws = request.GET.get('token_ws') or request.POST.get('token_ws')

    if not token_ws:
        messages.error(request, 'Token no encontrado')
        return redirect('dashboard')

    try:
        options = get_webpay_options()

        if options:
            transaction = Transaction(options)
        else:
            transaction = Transaction()

        response = transaction.commit(token_ws)

        if hasattr(response, 'status'):
            status = response.status
            amount = response.amount
            auth_code = getattr(response, 'authorization_code', '')
        elif isinstance(response, dict):
            status = response.get('status')
            amount = response.get('amount')
            auth_code = response.get('authorization_code', '')
        else:
            raise Exception("Respuesta inesperada")

        solicitud = SolicitudServicio.objects.get(webpay_token=token_ws)
        estado_anterior = solicitud.estado

        if status == 'AUTHORIZED':
            solicitud.pagado = True
            solicitud.estado = 'confirmada'
            solicitud.metodo_pago = 'webpay'
            solicitud.webpay_authorization_code = auth_code
            solicitud.costo_total = amount
            solicitud.save()

            # Enviar email de actualización de estado
            

            messages.success(
                request, f'Pago aprobado! Solicitud {solicitud.numero_orden} confirmada')
            return redirect('pago_exitoso', solicitud_id=solicitud.id)
        else:
            messages.error(request, 'Pago rechazado')
            return redirect('confirmacion_solicitud', solicitud_id=solicitud.id)

    except Exception as e:
        messages.error(request, f'Error: {e}')
        return redirect('dashboard')


@login_required
def pago_exitoso(request, solicitud_id):
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)
    
    context = {'solicitud': solicitud}
    return render(request, 'grua_app/pago_exitoso.html', context)

# ===== VISTAS DE RESET DE CONTRASEÑA =====


def forgot_password(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email_or_username = request.POST.get('email_or_username')

        user = None
        if '@' in email_or_username:
            user = User.objects.filter(email=email_or_username).first()
        else:
            user = User.objects.filter(username=email_or_username).first()

        if user and user.email and EMAIL_UTILS_AVAILABLE:
            try:
                codigo_obj = enviar_codigo_reset_password(user)
                if codigo_obj:
                    request.session['reset_user_id'] = user.id
                    messages.success(request, f'Código enviado a {user.email}')
                    return redirect('verify_reset_code')
                else:
                    messages.error(request, 'Error al enviar código')
            except Exception as e:
                print(f"⚠️ Error enviando código: {e}")
                messages.error(request, 'Sistema de email no disponible')
        else:
            messages.error(
                request, 'Usuario no encontrado o email no configurado')

    return render(request, 'grua_app/forgot_password.html')


def verify_reset_code(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if not EMAIL_UTILS_AVAILABLE:
        messages.error(request, 'Función no disponible')
        return redirect('login')

    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Sesión expirada')
        return redirect('forgot_password')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        codigo_ingresado = request.POST.get('codigo')

        try:
            codigo_obj = verificar_codigo_reset(user, codigo_ingresado)
            if codigo_obj:
                codigo_obj.usado = True
                codigo_obj.save()

                request.session['verified_reset_user_id'] = user.id
                del request.session['reset_user_id']

                messages.success(request, 'Código verificado')
                return redirect('reset_password_confirm')
            else:
                messages.error(request, 'Código inválido')
        except Exception as e:
            print(f"⚠️ Error verificando código: {e}")
            messages.error(request, 'Error al verificar código')

    context = {'user_email': user.email}
    return render(request, 'grua_app/verify_reset_code.html', context)


def reset_password_confirm(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    user_id = request.session.get('verified_reset_user_id')
    if not user_id:
        messages.error(request, 'Sesión expirada')
        return redirect('forgot_password')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            del request.session['verified_reset_user_id']
            messages.success(request, 'Contraseña cambiada exitosamente')
            return redirect('login')
    else:
        form = SetPasswordForm(user)

    context = {'form': form, 'user': user}
    return render(request, 'grua_app/reset_password_confirm.html', context)


def resend_reset_code(request):
    if not EMAIL_UTILS_AVAILABLE:
        messages.error(request, 'Función no disponible')
        return redirect('login')

    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Sesión expirada')
        return redirect('forgot_password')

    user = get_object_or_404(User, id=user_id)

    try:
        codigo_obj = enviar_codigo_reset_password(user)
        if codigo_obj:
            messages.success(request, f'Nuevo código enviado a {user.email}')
        else:
            messages.error(request, 'Error al enviar código')
    except Exception as e:
        print(f"⚠️ Error reenviando código: {e}")
        messages.error(request, 'Error al enviar código')

    return redirect('verify_reset_code')


def asistencia_mecanica(request):
    """Vista para la página de asistencia mecánica"""
    return render(request, 'grua_app/asistencia_mecanica.html')


def carga_bateria(request):
    """Vista para la página de carga de batería"""
    return render(request, 'grua_app/carga_bateria.html')
# ===== NUEVAS VISTAS DEL PERFIL CORREGIDAS =====

@login_required
def perfil(request):
    """Vista principal del perfil del usuario - CORREGIDA CON RUT CORTO"""
    cliente = None
    
    # Intentar obtener/crear cliente con manejo específico de errores
    try:
        from .models import Cliente
        
        # Primero intentar obtener el cliente existente
        try:
            cliente = Cliente.objects.get(user=request.user)
            print(f"✅ Cliente existente encontrado: {cliente}")
        except Cliente.DoesNotExist:
            # Si no existe, crear uno nuevo con RUT único pero corto
            import random
            import string
            
            # Generar RUT temporal de máximo 11 caracteres (dejando espacio para edición)
            random_suffix = ''.join(random.choices(string.digits, k=4))
            rut_temporal = f"T{request.user.id}{random_suffix}"  # Ej: T95678
            
            cliente = Cliente.objects.create(
                user=request.user,
                telefono='',
                rut=rut_temporal,  # RUT temporal único y corto
                direccion=''
            )
            print(f"✅ Cliente creado con RUT temporal: {cliente} (RUT: {rut_temporal})")
        
    except Exception as e:
        print(f"❌ Error específico al obtener cliente: {e}")
        print(f"   Tipo de error: {type(e)}")
        
        # En lugar de redirigir, crear datos por defecto
        class ClienteTemp:
            telefono = ''
            rut = ''
            direccion = ''
        
        cliente = ClienteTemp()
        messages.warning(request, 'Algunos datos del perfil no se pudieron cargar completamente.')
    
    # Obtener estadísticas del usuario con manejo de errores
    solicitudes = []
    total_solicitudes = 0
    solicitudes_completadas = 0
    solicitudes_pendientes = 0
    total_gastado = 0
    solicitudes_recientes = []
    
    try:
        solicitudes = SolicitudServicio.objects.filter(cliente=request.user)
        total_solicitudes = solicitudes.count()
        solicitudes_completadas = solicitudes.filter(estado='completada').count()
        solicitudes_pendientes = solicitudes.filter(estado__in=['pendiente', 'confirmada', 'en_proceso']).count()
        
        # Calcular total gastado
        for solicitud in solicitudes.filter(pagado=True):
            if solicitud.costo_total:
                total_gastado += float(solicitud.costo_total)
        
        solicitudes_recientes = solicitudes.order_by('-fecha_solicitud')[:5]
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        messages.info(request, 'Algunas estadísticas no están disponibles temporalmente.')
    
    # Obtener membresía activa con manejo de errores
    membresia_activa = None
    try:
        membresia_activa = Membresia.objects.filter(
            usuario=request.user,
            estado='activa'
        ).first()
    except Exception as e:
        print(f"❌ Error obteniendo membresía: {e}")
    
    context = {
        'user': request.user,
        'cliente': cliente,
        'total_solicitudes': total_solicitudes,
        'solicitudes_completadas': solicitudes_completadas,
        'solicitudes_pendientes': solicitudes_pendientes,
        'total_gastado': total_gastado,
        'solicitudes_recientes': solicitudes_recientes,
        'membresia_activa': membresia_activa,
    }
    
    return render(request, 'grua_app/perfil.html', context)


@login_required
def editar_perfil(request):
    """Vista para editar el perfil del usuario"""
    if request.method == 'POST':
        form = EditarPerfilForm(request.user, request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, '✅ Perfil actualizado exitosamente!')
                return redirect('perfil')
            except Exception as e:
                print(f"❌ Error guardando perfil: {e}")
                messages.error(request, 'Error al guardar los cambios. Inténtalo nuevamente.')
        else:
            print("❌ Errores en formulario de edición:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
    else:
        form = EditarPerfilForm(request.user)
    
    context = {
        'form': form,
        'user': request.user
    }
    
    return render(request, 'grua_app/editar_perfil.html', context)


@login_required
def cambiar_password(request):
    """Vista para cambiar contraseña"""
    if request.method == 'POST':
        from django.contrib.auth.forms import PasswordChangeForm
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)  # Mantener la sesión activa
            messages.success(request, '✅ Contraseña cambiada exitosamente!')
            return redirect('perfil')
        else:
            print("❌ Errores en cambio de contraseña:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
    else:
        from django.contrib.auth.forms import PasswordChangeForm
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'user': request.user
    }
    
    return render(request, 'grua_app/cambiar_password.html', context)


# ===== VISTAS DE MEMBRESÍAS =====

@login_required
def membresias(request):
    """Vista de la página de membresías"""
    # Obtener membresía activa del usuario si la tiene
    membresia_activa = None
    try:
        membresia_activa = Membresia.objects.filter(
            usuario=request.user,
            estado='activa'
        ).first()
    except Exception as e:
        print(f"Error obteniendo membresía: {e}")
    
    context = {
        'membresia_activa': membresia_activa,
    }
    return render(request, 'grua_app/membresias.html', context)


@login_required  
def pago_membresia(request):
    """Vista para el pago de membresías - ACTUALIZADA con nueva estructura"""
    plan = request.GET.get('plan', 'basica')  # Plan por defecto
    duration = request.GET.get('duration', '3')  # Duración por defecto 3 meses
    
    # Definir la nueva estructura de planes con duración
    planes_data = {
        'basica': {
            'nombre': 'Básica',
            'duraciones': {
                '3': {
                    'precio': 59990,
                    'detalles': '• Tarifa base: $25.000<br>• Tarifa x Km: $1.300',
                    'periodo': 'por 3 meses'
                },
                '6': {
                    'precio': 109990,
                    'detalles': '• 1 Viaje Gratis región metropolitana<br>• Tarifa base: $25.000 • Tarifa x Km: $1.300',
                    'periodo': 'por 6 meses'
                },
                '12': {
                    'precio': 199990,
                    'detalles': '• 3 Viajes Gratis región metropolitana<br>• Tarifa base: $25.000 • Tarifa x Km: $1.300',
                    'periodo': 'por 1 año'
                }
            }
        },
        'pro': {
            'nombre': 'Pro',
            'duraciones': {
                '3': {
                    'precio': 99990,
                    'detalles': '• 1 Viaje a mitad de precio región metropolitana<br>• Tarifa base: $20.000 • Tarifa x Km: $1.300<br>• Sin tarifa mínima',
                    'periodo': 'por 3 meses'
                },
                '6': {
                    'precio': 189990,
                    'detalles': '• 2 viajes gratis región metropolitana<br>• Tarifa base: $20.000 • Tarifa x Km: $1.300<br>• Sin tarifa mínima',
                    'periodo': 'por 6 meses'
                },
                '12': {
                    'precio': 349000,
                    'detalles': '• 5 viajes gratis región metropolitana<br>• Un servicio de revisión técnica a domicilio<br>• Taza de regalo',
                    'periodo': 'por 1 año'
                }
            }
        },
        'premium': {
            'nombre': 'Premium',
            'duraciones': {
                '3': {
                    'precio': 299000,
                    'detalles': '• 2 viajes gratis región metropolitana<br>• 2 viajes precio fijo $20.000 toda RM<br>• Tarifa base: $20.000 • Tarifa x Km: $1.200<br>• Sin tarifa mínima',
                    'periodo': 'por 3 meses'
                },
                '6': {
                    'precio': 549000,
                    'detalles': '• 4 viajes gratis región metropolitana<br>• 3 viajes precio fijo $20.000 toda RM<br>• Tarifa base: $20.000 • Tarifa x Km: $1.200<br>• Sin tarifa mínima',
                    'periodo': 'por 6 meses'
                },
                '12': {
                    'precio': 999000,
                    'detalles': '• 10 viajes gratis región metropolitana<br>• 10 viajes precio fijo $20.000 toda RM<br>• Un servicio de revisión técnica a domicilio<br>• Taza de regalo • Asistencia prioritaria',
                    'periodo': 'por 1 año'
                }
            }
        }
    }
    
    # Validar plan y duración
    if plan not in planes_data:
        plan = 'basica'
    
    if duration not in ['3', '6', '12']:
        duration = '3'
    
    # Obtener datos del plan seleccionado
    plan_info = planes_data[plan]
    duration_info = plan_info['duraciones'][duration]
    
    # Generar texto de duración
    duration_text = {
        '3': '3 Meses',
        '6': '6 Meses', 
        '12': '1 Año'
    }[duration]
    
    # Crear objeto plan_data para el template
    plan_data = {
        'nombre': plan_info['nombre'],
        'precio': duration_info['precio'],
        'detalles': duration_info['detalles'],
        'periodo': duration_info['periodo']
    }
    
    context = {
        'plan': plan,
        'duration': duration,
        'duration_text': duration_text,
        'plan_data': plan_data,
        'user': request.user
    }
    
    return render(request, 'grua_app/pago_membresia.html', context)

@login_required
def confirmacion_transferencia_membresia(request, membresia_id):
    """Vista de confirmación de transferencia bancaria para membresías"""
    try:
        membresia = get_object_or_404(Membresia, id=membresia_id, usuario=request.user)
        
        # Obtener el pago asociado
        try:
            pago = PagoMembresia.objects.get(membresia=membresia)
        except PagoMembresia.DoesNotExist:
            messages.error(request, 'No se encontró información del pago.')
            return redirect('membresias')
        
        # Datos bancarios de la empresa
        datos_bancarios = {
            'banco': 'Banco de Chile',
            'tipo_cuenta': 'Cuenta Vista',
            'numero_cuenta': '1322825020',
            'rut_titular': '77.971.506-K',
            'nombre_titular': 'Grúas Style',
            'email_confirmacion': 'contacto@gruastyle.com'
        }
        
        context = {
            'membresia': membresia,
            'pago': pago,
            'datos_bancarios': datos_bancarios,
            'monto_total': int(pago.monto),
        }
        
        return render(request, 'grua_app/confirmacion_transferencia_membresia.html', context)
        
    except Exception as e:
        print(f"Error en confirmacion_transferencia_membresia: {e}")
        messages.error(request, 'Error al cargar la confirmación.')
        return redirect('membresias')

@login_required
def procesar_pago_membresia(request):
    """Vista para procesar el pago de membresía con Mercado Pago"""
    if request.method != 'POST':
        return redirect('membresias')
    
    try:
        # Obtener datos del formulario
        plan = request.POST.get('plan')
        duration = request.POST.get('duration', '3')
        metodo_pago = request.POST.get('metodo_pago')
        
        # Verificar que el usuario no tenga una membresía activa
        membresia_activa = Membresia.objects.filter(
            usuario=request.user,
            estado='activa'
        ).first()
        
        if membresia_activa and membresia_activa.esta_activa:
            messages.warning(request, 'Ya tienes una membresía activa.')
            return redirect('membresias')
        
        # Definir precios y características según plan y duración
        planes_config = {
            'basica': {
                'precios': {'3': 59990, '6': 109990, '12': 199990},
                'servicios_incluidos': 5,
                'descuento': 10
            },
            'pro': {
                'precios': {'3': 99990, '6': 189990, '12': 349000},
                'servicios_incluidos': 10,
                'descuento': 20
            },
            'premium': {
                'precios': {'3': 299000, '6': 549000, '12': 999000},
                'servicios_incluidos': 0,
                'descuento': 30
            }
        }
        
        # Validar plan y duración
        if plan not in planes_config or duration not in planes_config[plan]['precios']:
            messages.error(request, 'Plan o duración no válidos.')
            return redirect('membresias')
        
        # Obtener configuración del plan
        config_plan = planes_config[plan]
        precio = config_plan['precios'][duration]
        
        # Obtener o crear tipo de membresía
        tipo_membresia, created = TipoMembresia.objects.get_or_create(
            nombre=plan,
            defaults={
                'precio': precio,
                'servicios_incluidos': config_plan['servicios_incluidos'],
                'descuento_porcentaje': config_plan['descuento'],
                'activo': True
            }
        )
        
        if tipo_membresia.precio != precio:
            tipo_membresia.precio = precio
            tipo_membresia.save()
        
        # Crear la membresía (estado pendiente hasta confirmar pago)
        from datetime import timedelta
        dias_duracion = int(duration) * 30
        fecha_vencimiento = timezone.now() + timedelta(days=dias_duracion)
        
        # 🆕 ESTADO PENDIENTE HASTA CONFIRMAR PAGO
        estado_inicial = 'pendiente'
        
        membresia = Membresia.objects.create(
            usuario=request.user,
            tipo_membresia=tipo_membresia,
            fecha_vencimiento=fecha_vencimiento,
            estado=estado_inicial
        )
        
            
        # 🆕 LÓGICA SEGÚN MÉTODO DE PAGO

        if metodo_pago == 'webpay':  # Ahora redirige a Mercado Pago
            messages.info(request, 'Redirigiendo a Mercado Pago para procesar el pago...')
            return crear_pago_mercadopago_membresia(request, membresia, precio, plan, duration)
            
        elif metodo_pago == 'transferencia':  # Transferencia bancaria
            pago = PagoMembresia.objects.create(
                membresia=membresia,
                usuario=request.user,
                monto=precio,
                metodo_pago='transferencia',
                orden_compra=f"MEM_{timezone.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}",
                estado='pendiente'
            )
            
            messages.info(request, f'Transfiere ${precio:,} a la cuenta bancaria. Orden: {pago.orden_compra}')
            return redirect('confirmacion_transferencia_membresia', membresia_id=membresia.id)
        
        else:
            messages.error(request, 'Método de pago no válido.')
            return redirect('membresias')
        
    except Exception as e:
        print(f"Error procesando pago de membresía: {e}")
        messages.error(request, 'Error al procesar el pago. Inténtalo nuevamente.')
        return redirect('pago_membresia')

def crear_pago_mercadopago_membresia(request, membresia, precio, plan, duration):
    """Crear preferencia de Mercado Pago para membresías"""
    try:
        import mercadopago
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        
        # DEBUG
        print(f"🔍 DEBUG MERCADO PAGO:")
        print(f"   Vendedor Access Token: {settings.MERCADOPAGO_ACCESS_TOKEN[:20]}...")
        print(f"   Email del comprador: cliente.test.diferente@gmail.com")
        print(f"   Precio: {precio}")
        
        # Datos del cliente
        cliente = request.user
        nombre_completo = f"{cliente.first_name} {cliente.last_name}".strip()
        if not nombre_completo:
            nombre_completo = cliente.username
        
        # Texto de duración
        duration_text = {'3': '3 meses', '6': '6 meses', '12': '1 año'}[duration]
        
        # Datos de la preferencia
        preference_data = {
            "items": [
                {
                    "title": f"Membresía {plan.title()} - {duration_text}",
                    "description": f"Membresía {plan.title()} de Grúa Style por {duration_text}",
                    "quantity": 1,
                    "currency_id": "CLP",
                    "unit_price": float(precio)
                }
            ],
            "payer": {
                "name": nombre_completo,
                "email": request.user.email
            },
            "back_urls": {
                "success": f"http://127.0.0.1:8000/membresia/result/{membresia.id}/?status=success",
                "failure": f"http://127.0.0.1:8000/membresia/result/{membresia.id}/?status=failure",
                "pending": f"http://127.0.0.1:8000/membresia/result/{membresia.id}/?status=pending"
            },
            "external_reference": str(membresia.id),
            "statement_descriptor": "GRUA STYLE MEMBRESIA",
            "payment_methods": {
                "excluded_payment_types": [],
                "installments": 12
            }
        }
        
        # Crear preferencia
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        if preference_response["status"] == 201:
            # Crear registro de pago
            pago = PagoMembresia.objects.create(
                membresia=membresia,
                usuario=request.user,
                monto=precio,
                metodo_pago='mercadopago_card',
                orden_compra=f"MEM_{timezone.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}",
                estado='pendiente'
            )
            
            # Guardar referencia del pago
            pago.datos_adicionales = {"preference_id": preference["id"]}
            pago.save()
            
            # Redirigir a Mercado Pago
            if settings.MERCADOPAGO_SANDBOX:
                redirect_url = preference["sandbox_init_point"]
            else:
                redirect_url = preference["init_point"]
                
            return redirect(redirect_url)
        else:
            print(f"❌ Error creando preferencia de membresía: {preference_response}")
            messages.error(request, 'Error al crear la preferencia de pago.')
            return redirect('membresias')
            
    except Exception as e:
        print(f"❌ Error en Mercado Pago membresía: {e}")
        messages.error(request, 'Error procesando el pago con Mercado Pago.')
        return redirect('membresias')
    
@login_required
def cancelar_membresia(request):
    """Vista para cancelar membresía"""
    if request.method == 'POST':
        try:
            membresia = Membresia.objects.get(
                usuario=request.user,
                estado='activa'
            )
            
            membresia.estado = 'cancelada'
            membresia.fecha_cancelacion = timezone.now()
            membresia.auto_renovar = False
            membresia.save()
            
            messages.success(request, 'Membresía cancelada exitosamente.')
            
        except Membresia.DoesNotExist:
            messages.error(request, 'No tienes una membresía activa para cancelar.')
        except Exception as e:
            print(f"Error cancelando membresía: {e}")
            messages.error(request, 'Error al cancelar la membresía.')
    else:
        messages.warning(request, 'Acción no permitida.')
    
    return redirect('dashboard')

@login_required
def procesar_pago_legacy(request, solicitud_id):
    """Vista legacy que redirige al nuevo sistema de Mercado Pago"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        messages.info(request, 'Redirigiendo al nuevo sistema de pago...')
        return redirect('payment_selection', solicitud_id=solicitud.id)
    except Exception as e:
        print(f"Error en procesar_pago_legacy: {e}")
        messages.error(request, 'Error procesando el pago')
        return redirect('dashboard')

# ===== NUEVAS FUNCIONES DE GEOCODIFICACIÓN =====

import requests
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def geocodificar_coordenadas(request):
    """
    Endpoint para convertir coordenadas a direcciones exactas
    """
    try:
        data = json.loads(request.body)
        lat = float(data.get('lat'))
        lng = float(data.get('lng'))
        
        # Intentar múltiples servicios de geocodificación
        direccion = obtener_direccion_exacta(lat, lng)
        
        return JsonResponse({
            'success': True,
            'direccion': direccion,
            'coordenadas': {'lat': lat, 'lng': lng}
        })
        
    except Exception as e:
        logger.error(f"Error en geocodificación: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'direccion': f"Coordenadas: {lat}, {lng}"
        })

def obtener_direccion_exacta(lat, lng):
    """
    Función para obtener dirección exacta usando múltiples servicios
    """
    
    # Servicio 1: Nominatim (OpenStreetMap) con User-Agent correcto
    try:
        headers = {
            'User-Agent': 'GruaStyle/1.0 (contacto@gruastyle.cl)',
            'Accept': 'application/json',
            'Accept-Language': 'es-CL,es;q=0.9'
        }
        
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            'format': 'json',
            'lat': lat,
            'lon': lng,
            'zoom': 18,
            'addressdetails': 1,
            'accept-language': 'es-CL'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            direccion = procesar_respuesta_nominatim(data)
            if direccion and len(direccion) > 10:  # Verificar que sea una dirección válida
                logger.info(f"Dirección obtenida con Nominatim: {direccion}")
                return direccion
                
    except Exception as e:
        logger.warning(f"Error con Nominatim: {str(e)}")
    
    # Fallback: Generar dirección más realista
    return generar_direccion_realista(lat, lng)

def procesar_respuesta_nominatim(data):
    """
    Procesa la respuesta de Nominatim para generar una dirección chilena
    """
    if not data or not data.get('address'):
        return None
    
    address = data.get('address', {})
    direccion_parts = []
    
    # Nombre de la calle + número
    if address.get('house_number') and address.get('road'):
        direccion_parts.append(f"{address['road']} {address['house_number']}")
    elif address.get('road'):
        direccion_parts.append(address['road'])
    elif address.get('pedestrian'):
        direccion_parts.append(address['pedestrian'])
    elif address.get('footway'):
        direccion_parts.append(address['footway'])
    
    # Comuna/Barrio
    if address.get('suburb'):
        direccion_parts.append(address['suburb'])
    elif address.get('neighbourhood'):
        direccion_parts.append(address['neighbourhood'])
    elif address.get('hamlet'):
        direccion_parts.append(address['hamlet'])
    
    # Ciudad/Comuna
    if address.get('city'):
        direccion_parts.append(address['city'])
    elif address.get('town'):
        direccion_parts.append(address['town'])
    elif address.get('village'):
        direccion_parts.append(address['village'])
    elif address.get('municipality'):
        direccion_parts.append(address['municipality'])
    
    # Construir dirección final
    if direccion_parts:
        return ', '.join(direccion_parts)
    
    # Si no hay datos suficientes, usar display_name
    if data.get('display_name'):
        # Limpiar y acortar display_name
        display_name = data['display_name']
        parts = display_name.split(',')[:3]  # Tomar solo las primeras 3 partes
        return ', '.join(part.strip() for part in parts)
    
    return None

def generar_direccion_realista(lat, lng):
    """
    Genera una dirección más realista basada en coordenadas
    """
    
    # Mapeo de zonas de Santiago con coordenadas más precisas
    zonas_detalladas = [
        # Santiago Centro
        {'lat_min': -33.46, 'lat_max': -33.43, 'lng_min': -70.68, 'lng_max': -70.63, 'zona': 'Santiago Centro'},
        
        # Las Condes
        {'lat_min': -33.43, 'lat_max': -33.40, 'lng_min': -70.62, 'lng_max': -70.55, 'zona': 'Las Condes'},
        
        # Providencia
        {'lat_min': -33.44, 'lat_max': -33.41, 'lng_min': -70.64, 'lng_max': -70.59, 'zona': 'Providencia'},
        
        # Ñuñoa
        {'lat_min': -33.47, 'lat_max': -33.44, 'lng_min': -70.62, 'lng_max': -70.57, 'zona': 'Ñuñoa'},
        
        # San Miguel
        {'lat_min': -33.50, 'lat_max': -33.47, 'lng_min': -70.68, 'lng_max': -70.63, 'zona': 'San Miguel'},
        
        # Lampa
        {'lat_min': -33.32, 'lat_max': -33.25, 'lng_min': -70.90, 'lng_max': -70.70, 'zona': 'Lampa'},
        
        # Maipú
        {'lat_min': -33.53, 'lat_max': -33.47, 'lng_min': -70.82, 'lng_max': -70.72, 'zona': 'Maipú'},
        
        # Pudahuel
        {'lat_min': -33.47, 'lat_max': -33.40, 'lng_min': -70.82, 'lng_max': -70.72, 'zona': 'Pudahuel'},
        
        # La Florida
        {'lat_min': -33.55, 'lat_max': -33.48, 'lng_min': -70.62, 'lng_max': -70.55, 'zona': 'La Florida'},
        
        # Puente Alto
        {'lat_min': -33.65, 'lat_max': -33.55, 'lng_min': -70.65, 'lng_max': -70.55, 'zona': 'Puente Alto'},
    ]
    
    # Encontrar zona exacta
    zona_encontrada = 'Santiago'
    for zona in zonas_detalladas:
        if (zona['lat_min'] <= lat <= zona['lat_max'] and 
            zona['lng_min'] <= lng <= zona['lng_max']):
            zona_encontrada = zona['zona']
            break
    
    # Generar número de casa realista basado en coordenadas
    numero_casa = abs(int((lat * lng * 10000) % 9999) + 100)
    
    # Calles comunes por zona
    calles_por_zona = {
        'Santiago Centro': ['Ahumada', 'Estado', 'Bandera', 'Morandé', 'Teatinos', 'Amunátegui'],
        'Las Condes': ['Apoquindo', 'Las Condes', 'Manquehue', 'El Bosque Norte', 'Isidora Goyenechea'],
        'Providencia': ['Providencia', 'Manuel Montt', 'Los Leones', 'Nueva Providencia', 'Antonio Varas'],
        'Ñuñoa': ['Irarrazaval', 'Grecia', 'José Pedro Alessandri', 'Diagonal Paraguay', 'Salvador'],
        'San Miguel': ['Gran Avenida', 'Santa Rosa', 'Departamental', 'Llano Subercaseaux', 'Club Hípico'],
        'Lampa': ['Barros Luco', 'Manuel Rodríguez', 'Libertad', 'Independencia', 'Chacabuco'],
        'Maipú': ['Pajaritos', 'Américo Vespucio', 'Los Pajaritos', 'Longitudinal Sur', 'Carmen'],
        'Pudahuel': ['San Pablo', 'Dorsal', 'Noviciado', 'Blanqueado', 'Pudahuel'],
        'La Florida': ['Vicuña Mackenna', 'Walker Martínez', 'La Florida', 'Los Presidentes', 'Rojas Magallanes'],
        'Puente Alto': ['Concha y Toro', 'Eyzaguirre', 'Gabriela Mistral', 'Hospital', 'Manuel Rodríguez']
    }
    
    # Seleccionar calle basada en las coordenadas
    calles = calles_por_zona.get(zona_encontrada, ['Avenida Principal', 'Calle Central'])
    indice_calle = abs(int((lat * 1000) % len(calles)))
    calle_seleccionada = calles[indice_calle]
    
    # Construir dirección realista
    direccion = f"{calle_seleccionada} {numero_casa}, {zona_encontrada}"
    
    logger.info(f"Dirección realista generada: {direccion}")
    return direccion
    
# Reemplaza la función payment_selection existente en views.py por esta versión completa:

@login_required
def payment_selection(request, solicitud_id):
    """Vista completa para selección de método de pago con Mercado Pago"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Datos bancarios para transferencias tradicionales
        datos_bancarios = {
            'bank_name': 'Banco de Chile',
            'account_type': 'Cuenta Vista', 
            'account_number': '1322825020',
            'rut': '77.971.506-K',
            'account_holder': 'Grúas Style',
            'email': 'contacto@gruastyle.com'
        }
        
        context = {
            'solicitud': solicitud,
            'precio_total': int(solicitud.costo_total),
            'datos_bancarios': datos_bancarios,
            'mercadopago_public_key': getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', 'TEST-demo-key'),
        }
        
        return render(request, 'grua_app/payment_selection.html', context)
        
    except Exception as e:
        print(f"❌ Error en payment_selection: {e}")
        messages.error(request, 'Error cargando métodos de pago.')
        return redirect('dashboard')


@login_required
def mercadopago_checkout(request, solicitud_id):
    """Crear preferencia de pago en Mercado Pago"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Configurar SDK de Mercado Pago
        import mercadopago
        sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
        
        # Datos del cliente (corregido)
        cliente = request.user
        nombre_completo = f"{cliente.first_name} {cliente.last_name}".strip()
        if not nombre_completo:
            nombre_completo = cliente.username
            
        # Datos de la preferencia
        preference_data = {
            "items": [
                {
                    "title": f"{'Asistencia Mecánica' if solicitud.tipo_servicio_categoria == 'asistencia' else 'Servicio de Grúa'} - {solicitud.numero_orden}",
                    "description": f"{'Asistencia mecánica en' if solicitud.tipo_servicio_categoria == 'asistencia' else 'Grúa desde'} {solicitud.direccion_origen[:50]}{'.' if solicitud.tipo_servicio_categoria == 'asistencia' else '... hasta ' + solicitud.direccion_destino[:50] + '...'}",
                    "quantity": 1,
                    "currency_id": "CLP",
                    "unit_price": float(solicitud.costo_total)
                }
            ],
            "payer": {
                "name": nombre_completo,
                "email": request.user.email  # ← Email totalmente diferente
                
            },
            "back_urls": {
                "success": f"http://127.0.0.1:8000/payment/result/{solicitud.id}/?status=success",
                "failure": f"http://127.0.0.1:8000/payment/result/{solicitud.id}/?status=failure",
                "pending": f"http://127.0.0.1:8000/payment/result/{solicitud.id}/?status=pending"
            },
            "external_reference": str(solicitud.id),
            "statement_descriptor": "GRUA STYLE",
            "payment_methods": {
                "excluded_payment_types": [],
                "installments": 12
            }
        }
        
        # Crear preferencia
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        if preference_response["status"] == 201:
            # Guardar referencia del pago
            solicitud.referencia_pago = preference["id"]
            solicitud.estado = 'procesando_pago'
            # Guardar tarifas aplicadas para el desglose
            tarifas = obtener_tarifas_usuario(request.user)
            solicitud.tarifa_base_aplicada = tarifas['tarifa_base']
            solicitud.tarifa_km_aplicada = tarifas['tarifa_por_km']
            solicitud.save()
            
            # Redirigir a Mercado Pago
            if settings.MERCADOPAGO_SANDBOX:
                redirect_url = preference["sandbox_init_point"]
            else:
                redirect_url = preference["init_point"]
                
            return redirect(redirect_url)
        else:
            print(f"❌ Error creando preferencia: {preference_response}")
            messages.error(request, 'Error al crear la preferencia de pago.')
            return redirect('payment_selection', solicitud_id=solicitud.id)
            
    except Exception as e:
        print(f"❌ Error en mercadopago_checkout: {e}")
        import traceback
        traceback.print_exc()
        messages.error(request, 'Error procesando el pago con Mercado Pago.')
        return redirect('payment_selection', solicitud_id=solicitud.id)


@login_required
def payment_result(request, solicitud_id):
    """Manejar resultado del pago de Mercado Pago"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        status = request.GET.get('status', 'unknown')
        collection_status = request.GET.get('collection_status')
        payment_id = request.GET.get('payment_id')
        
        if status == 'success' or collection_status == 'approved':
            # Pago exitoso
            solicitud.estado = 'confirmada'
            solicitud.pagado = True
            solicitud.mercadopago_payment_id = payment_id
            # Guardar tarifas aplicadas para el desglose si no las tiene
        if not hasattr(solicitud, 'tarifa_base_aplicada') or not solicitud.tarifa_base_aplicada:
            tarifas = obtener_tarifas_usuario(request.user)
            solicitud.tarifa_base_aplicada = tarifas['tarifa_base']
            solicitud.tarifa_km_aplicada = tarifas['tarifa_por_km']
            solicitud.save()
            
            # Enviar email de confirmación
            if EMAIL_UTILS_AVAILABLE:
                try:
                    pass
                except Exception as e:
                    print(f"⚠️ Error enviando email confirmación: {e}")
            
            messages.success(request, f'🎉 ¡Pago exitoso! Solicitud {solicitud.numero_orden} confirmada.')
            return redirect('pago_exitoso', solicitud_id=solicitud.id)
            
        elif status == 'pending':
            # Pago pendiente
            solicitud.estado = 'pendiente_confirmacion'
            solicitud.mercadopago_payment_id = payment_id
            solicitud.save()
            
            messages.info(request, f'⏳ Pago pendiente. Solicitud {solicitud.numero_orden} en proceso.')
            return redirect('dashboard')
            
        else:
            # Pago fallido
            solicitud.estado = 'pendiente'
            solicitud.save()
            
            messages.error(request, 'Pago cancelado o falló. Puedes intentar nuevamente.')
            return redirect('payment_selection', solicitud_id=solicitud.id)
            
    except Exception as e:
        print(f"❌ Error en payment_result: {e}")
        messages.error(request, 'Error procesando el resultado del pago.')
        return redirect('dashboard')


@login_required
def bank_transfer_mp(request, solicitud_id):
    """Procesar transferencia bancaria via Mercado Pago"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Por ahora, marcar como pendiente de pago con transferencia
        solicitud.estado = 'pendiente_confirmacion'
        solicitud.metodo_pago = 'mercadopago_transfer'
        solicitud.save()
        
        # Datos de transferencia de Mercado Pago (estos serían los reales de tu cuenta MP)
        datos_mp_transfer = {
            'cvu': '0000007900001234567890',  # CVU de ejemplo - usar tu CVU real
            'alias': 'grua.style.mp',  # Alias de ejemplo - usar tu alias real
            'titular': 'Grúa Style SpA',
            'cuit': '12345678901',  # CUIT de ejemplo - usar tu CUIT real
            'banco': 'Mercado Pago',
            'referencia': solicitud.numero_orden
        }
        
        context = {
            'solicitud': solicitud,
            'datos_transfer': datos_mp_transfer,
            'precio_total': int(solicitud.costo_total)
        }
        
        messages.success(request, f'Transferencia iniciada para solicitud {solicitud.numero_orden}')
        return render(request, 'grua_app/bank_transfer_mp.html', context)
        
    except Exception as e:
        print(f"❌ Error en bank_transfer_mp: {e}")
        messages.error(request, 'Error procesando transferencia.')
        return redirect('dashboard')
    
@login_required
def membresia_payment_result(request, membresia_id):
    """Manejar resultado del pago de membresía de Mercado Pago"""
    try:
        membresia = get_object_or_404(Membresia, id=membresia_id, usuario=request.user)
        status = request.GET.get('status', 'unknown')
        payment_id = request.GET.get('payment_id')
        
        if status == 'success':
            # Pago exitoso - activar membresía
            membresia.estado = 'activa'
            membresia.save()
            
            # Actualizar pago
            try:
                pago = PagoMembresia.objects.get(membresia=membresia)
                pago.estado = 'completado'
                pago.fecha_confirmacion = timezone.now()
                if payment_id:
                    pago.payment_id = payment_id
                pago.save()
            except PagoMembresia.DoesNotExist:
                pass
            
            messages.success(request, f'🎉 ¡Membresía {membresia.tipo_membresia.nombre.title()} activada exitosamente!')
            return redirect('perfil')
            
        elif status == 'pending':
            # Pago pendiente
            try:
                pago = PagoMembresia.objects.get(membresia=membresia)
                pago.estado = 'pendiente'
                pago.save()
            except:
                pass
            
            messages.info(request, '⏳ Pago pendiente. Te notificaremos cuando se confirme.')
            return redirect('perfil')
            
        else:
            # Pago fallido - eliminar membresía pendiente
            membresia.delete()
            messages.error(request, 'Pago cancelado o falló. Puedes intentar nuevamente.')
            return redirect('membresias')
            
    except Exception as e:
        print(f"❌ Error en resultado de membresía: {e}")
        messages.error(request, 'Error procesando el resultado del pago.')
        return redirect('membresias')
    
    # ===== NUEVAS VISTAS PARA CONFIRMACIONES DE SOLICITUD =====

@login_required
def confirmacion_efectivo_solicitud(request, solicitud_id):
    """Vista de confirmación de pago en efectivo para solicitud de servicio"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Actualizar estado de la solicitud
        estado_anterior = solicitud.estado
        solicitud.estado = 'confirmada'
        solicitud.metodo_pago = 'efectivo'
        solicitud.save()
        
        
        context = {
            'solicitud': solicitud,
        }
        return render(request, 'grua_app/confirmacion_efectivo.html', context)
        
    except Exception as e:
        print(f"❌ Error en confirmacion_efectivo_solicitud: {e}")
        messages.error(request, 'Error al cargar la confirmación.')
        return redirect('dashboard')


@login_required
def confirmacion_transferencia_solicitud(request, solicitud_id):
    """Vista de confirmación de transferencia bancaria para solicitud de servicio"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        # Formatear fechas para el template
        solicitud = formatear_fechas_solicitud(solicitud)
        
        # Actualizar estado de la solicitud
        estado_anterior = solicitud.estado
        solicitud.estado = 'pendiente_confirmacion'
        solicitud.metodo_pago = 'transferencia'
        solicitud.save()
        
        
        # Datos bancarios de la empresa
        datos_bancarios = {
            'banco': 'Banco de Chile',
            'tipo_cuenta': 'Cuenta Vista',
            'numero_cuenta': '1322825020',
            'rut_titular': '77.971.506-K',
            'nombre_titular': 'Grúas Style',
            'email_confirmacion': 'contacto@gruastyle.com'
        }
        
        context = {
            'solicitud': solicitud,
            'datos_bancarios': datos_bancarios,
        }
        
        return render(request, 'grua_app/confirmacion_transferencia.html', context)
        
    except Exception as e:
        print(f"❌ Error en confirmacion_transferencia_solicitud: {e}")
        messages.error(request, 'Error al cargar la confirmación.')
        return redirect('dashboard')


@login_required
def mercadopago_checkout_solicitud(request, solicitud_id):
    """Vista para checkout con Mercado Pago para solicitud de servicio"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Si es POST, procesar el pago (este método ya está implementado en tu código)
        if request.method == 'POST':
            # Esta lógica ya existe en tu función mercadopago_checkout
            return mercadopago_checkout(request, solicitud_id)
        
        # Si es GET, mostrar el formulario de pago
        context = {
            'solicitud': solicitud,
            'amount': int(solicitud.costo_total),
            'public_key': getattr(settings, 'MERCADOPAGO_PUBLIC_KEY', 'TEST-demo-key'),
            'max_installments': 12,
        }
        
        return render(request, 'grua_app/mercadopago_checkout.html', context)
        
    except Exception as e:  # ← ESTO FALTABA
        print(f"❌ Error en mercadopago_checkout_solicitud: {e}")
        messages.error(request, 'Error al cargar el checkout.')
        return redirect('dashboard')
        
# ===== NUEVAS VISTAS PARA MANEJO DE PAGOS PENDIENTES =====

@login_required
def completar_pago_pendiente(request, solicitud_id):
    """Permite completar el pago de una solicitud en procesando_pago"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        if solicitud.estado != 'procesando_pago':
            messages.warning(request, 'Esta solicitud no está en estado de pago pendiente.')
            return redirect('dashboard')
        
        # Redirigir al sistema de pago de Mercado Pago
        messages.info(request, 'Redirigiendo a Mercado Pago para completar el pago...')
        return redirect('mercadopago_checkout', solicitud_id=solicitud.id)
        
    except Exception as e:
        print(f"Error en completar_pago_pendiente: {e}")
        messages.error(request, 'Error al procesar la solicitud.')
        return redirect('dashboard')


@login_required
def cambiar_a_efectivo(request, solicitud_id):
    """Cambia una solicitud de procesando_pago a efectivo"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        if solicitud.estado not in ['procesando_pago', 'pendiente_confirmacion', 'confirmada']:
            print(f"🔍 DEBUG cambiar_a_efectivo:")
            print(f"   Solicitud: {solicitud.numero_orden}")
            print(f"   Estado actual: '{solicitud.estado}'")
            print(f"   Método actual: '{solicitud.metodo_pago}'")
            messages.warning(request, 'Esta solicitud no puede ser modificada.')
            return redirect('dashboard')
        
        # Cambiar a efectivo
        solicitud.metodo_pago = 'efectivo'
        solicitud.estado = 'confirmada'
        solicitud.save()
        
        messages.success(request, f'Solicitud {solicitud.numero_orden} cambiada a pago en efectivo.')
        return redirect('confirmacion_efectivo', solicitud_id=solicitud.id)
        
    except Exception as e:
        print(f"Error en cambiar_a_efectivo: {e}")
        messages.error(request, 'Error al cambiar método de pago.')
        return redirect('dashboard')


@login_required
def cambiar_a_transferencia(request, solicitud_id):
    """Cambia una solicitud de procesando_pago a transferencia"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        if solicitud.estado not in ['procesando_pago', 'pendiente_confirmacion', 'confirmada']:
            print(f"🔍 DEBUG eliminar_solicitud:")
            print(f"   Solicitud: {solicitud.numero_orden}")
            print(f"   Estado actual: '{solicitud.estado}'")
            print(f"   Método actual: '{solicitud.metodo_pago}'")
            print(f"   Fecha: {solicitud.fecha_solicitud}")
            messages.warning(request, 'Esta solicitud no puede ser modificada.')
            return redirect('dashboard')
        
        # Cambiar a transferencia
        solicitud.metodo_pago = 'transferencia'
        solicitud.estado = 'pendiente_confirmacion'
        solicitud.save()
        
        messages.success(request, f'Solicitud {solicitud.numero_orden} cambiada a transferencia bancaria.')
        return redirect('confirmacion_transferencia', solicitud_id=solicitud.id)
        
    except Exception as e:
        print(f"Error en cambiar_a_transferencia: {e}")
        messages.error(request, 'Error al cambiar método de pago.')
        return redirect('dashboard')


@login_required
def cancelar_solicitud_pendiente(request, solicitud_id):
    """Cancela definitivamente una solicitud en procesando_pago"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        if solicitud.estado != 'procesando_pago':
            messages.warning(request, 'Esta solicitud no puede ser cancelada.')
            return redirect('dashboard')
        
        # Cancelar la solicitud
        solicitud.estado = 'cancelada'
        solicitud.save()
        
        messages.success(request, f'Solicitud {solicitud.numero_orden} cancelada exitosamente.')
        return redirect('dashboard')
        
    except Exception as e:
        print(f"Error en cancelar_solicitud_pendiente: {e}")
        messages.error(request, 'Error al cancelar la solicitud.')
        return redirect('dashboard')@login_required

@login_required
def cambiar_a_mercadopago(request, solicitud_id):
    """Cambia una solicitud a pago con Mercado Pago"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        print(f"🔍 DEBUG cambiar_a_mercadopago:")
        print(f"   Solicitud: {solicitud.numero_orden}")
        print(f"   Estado actual: '{solicitud.estado}'")
        print(f"   Método actual: '{solicitud.metodo_pago}'")
        
        if solicitud.estado not in ['procesando_pago', 'pendiente_confirmacion', 'confirmada']:
            messages.warning(request, 'Esta solicitud no puede ser modificada.')
            return redirect('dashboard')
        
        # Cambiar a Mercado Pago
        solicitud.metodo_pago = 'mercadopago_card'
        solicitud.estado = 'procesando_pago'
        solicitud.save()
        
        messages.success(request, f'Solicitud {solicitud.numero_orden} cambiada a pago con tarjeta.')
        return redirect('mercadopago_checkout', solicitud_id=solicitud.id)
        
    except Exception as e:
        print(f"Error en cambiar_a_mercadopago: {e}")
        messages.error(request, 'Error al cambiar método de pago.')
        return redirect('dashboard')
    
def eliminar_solicitud_pendiente(request, solicitud_id):
    """Elimina definitivamente una solicitud pendiente"""
    try:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Solo permitir eliminar si está en estados pendientes
        if solicitud.estado not in ['procesando_pago', 'pendiente', 'pendiente_confirmacion', 'confirmada']:
            messages.warning(request, 'Esta solicitud no puede ser eliminada.')
            return redirect('dashboard')
        
        numero_orden = solicitud.numero_orden
        # Eliminar la solicitud completamente
        solicitud.delete()
        
        messages.success(request, f'Solicitud {numero_orden} eliminada exitosamente.')
        return redirect('dashboard')
        
    except Exception as e:
        print(f"Error en eliminar_solicitud_pendiente: {e}")
        messages.error(request, 'Error al eliminar la solicitud.')
        return redirect('dashboard')
    # No permitir eliminar solicitudes de más de 2 horas o que estén realmente en proceso
        from datetime import timedelta
        hace_dos_horas = timezone.now() - timedelta(hours=2)
        if solicitud.fecha_solicitud < hace_dos_horas and solicitud.estado == 'confirmada':
            messages.warning(request, 'Esta solicitud ya no puede ser eliminada (muy antigua).')
            return redirect('dashboard')
    


# ===== FUNCIÓN DE TIMEOUT AUTOMÁTICO =====

def limpiar_solicitudes_expiradas():
    """
    Elimina solicitudes expiradas y sin confirmar después de 1 hora
    """
    from datetime import timedelta
    
    try:
        # Calcular la fecha límite (1 hora atrás)
        hace_una_hora = timezone.now() - timedelta(hours=1)
        
        # Estados que deben ser eliminados después de 1 hora sin confirmación
        estados_expirados = [
            'procesando_pago',
            'pendiente',  # Solicitudes sin método de pago definido
        ]
        
        # Buscar solicitudes expiradas para eliminar
        solicitudes_expiradas = SolicitudServicio.objects.filter(
            estado__in=estados_expirados,
            fecha_solicitud__lt=hace_una_hora
        )
        
        # Contar antes de eliminar
        total_eliminadas = solicitudes_expiradas.count()
        
        if total_eliminadas > 0:
            # Mostrar qué se va a eliminar
            for solicitud in solicitudes_expiradas:
                print(f"🗑️ Eliminando solicitud expirada: {solicitud.numero_orden} (Estado: {solicitud.estado})")
            
            # Eliminar las solicitudes expiradas
            solicitudes_expiradas.delete()
            print(f"✅ {total_eliminadas} solicitudes expiradas eliminadas de la base de datos")
        
        return total_eliminadas
        
    except Exception as e:
        print(f"❌ Error eliminando solicitudes expiradas: {e}")
        return 0


@login_required
def limpiar_solicitudes_manual(request):
    """Vista manual para limpiar solicitudes expiradas (para testing)"""
    if request.user.is_staff:  # Solo para administradores
        total_eliminadas = limpiar_solicitudes_expiradas()
        messages.success(request, f'Se eliminaron {total_eliminadas} solicitudes expiradas.')
    else:
        messages.error(request, 'No tienes permisos para esta acción.')
    
    return redirect('dashboard')

@staff_member_required
def check_notifications_api(request):
    """API para verificar nuevas notificaciones"""
    try:
        from .models import NotificacionAdmin
        from django.utils import timezone
        from datetime import timedelta
        
        # Obtener notificaciones de los últimos 30 segundos (nuevas)
        last_30_seconds = timezone.now() - timedelta(seconds=30)
        new_notifications = NotificacionAdmin.objects.filter(
            fecha_creacion__gte=last_30_seconds,
            leida=False
        ).order_by('-fecha_creacion')
        
        # Obtener todas las notificaciones recientes (últimas 10)
        all_notifications = NotificacionAdmin.objects.filter(
            leida=False
        ).order_by('-fecha_creacion')[:10]
        
        new_data = []
        for notif in new_notifications:
            new_data.append({
                'id': notif.id,
                'titulo': notif.titulo,
                'mensaje': notif.mensaje,
                'solicitud_id': notif.solicitud.id if notif.solicitud else None,
                'fecha_creacion': notif.fecha_creacion.isoformat()
            })
        
        all_data = []
        for notif in all_notifications:
            all_data.append({
                'id': notif.id,
                'titulo': notif.titulo,
                'mensaje': notif.mensaje,
                'leida': notif.leida,
                'fecha_creacion': notif.fecha_creacion.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'new_notifications': new_data,
            'all_notifications': all_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@staff_member_required
def admin_alerts_view(request):
    """Vista para la página de alertas del admin"""
    return render(request, 'admin_alerts.html')

# Agregar estas vistas al final de tu views.py

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
