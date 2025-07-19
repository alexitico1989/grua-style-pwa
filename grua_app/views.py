from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
from django.db.models import Q, Count, Sum
from datetime import datetime, timedelta
import uuid
import traceback

# Imports de Transbank
from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.integration_type import IntegrationType

try:
    from transbank.common.options import WebpayOptions
    WEBPAY_OPTIONS_AVAILABLE = True
except ImportError:
    print("⚠️ WebpayOptions no disponible")
    WEBPAY_OPTIONS_AVAILABLE = False

# Imports de modelos y email
from .forms import SolicitudServicioForm, CustomUserCreationForm
from .models import SolicitudServicio, CodigoVerificacion

# Imports de email - con manejo de errores
try:
    from .email_utils import enviar_email_bienvenida, enviar_codigo_reset_password, verificar_codigo_reset, enviar_comprobante_solicitud, enviar_actualizacion_estado
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
    from .models import HistorialPago, Factura
    HISTORIAL_PAGO_AVAILABLE = True
    FACTURA_AVAILABLE = True
except ImportError:
    print("⚠️ HistorialPago o Factura no encontrado")
    HISTORIAL_PAGO_AVAILABLE = False
    FACTURA_AVAILABLE = False


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
    return render(request, 'grua_app/home.html')


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
    """Dashboard mejorado con estadísticas, facturas y servicios organizados"""
    try:
        from .models import Cliente
        cliente, created = Cliente.objects.get_or_create(
            user=request.user,
            defaults={'telefono': ''}
        )
        
        # Obtener todas las solicitudes del cliente
        solicitudes = SolicitudServicio.objects.filter(
            cliente=cliente).order_by('-fecha_solicitud')
        
        # Separar solicitudes activas (pendientes, confirmadas, en proceso) de completadas
        solicitudes_activas = solicitudes.filter(
            estado__in=['pendiente', 'confirmada', 'en_proceso', 'pendiente_pago']
        )
        
        servicios_completados = solicitudes.filter(
            estado__in=['completada', 'cancelada']
        )
        
        # Obtener facturas (si el modelo existe)
        facturas = []
        if FACTURA_AVAILABLE:
            try:
                facturas = Factura.objects.filter(
                    solicitud__cliente=cliente
                ).order_by('-fecha_emision')
            except:
                # Si no existe el modelo Factura, crear facturas virtuales desde solicitudes pagadas
                facturas = solicitudes.filter(
                    pagado=True, 
                    estado__in=['confirmada', 'completada']
                )
        else:
            # Usar solicitudes pagadas como facturas
            facturas = solicitudes.filter(
                pagado=True, 
                estado__in=['confirmada', 'completada']
            )
        
        # Calcular estadísticas
        total_servicios = solicitudes.count()
        total_facturas = len(facturas)
        
        # Calcular total gastado
        total_gastado = 0
        for solicitud in solicitudes.filter(pagado=True):
            if hasattr(solicitud, 'costo_total') and solicitud.costo_total:
                total_gastado += float(solicitud.costo_total)
        
        # Servicios del mes actual
        fecha_inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        servicios_mes = solicitudes.filter(
            fecha_solicitud__gte=fecha_inicio_mes
        ).count()
        
        context = {
            'solicitudes': solicitudes,  # Para compatibilidad con template existente
            'solicitudes_activas': solicitudes_activas,
            'servicios_completados': servicios_completados,
            'facturas': facturas,
            'total_servicios': total_servicios,
            'total_facturas': total_facturas,
            'total_gastado': int(total_gastado),
            'servicios_mes': servicios_mes,
        }
        
    except Exception as e:
        print(f"❌ Error en dashboard: {e}")
        # Fallback básico
        context = {
            'solicitudes': [],
            'solicitudes_activas': [],
            'servicios_completados': [],
            'facturas': [],
            'total_servicios': 0,
            'total_facturas': 0,
            'total_gastado': 0,
            'servicios_mes': 0,
        }
    
    return render(request, 'grua_app/dashboard.html', context)


# ===== NUEVAS VISTAS PARA FUNCIONALIDADES DEL DASHBOARD =====

