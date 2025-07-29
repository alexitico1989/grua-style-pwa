from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm
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

# Imports de modelos y email - ACTUALIZADO CON EditarPerfilForm y MEMBRESÍAS
from .forms import SolicitudServicioForm, CustomUserCreationForm, EditarPerfilForm
from .models import SolicitudServicio, CodigoVerificacion, TipoMembresia, Membresia, PagoMembresia

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
    from .models import HistorialPago
    HISTORIAL_PAGO_AVAILABLE = True
except ImportError:
    print("⚠️ HistorialPago no encontrado")
    HISTORIAL_PAGO_AVAILABLE = False


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
    try:
        from .models import Cliente
        cliente, created = Cliente.objects.get_or_create(
            user=request.user,
            defaults={'telefono': ''}
        )
        solicitudes = SolicitudServicio.objects.filter(
            cliente=request.user).order_by('-fecha_solicitud')
    except:
        solicitudes = []
    
    context = {'solicitudes': solicitudes}
    return render(request, 'grua_app/dashboard.html', context)


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
            
            # Obtener método de pago seleccionado
            metodo_pago = form.cleaned_data['metodo_pago']
            solicitud.metodo_pago = metodo_pago
            
            # Calcular costo total
            tarifa_base = 30000  # Actualizada según el template
            tarifa_por_km = 1500
            tarifa_minima = 35000
            
            if solicitud.distancia_km:
                costo_km = float(solicitud.distancia_km) * tarifa_por_km
                costo_total = max(tarifa_base + costo_km, tarifa_minima)
            else:
                costo_total = tarifa_minima
            
            solicitud.costo_total = costo_total
            solicitud.save()

            # 📧 Enviar email de comprobante
            if EMAIL_UTILS_AVAILABLE:
                try:
                    email_enviado = enviar_comprobante_solicitud(solicitud)
                    if not email_enviado:
                        print("⚠️ No se pudo enviar el comprobante por email")
                except Exception as e:
                    print(f"⚠️ Error enviando comprobante: {e}")

            # REDIRIGIR DIRECTAMENTE SEGÚN EL MÉTODO DE PAGO
            print(f"🔄 Procesando pago directo - Método: {metodo_pago}")
            
            if metodo_pago == 'efectivo':
                return procesar_efectivo_directo(request, solicitud)
            elif metodo_pago == 'transferencia':
                return procesar_transferencia_directo(request, solicitud)
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

    return render(request, 'grua_app/solicitar_servicio.html', {'form': form})


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
            solicitud.tipo_servicio = 'asistencia_mecanica'
            
            # Obtener método de pago seleccionado
            metodo_pago = form.cleaned_data['metodo_pago']
            solicitud.metodo_pago = metodo_pago
            
            # Calcular costo total para asistencia mecánica (precios diferentes)
            tarifa_base_asistencia = 25000  # Precio base para asistencia
            tarifa_por_km_asistencia = 1000
            tarifa_minima_asistencia = 30000
            
            if solicitud.distancia_km:
                costo_km = float(solicitud.distancia_km) * tarifa_por_km_asistencia
                costo_total = max(tarifa_base_asistencia + costo_km, tarifa_minima_asistencia)
            else:
                costo_total = tarifa_minima_asistencia
            
            solicitud.costo_total = costo_total
            solicitud.save()

            # 📧 Enviar email de comprobante
            if EMAIL_UTILS_AVAILABLE:
                try:
                    email_enviado = enviar_comprobante_solicitud(solicitud)
                    if not email_enviado:
                        print("⚠️ No se pudo enviar el comprobante por email")
                except Exception as e:
                    print(f"⚠️ Error enviando comprobante: {e}")

            # REDIRIGIR DIRECTAMENTE SEGÚN EL MÉTODO DE PAGO
            print(f"🔧 Procesando pago directo asistencia mecánica - Método: {metodo_pago}")
            
            if metodo_pago == 'efectivo':
                return procesar_efectivo_directo_asistencia(request, solicitud)
            elif metodo_pago == 'transferencia':
                return procesar_transferencia_directo_asistencia(request, solicitud)
            elif metodo_pago == 'webpay':
                return iniciar_pago_webpay_directo_asistencia(request, solicitud)
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
        
        # Enviar email de actualización de estado
        if EMAIL_UTILS_AVAILABLE and estado_anterior != solicitud.estado:
            try:
                enviar_actualizacion_estado(solicitud, estado_anterior)
            except Exception as e:
                print(f"⚠️ Error enviando actualización de estado: {e}")
        
        messages.success(
            request, 
            f'✅ Solicitud de asistencia mecánica {solicitud.numero_orden} creada y confirmada para pago en efectivo. '
            f'Total a pagar: ${int(solicitud.costo_total):,}'
        )
        
        return redirect('confirmacion_efectivo_asistencia', solicitud_id=solicitud.id)
        
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
        
        solicitud.estado = 'pendiente_pago'
        solicitud.save()
        
        # Enviar email de actualización de estado
        if EMAIL_UTILS_AVAILABLE and estado_anterior != solicitud.estado:
            try:
                enviar_actualizacion_estado(solicitud, estado_anterior)
            except Exception as e:
                print(f"⚠️ Error enviando actualización de estado: {e}")
        
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
        'tipo_cuenta': 'Cuenta Corriente',
        'numero_cuenta': '12345678-9',
        'rut_titular': '12.345.678-9',
        'nombre_titular': 'Grúa Style SpA',
        'email_confirmacion': 'pagos@gruastyle.cl'
    }

    context = {
        'solicitud': solicitud,
        'datos_bancarios': datos_bancarios,
        'es_asistencia': True
    }

    return render(request, 'grua_app/confirmacion_transferencia_asistencia.html', context)


