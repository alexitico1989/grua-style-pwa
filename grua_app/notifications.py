# grua_app/notifications.py
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def enviar_notificacion_nueva_solicitud(solicitud):
    """Envía notificación por Telegram cuando hay una nueva solicitud"""
    
    # Tipo de servicio
    tipo_servicio = 'ASISTENCIA MECÁNICA' if solicitud.tipo_servicio_categoria == 'asistencia' else 'SERVICIO DE GRÚA'
    
    # Información del cliente
    cliente_nombre = solicitud.cliente.get_full_name() or solicitud.cliente.username
    
    # Enviar mensaje por Telegram
    telegram_enviado = enviar_telegram_alert(solicitud, tipo_servicio, cliente_nombre)
    
    # Enviar email al administrador
    email_enviado = enviar_email_admin_urgente(solicitud, tipo_servicio, cliente_nombre)

    # Crear notificación en BD para historial
    crear_notificacion_bd(solicitud, tipo_servicio, cliente_nombre)
    
    # Log del resultado
    logger.info(f"Notificaciones enviadas para {solicitud.numero_orden}: Telegram={telegram_enviado}, Email={email_enviado}")
    print(f"📱 Notificaciones enviadas para {solicitud.numero_orden}: Telegram={telegram_enviado}, Email={email_enviado}")

    return telegram_enviado or email_enviado

def enviar_telegram_alert(solicitud, tipo_servicio, cliente_nombre):
    """Envía alerta por Telegram con formato empresarial"""
    try:
        # Verificar configuración
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)
        
        if not bot_token or not chat_id:
            print("❌ Configuración de Telegram no encontrada en settings.py")
            return False
        
        # Formatear dirección de destino para grúas
        destino_info = ""
        if solicitud.tipo_servicio_categoria != 'asistencia':
            destino_info = f"\n🎯 *Destino:* {solicitud.direccion_destino}"
        
        # Crear mensaje formateado
        mensaje = f"""🚨 *NUEVA SOLICITUD URGENTE*
🆔 *Orden:* `{solicitud.numero_orden}`
🔧 *Servicio:* {tipo_servicio}

👤 *Cliente:* {cliente_nombre}
📱 *Usuario:* @{solicitud.cliente.username}
🚗 *Vehículo:* {solicitud.marca_vehiculo} {solicitud.modelo_vehiculo}
🔑 *Tipo:* {solicitud.tipo_vehiculo or 'No especificado'}
📍 *Origen:* {solicitud.direccion_origen}{destino_info}

💰 *Valor:* ${'${:,}'.format(int(solicitud.costo_total))}
💳 *Pago:* {solicitud.get_metodo_pago_display()}
⏰ *Fecha Servicio:* {solicitud.fecha_servicio.strftime('%d/%m/%Y %H:%M')}
📝 *Estado:* {solicitud.get_estado_display()}

{f'📋 *Problema:* {solicitud.descripcion_problema}' if solicitud.descripcion_problema else ''}

🔗 [Ver en Admin](http://127.0.0.1:8000/admin/grua_app/solicitudservicio/{solicitud.id}/change/)

⚡ *Solicitud recibida:* {solicitud.fecha_solicitud.strftime('%d/%m/%Y %H:%M:%S')}"""

        # URL de la API de Telegram
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Datos del mensaje
        data = {
            'chat_id': chat_id,
            'text': mensaje,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        # Enviar mensaje
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Mensaje Telegram enviado para {solicitud.numero_orden}")
                print(f"✅ Mensaje Telegram enviado para {solicitud.numero_orden}")
                return True
            else:
                logger.error(f"❌ Error en respuesta Telegram: {result}")
                print(f"❌ Error en respuesta Telegram: {result}")
                return False
        else:
            logger.error(f"❌ Error HTTP Telegram: {response.status_code}")
            print(f"❌ Error HTTP Telegram: {response.status_code}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Excepción enviando Telegram: {e}")
        print(f"❌ Error enviando Telegram: {e}")
        return False

def crear_notificacion_bd(solicitud, tipo_servicio, cliente_nombre):
    """Crea registro en BD para historial de notificaciones"""
    try:
        from .models import NotificacionAdmin
        
        titulo = f"Nueva {tipo_servicio}"
        mensaje = f"Cliente: {cliente_nombre}\nOrden: {solicitud.numero_orden}\nValor: ${'${:,}'.format(int(solicitud.costo_total))}"
        
        # Crear registro en BD
        NotificacionAdmin.objects.create(
            titulo=titulo,
            mensaje=mensaje,
            solicitud=solicitud,
            tipo='nueva_solicitud',
            leida=False
        )
        
        logger.info(f"📝 Registro BD creado para {solicitud.numero_orden}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creando registro BD: {e}")
        return False

def enviar_telegram_test():
    """Función para probar el bot de Telegram"""
    try:
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)
        
        if not bot_token or not chat_id:
            print("❌ Configuración de Telegram no encontrada")
            return False
        
        mensaje = """🧪 *PRUEBA DEL SISTEMA*
✅ Bot de Telegram funcionando correctamente
🔔 Las alertas de nuevas solicitudes llegaran a este chat

📱 *Grúa Style - Sistema de Alertas*"""

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': mensaje,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✅ Mensaje de prueba enviado correctamente")
                return True
        
        print(f"❌ Error en prueba: {response.status_code}")
        return False
        
    except Exception as e:
        print(f"❌ Error en prueba Telegram: {e}")
        return False

def enviar_email_admin_urgente(solicitud, tipo_servicio, cliente_nombre):
    """Envía email de alerta al administrador"""
    try:
        from django.core.mail import send_mail
        
        admin_email = getattr(settings, 'NOTIFICATIONS_ADMIN_EMAIL', 'tu-email@gmail.com')
        
        subject = f'NUEVA SOLICITUD #{solicitud.numero_orden} - {tipo_servicio}'
        
        mensaje = f"""Nueva solicitud recibida:

Orden: {solicitud.numero_orden}
Cliente: {cliente_nombre}
Servicio: {tipo_servicio}
Vehículo: {solicitud.marca_vehiculo} {solicitud.modelo_vehiculo}
Origen: {solicitud.direccion_origen}
Valor: ${int(solicitud.costo_total):,}
Estado: {solicitud.get_estado_display()}

Ver detalles: http://127.0.0.1:8000/admin/grua_app/solicitudservicio/{solicitud.id}/change/
"""
        
        send_mail(
            subject=subject,
            message=mensaje,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=False,
        )
        
        print(f"Email de alerta enviado al administrador: {admin_email}")
        return True
        
    except Exception as e:
        print(f"Error enviando email de alerta: {e}")
        return False