@login_required
def historial_servicios(request):
    """Vista dedicada al historial completo de servicios"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        servicios = SolicitudServicio.objects.filter(
            cliente=cliente
        ).order_by('-fecha_solicitud')
        
        # Filtros opcionales
        estado_filtro = request.GET.get('estado')
        if estado_filtro:
            servicios = servicios.filter(estado=estado_filtro)
            
        mes_filtro = request.GET.get('mes')
        if mes_filtro:
            try:
                año, mes = mes_filtro.split('-')
                servicios = servicios.filter(
                    fecha_solicitud__year=int(año),
                    fecha_solicitud__month=int(mes)
                )
            except:
                pass
        
        context = {
            'servicios': servicios,
            'estado_filtro': estado_filtro,
            'mes_filtro': mes_filtro,
        }
        
    except:
        context = {'servicios': []}
    
    return render(request, 'grua_app/historial_servicios.html', context)


@login_required
def ver_factura(request, factura_id):
    """Vista para ver detalles de una factura específica"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        
        if FACTURA_AVAILABLE:
            factura = get_object_or_404(Factura, id=factura_id, solicitud__cliente=cliente)
            solicitud = factura.solicitud
        else:
            # Si no hay modelo Factura, usar la solicitud directamente
            solicitud = get_object_or_404(
                SolicitudServicio, 
                id=factura_id, 
                cliente=cliente, 
                pagado=True
            )
            factura = solicitud  # Usar solicitud como factura
            
        context = {
            'factura': factura,
            'solicitud': solicitud,
        }
        
    except:
        messages.error(request, 'Factura no encontrada')
        return redirect('dashboard')
    
    return render(request, 'grua_app/ver_factura.html', context)


@login_required
def descargar_factura_pdf(request, factura_id):
    """Descarga una factura específica en PDF"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        
        if FACTURA_AVAILABLE:
            factura = get_object_or_404(Factura, id=factura_id, solicitud__cliente=cliente)
            solicitud = factura.solicitud
        else:
            solicitud = get_object_or_404(
                SolicitudServicio, 
                id=factura_id, 
                cliente=cliente, 
                pagado=True
            )
            
        if PDF_UTILS_AVAILABLE:
            pdf_response = generar_pdf_comprobante(solicitud)
            if pdf_response:
                return pdf_response
            else:
                messages.error(request, 'Error al generar el PDF de la factura.')
        else:
            messages.error(request, 'Función de PDF no disponible.')
            
    except:
        messages.error(request, 'Factura no encontrada')
    
    return redirect('dashboard')


@login_required
def repetir_servicio(request, servicio_id):
    """Permite repetir un servicio anterior con los mismos datos"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        servicio_original = get_object_or_404(
            SolicitudServicio, 
            id=servicio_id, 
            cliente=cliente
        )
        
        # Pre-llenar el formulario con los datos del servicio anterior
        form_data = {
            'direccion_origen': servicio_original.direccion_origen,
            'direccion_destino': servicio_original.direccion_destino,
            'marca_vehiculo': servicio_original.marca_vehiculo,
            'modelo_vehiculo': servicio_original.modelo_vehiculo,
            'año_vehiculo': servicio_original.año_vehiculo,
            'descripcion_problema': servicio_original.descripcion_problema,
        }
        
        if hasattr(servicio_original, 'tipo_servicio'):
            form_data['tipo_servicio'] = servicio_original.tipo_servicio
        
        # Redirigir al formulario de solicitud con datos pre-llenados
        request.session['repetir_servicio_data'] = form_data
        messages.info(request, f'Repitiendo servicio {servicio_original.numero_orden}')
        return redirect('solicitar_servicio')
        
    except:
        messages.error(request, 'Servicio no encontrado')
        return redirect('dashboard')


@login_required
def calificar_servicio(request, servicio_id):
    """Permite calificar un servicio completado"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        servicio = get_object_or_404(
            SolicitudServicio, 
            id=servicio_id, 
            cliente=cliente,
            estado='completada'
        )
        
        if request.method == 'POST':
            calificacion = request.POST.get('calificacion')
            comentario = request.POST.get('comentario', '')
            
            try:
                calificacion = int(calificacion)
                if 1 <= calificacion <= 5:
                    servicio.calificacion = calificacion
                    if hasattr(servicio, 'comentario_calificacion'):
                        servicio.comentario_calificacion = comentario
                    servicio.save()
                    
                    messages.success(request, f'¡Gracias por calificar el servicio {servicio.numero_orden}!')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Calificación debe ser entre 1 y 5 estrellas')
            except ValueError:
                messages.error(request, 'Calificación inválida')
        
        context = {'servicio': servicio}
        return render(request, 'grua_app/calificar_servicio.html', context)
        
    except:
        messages.error(request, 'Servicio no encontrado')
        return redirect('dashboard')


@login_required
def rastrear_servicio(request, solicitud_id):
    """Vista para rastrear un servicio en tiempo real"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(
            SolicitudServicio, 
            id=solicitud_id, 
            cliente=cliente,
            estado='en_proceso'
        )
        
        context = {
            'solicitud': solicitud,
            # Aquí puedes agregar datos de ubicación de la grúa si los tienes
        }
        
        return render(request, 'grua_app/rastrear_servicio.html', context)
        
    except:
        messages.error(request, 'Servicio no encontrado o no está en proceso')
        return redirect('dashboard')