# ===== NUEVAS FUNCIONES DE PAGO DIRECTO =====

def procesar_efectivo_directo(request, solicitud):
    """Procesa pago en efectivo directamente desde la solicitud"""
    try:
        print(f"💵 Procesando efectivo directo para solicitud {solicitud.numero_orden}")
        
        # Actualizar estado anterior para envío de email
        estado_anterior = solicitud.estado
        
        solicitud.estado = 'confirmada'
        solicitud.save()
        
        # Enviar email de actualización de estado
        if EMAIL_UTILS_AVAILABLE and estado_anterior != solicitud.estado:
            try:
                enviar_actualizacion_estado(solicitud, estado_anterior)
            except Exception as e:
                print(f"⚠️ Error enviando actualización de estado: {e}")
        
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
        
        solicitud.estado = 'pendiente_pago'
        solicitud.save()
        
        # Enviar email de actualización de estado
        if EMAIL_UTILS_AVAILABLE and estado_anterior != solicitud.estado:
            try:
                enviar_actualizacion_estado(solicitud, estado_anterior)
            except Exception as e:
                print(f"⚠️ Error enviando actualización de estado: {e}")
        
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


@login_required
def confirmacion_solicitud(request, solicitud_id):
    """Vista de confirmación - YA NO NECESARIA pero mantenida por compatibilidad"""
    try:
        from .models import Cliente
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    # Redirigir según el método de pago ya establecido
    if solicitud.metodo_pago == 'efectivo':
        return redirect('confirmacion_efectivo', solicitud_id=solicitud.id)
    elif solicitud.metodo_pago == 'transferencia':
        return redirect('confirmacion_transferencia', solicitud_id=solicitud.id)
    elif solicitud.metodo_pago == 'webpay':
        # Si ya se procesó WebPay, mostrar resultado
        if solicitud.pagado:
            return redirect('pago_exitoso', solicitud_id=solicitud.id)
        else:
            messages.info(request, 'Procesando pago con WebPay...')
            return redirect('dashboard')
    
    # Fallback - calcular costo y mostrar confirmación básica
    tarifa_base = 30000
    tarifa_por_km = 1500
    tarifa_minima = 35000

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

    # Calcular tarifas actualizadas
    tarifa_base = 30000
    tarifa_por_km = 1500
    tarifa_minima = 35000

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

    tarifa_base = 30000  # Actualizada
    tarifa_por_km = 1500
    tarifa_minima = 35000

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

    tarifa_base = 30000  # Actualizada
    tarifa_por_km = 1500
    tarifa_minima = 35000

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
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    tarifa_base = 30000  # Actualizada
    tarifa_por_km = 1500
    tarifa_minima = 35000

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
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
    except:
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id)

    datos_bancarios = {
        'banco': 'Banco de Chile',
        'tipo_cuenta': 'Cuenta Corriente',
        'numero_cuenta': '12345678-9',
        'rut_titular': '12.345.678-9',
        'nombre_titular': 'Grúa Style SpA',
        'email_confirmacion': 'pagos@gruastyle.cl'
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

        tarifa_base = 30000  # Actualizada
        tarifa_por_km = 1500
        tarifa_minima = 35000

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
    """Vista para el pago de membresías"""
    plan = request.GET.get('plan', 'premium')  # Plan por defecto
    
    # Definir los planes disponibles
    planes = {
        'basico': {
            'nombre': 'Básico',
            'precio': 19990,
            'servicios_incluidos': 2,
            'descuento': 10,
            'color': '#4a90e2'
        },
        'premium': {
            'nombre': 'Premium', 
            'precio': 29990,
            'servicios_incluidos': 5,
            'descuento': 20,
            'color': '#00D563'
        },
        'vip': {
            'nombre': 'VIP',
            'precio': 49990,
            'servicios_incluidos': 0,  # Ilimitado
            'descuento': 30,
            'color': '#ff6b6b'
        }
    }
    
    if plan not in planes:
        plan = 'premium'
    
    plan_seleccionado = planes[plan]
    
    context = {
        'plan': plan,
        'plan_data': plan_seleccionado,
        'planes': planes
    }
    
    return render(request, 'grua_app/pago_membresia.html', context)


@login_required
def procesar_pago_membresia(request):
    """Vista para procesar el pago de membresía"""
    if request.method != 'POST':
        return redirect('membresias')
    
    try:
        # Obtener datos del formulario
        plan = request.POST.get('plan')
        metodo_pago = request.POST.get('metodo_pago')
        
        # Verificar que el usuario no tenga una membresía activa
        membresia_activa = Membresia.objects.filter(
            usuario=request.user,
            estado='activa'
        ).first()
        
        if membresia_activa and membresia_activa.esta_activa:
            messages.warning(request, 'Ya tienes una membresía activa.')
            return redirect('membresias')
        
        # Obtener tipo de membresía
        tipo_membresia = get_object_or_404(TipoMembresia, nombre=plan)
        
        # Crear la membresía
        from datetime import timedelta
        
        fecha_vencimiento = timezone.now() + timedelta(days=30)  # 30 días
        
        membresia = Membresia.objects.create(
            usuario=request.user,
            tipo_membresia=tipo_membresia,
            fecha_vencimiento=fecha_vencimiento,
            estado='activa'
        )
        
        # Crear registro de pago
        pago = PagoMembresia.objects.create(
            membresia=membresia,
            usuario=request.user,
            monto=tipo_membresia.precio,
            metodo_pago=metodo_pago,
            orden_compra=f"MEM_{timezone.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}",
            estado='completado'  # Por ahora marcamos como completado (simulado)
        )
        
        # Actualizar fecha de confirmación
        pago.fecha_confirmacion = timezone.now()
        pago.save()
        
        # Mensaje de éxito
        messages.success(
            request, 
            f'¡Membresía {tipo_membresia.get_nombre_display()} activada exitosamente! '
            f'Orden de compra: {pago.orden_compra}'
        )
        
        return redirect('perfil')
        
    except Exception as e:
        print(f"Error procesando pago de membresía: {e}")
        messages.error(request, 'Error al procesar el pago. Inténtalo nuevamente.')
        return redirect('pago_membresia')


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
    
    return redirect('perfil')