@login_required
def cancelar_solicitud(request, solicitud_id):
    """Permite cancelar una solicitud pendiente"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(
            SolicitudServicio, 
            id=solicitud_id, 
            cliente=cliente,
            estado='pendiente'
        )
        
        if request.method == 'POST':
            motivo = request.POST.get('motivo', 'Cancelado por el cliente')
            
            estado_anterior = solicitud.estado
            solicitud.estado = 'cancelada'
            if hasattr(solicitud, 'motivo_cancelacion'):
                solicitud.motivo_cancelacion = motivo
            solicitud.save()
            
            # Enviar email de actualización de estado
            if EMAIL_UTILS_AVAILABLE:
                try:
                    enviar_actualizacion_estado(solicitud, estado_anterior)
                except Exception as e:
                    print(f"⚠️ Error enviando actualización de estado: {e}")
            
            messages.success(request, f'Solicitud {solicitud.numero_orden} cancelada')
            return redirect('dashboard')
        
        context = {'solicitud': solicitud}
        return render(request, 'grua_app/cancelar_solicitud.html', context)
        
    except:
        messages.error(request, 'No se puede cancelar esta solicitud')
        return redirect('dashboard')


@login_required
def ver_servicio_detalle(request, servicio_id):
    """Vista detallada de un servicio específico"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        servicio = get_object_or_404(SolicitudServicio, id=servicio_id, cliente=cliente)
        
        context = {'servicio': servicio}
        return render(request, 'grua_app/ver_servicio_detalle.html', context)
        
    except:
        messages.error(request, 'Servicio no encontrado')
        return redirect('dashboard')


@login_required
def perfil_usuario(request):
    """Vista del perfil del usuario"""
    try:
        from .models import Cliente
        cliente, created = Cliente.objects.get_or_create(
            user=request.user,
            defaults={'telefono': ''}
        )
        
        if request.method == 'POST':
            # Actualizar datos del usuario
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            telefono = request.POST.get('telefono', '')
            
            request.user.first_name = first_name
            request.user.last_name = last_name
            request.user.email = email
            request.user.save()
            
            cliente.telefono = telefono
            cliente.save()
            
            messages.success(request, 'Perfil actualizado exitosamente')
            return redirect('perfil_usuario')
        
        context = {
            'cliente': cliente,
        }
        
    except Exception as e:
        print(f"❌ Error en perfil: {e}")
        context = {'cliente': None}
    
    return render(request, 'grua_app/perfil_usuario.html', context)


# ===== VISTAS ORIGINALES (MANTENIDAS) =====

@login_required
def solicitar_servicio(request):
    """Vista de solicitar servicio con envío automático de comprobante por email"""
    try:
        from .models import Cliente
        cliente, created = Cliente.objects.get_or_create(
            user=request.user,
            defaults={'telefono': ''}
        )
    except Exception as e:
        messages.error(request, 'Error al acceder al perfil del cliente.')
        return redirect('dashboard')
    
    # Verificar si hay datos de repetición de servicio
    form_data_inicial = request.session.pop('repetir_servicio_data', {})
    
    # Verificar tipo de servicio desde URL
    tipo_servicio = request.GET.get('tipo')
    if tipo_servicio:
        form_data_inicial['tipo_servicio'] = tipo_servicio
        
    if request.method == 'POST':
        form = SolicitudServicioForm(request.POST)
        if form.is_valid():
            solicitud = form.save(commit=False)
            solicitud.cliente = cliente
            solicitud.save()

            # 📧 NUEVO: Enviar email de comprobante
            if EMAIL_UTILS_AVAILABLE:
                try:
                    email_enviado = enviar_comprobante_solicitud(solicitud)
                    if email_enviado:
                        messages.success(
                            request, f'✅ Solicitud {solicitud.numero_orden} creada y comprobante enviado a {request.user.email}')
                    else:
                        messages.success(
                            request, f'✅ Solicitud {solicitud.numero_orden} creada')
                        messages.info(
                            request, 'El comprobante se enviará próximamente a tu email')
                except Exception as e:
                    print(f"⚠️ Error enviando comprobante: {e}")
                    messages.success(
                        request, f'✅ Solicitud {solicitud.numero_orden} creada')
                    messages.info(
                        request, 'El comprobante se enviará próximamente a tu email')
            else:
                messages.success(
                    request, f'✅ Solicitud {solicitud.numero_orden} creada')

            return redirect('confirmacion_solicitud', solicitud_id=solicitud.id)
        else:
            print("❌ Errores en formulario de solicitud:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
    else:
        form = SolicitudServicioForm(initial=form_data_inicial)

    return render(request, 'grua_app/solicitar_servicio.html', {'form': form})


@login_required
def confirmacion_solicitud(request, solicitud_id):
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    # Calcular costo
    tarifa_base = 15000
    tarifa_por_km = 1200
    tarifa_minima = 20000

    if solicitud.distancia_km:
        costo_km = float(solicitud.distancia_km) * tarifa_por_km
        total = max(tarifa_base + costo_km, tarifa_minima)
    else:
        costo_km = 0
        total = tarifa_minima

    context = {
        'solicitud': solicitud,
        'total': total,
        'tarifa_base': tarifa_base,
        'costo_km': costo_km,
    }

    return render(request, 'grua_app/confirmacion_solicitud.html', context)

# ===== RESTO DE VISTAS ORIGINALES (MANTENIDAS SIN CAMBIOS) =====

@login_required
def descargar_pdf_solicitud(request, solicitud_id):
    """Descarga la solicitud en formato PDF"""
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
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
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
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
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    # Calcular tarifas
    tarifa_base = 15000
    tarifa_por_km = 1200
    tarifa_minima = 20000

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
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
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

# ===== VISTAS DE PAGO =====


@login_required
def procesar_pago(request, solicitud_id):
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
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

    tarifa_base = 15000
    tarifa_por_km = 1200
    tarifa_minima = 20000

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
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    tarifa_base = 15000
    tarifa_por_km = 1200
    tarifa_minima = 20000

    if solicitud.distancia_km:
        costo_km = float(solicitud.distancia_km) * tarifa_por_km
        monto_total = max(tarifa_base + costo_km, tarifa_minima)
    else:
        monto_total = tarifa_minima

    # Actualizar estado anterior para envío de email
    estado_anterior = solicitud.estado

    solicitud.metodo_pago = 'transferencia'
    solicitud.estado = 'pendiente_pago'
    solicitud.costo_total = monto_total
    solicitud.save()

    # Enviar email de actualización de estado
    if EMAIL_UTILS_AVAILABLE and estado_anterior != solicitud.estado:
        try:
            enviar_actualizacion_estado(solicitud, estado_anterior)
        except Exception as e:
            print(f"⚠️ Error enviando actualización de estado: {e}")

    messages.success(request, f'Solicitud {solicitud.numero_orden} registrada')
    return redirect('confirmacion_transferencia', solicitud_id=solicitud.id)


@login_required
def procesar_efectivo(request, solicitud_id):
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    tarifa_base = 15000
    tarifa_por_km = 1200
    tarifa_minima = 20000

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
    if EMAIL_UTILS_AVAILABLE and estado_anterior != solicitud.estado:
        try:
            enviar_actualizacion_estado(solicitud, estado_anterior)
        except Exception as e:
            print(f"⚠️ Error enviando actualización de estado: {e}")

    messages.success(request, f'Solicitud {solicitud.numero_orden} confirmada')
    return redirect('confirmacion_efectivo', solicitud_id=solicitud.id)


@login_required
def confirmacion_transferencia(request, solicitud_id):
    try:
        from .models import Cliente
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    datos_bancarios = {
        'banco': 'Banco de Chile',
        'tipo_cuenta': 'Cuenta Corriente',
        'numero_cuenta': '12345678-9',
        'rut_titular': '12.345.678-9',
        'nombre_titular': 'GrúaExpress SpA',
        'email_confirmacion': 'pagos@gruaexpress.cl'
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
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)
    
    context = {'solicitud': solicitud}
    return render(request, 'grua_app/confirmacion_efectivo.html', context)


@login_required
def iniciar_pago_webpay(request, solicitud_id):
    """Inicia pago con Transbank WebPay (versión con mejor manejo de errores)"""
    try:
        try:
            from .models import Cliente
            cliente = Cliente.objects.get(user=request.user)
            solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
        except:
            solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

        # Verificar si Transbank está disponible
        if not WEBPAY_OPTIONS_AVAILABLE:
            messages.error(
                request, '⚠️ Pago con tarjeta temporalmente no disponible. Usa efectivo o transferencia.')
            return redirect('procesar_pago', solicitud_id=solicitud.id)

        tarifa_base = 15000
        tarifa_por_km = 1200
        tarifa_minima = 20000

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
            if EMAIL_UTILS_AVAILABLE and estado_anterior != solicitud.estado:
                try:
                    enviar_actualizacion_estado(solicitud, estado_anterior)
                except Exception as e:
                    print(f"⚠️ Error enviando actualización de estado: {e}")

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
        cliente = Cliente.objects.get(user=request.user)
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=cliente)
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
