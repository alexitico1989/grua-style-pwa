# grua_app/email_utils.py
# Sistema de emails usando Resend para Grúa Style

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import CodigoVerificacion
import random
import string


def generar_codigo():
    """Genera un código aleatorio de 6 dígitos"""
    return ''.join(random.choices(string.digits, k=6))


def enviar_email_bienvenida(user):
    """Envía email de bienvenida al usuario usando Resend"""
    try:
        subject = '🚗 ¡Bienvenido a Grúa Style!'
        message = f"""
Hola {user.username},

¡Bienvenido a Grúa Style! 🎉

Tu cuenta ha sido creada exitosamente.
Ya puedes solicitar servicios de grúa las 24 horas del día, los 7 días de la semana.

📋 Datos de tu cuenta:
- Usuario: {user.username}
- Email: {user.email}

🌐 Para acceder a tu cuenta:
http://127.0.0.1:8000/login/

🚗 Servicios disponibles:
- Grúa para vehículos livianos
- Auxilio mecánico
- Servicio de emergencia 24/7
- Precios transparentes

¡Gracias por confiar en Grúa Style para tus necesidades de transporte!

Saludos cordiales,
Equipo Grúa Style 🚗🎨
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        print(f"✅ Email de bienvenida enviado exitosamente a: {user.email}")
        return True

    except Exception as e:
        print(f"❌ Error enviando email de bienvenida: {e}")
        print(f"   Tipo de error: {type(e)}")
        return False


def enviar_codigo_reset_password(user):
    """Envía código de reset por email usando Resend"""
    try:
        # Crear código
        codigo = generar_codigo()

        # Eliminar códigos anteriores no usados
        CodigoVerificacion.objects.filter(
            user=user,
            tipo='reset_password',
            usado=False
        ).delete()

        # Crear nuevo código
        codigo_obj = CodigoVerificacion.objects.create(
            user=user,
            codigo=codigo,
            tipo='reset_password'
        )

        # Enviar email con código
        subject = '🔑 Código para restablecer contraseña - Grúa Style'
        message = f"""
Hola {user.username},

Has solicitado restablecer tu contraseña en Grúa Style.

🔑 Tu código de verificación es: {codigo}

⏱️ Este código es válido por 10 minutos únicamente.

📱 Para restablecer tu contraseña:
1. Regresa a la página web
2. Ingresa este código de 6 dígitos
3. Crea tu nueva contraseña

🛡️ Seguridad:
Si no solicitaste este cambio, puedes ignorar este mensaje de forma segura.
Tu cuenta permanece protegida.

¿Necesitas ayuda? Contáctanos:
📧 Email: soporte@gruastyle.com
📞 Teléfono: +56 9 1234 5678

Saludos,
Equipo Grúa Style 🚗
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        print(f"✅ Código de reset enviado exitosamente a: {user.email}")
        print(f"   Código generado: {codigo}")

        return codigo_obj

    except Exception as e:
        print(f"❌ Error enviando código de reset: {e}")
        print(f"   Tipo de error: {type(e)}")
        return None


def enviar_comprobante_solicitud(solicitud):
    """Envía comprobante de solicitud por email usando Resend"""
    try:
        user = solicitud.cliente

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

        # Preparar email
        subject = f'🧾 Comprobante de Solicitud #{solicitud.numero_orden} - Grúa Style'
        message = f"""
Hola {user.username},

¡Tu solicitud de servicio ha sido creada exitosamente! 🎉

📋 DETALLES DE LA SOLICITUD:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Número de Orden: {solicitud.numero_orden}
- Estado: {solicitud.get_estado_display()}
- Fecha de Solicitud: {solicitud.fecha_solicitud.strftime('%d/%m/%Y %H:%M')}
- Fecha de Servicio: {solicitud.fecha_servicio.strftime('%d/%m/%Y %H:%M')}

📍 UBICACIONES:
- Origen: {solicitud.direccion_origen}
- Destino: {solicitud.direccion_destino}
{f'• Distancia: {solicitud.distancia_km} km' if solicitud.distancia_km else ''}

🔧 PROBLEMA REPORTADO:
{solicitud.descripcion_problema}

💰 DETALLE DE COSTOS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Tarifa Base: ${tarifa_base:,}
{f'• Costo por Distancia ({solicitud.distancia_km} km): ${costo_km:,.0f}' if solicitud.distancia_km else ''}
- TOTAL A PAGAR: ${total:,.0f}

📱 PRÓXIMOS PASOS:
1. Confirma tu método de pago
2. Nuestro conductor se pondrá en contacto contigo
3. Recibirás actualizaciones del estado por email

🌐 Gestiona tu solicitud:
http://127.0.0.1:8000/dashboard/

📞 ¿Necesitas ayuda?
- Email: soporte@gruastyle.com
- Teléfono: +56 9 1234 5678
- WhatsApp: +56 9 1234 5678

¡Gracias por confiar en Grúa Style!

Saludos cordiales,
Equipo Grúa Style 🚗🎨
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        print(f"✅ Comprobante enviado exitosamente a: {user.email}")
        print(f"   Orden: {solicitud.numero_orden}")
        print(f"   Total: ${total:,.0f}")

        return True

    except Exception as e:
        print(f"❌ Error enviando comprobante: {e}")
        print(f"   Tipo de error: {type(e)}")
        return False


def enviar_actualizacion_estado(solicitud, estado_anterior):
    """Envía email cuando cambia el estado de la solicitud"""
    try:
        user = solicitud.cliente

        # Mensajes según el estado
        mensajes_estado = {
            'confirmada': '✅ Tu solicitud ha sido confirmada y asignada a un conductor.',
            'en_proceso': '🚗 Tu grúa está en camino. Te contactaremos pronto.',
            'completada': '🎉 ¡Servicio completado! Gracias por usar Grúa Style.',
            'cancelada': '❌ Tu solicitud ha sido cancelada.',
            'pendiente_pago': '💳 Tu solicitud está pendiente de pago.',
        }

        emoji_estados = {
            'confirmada': '✅',
            'en_proceso': '🚗',
            'completada': '🎉',
            'cancelada': '❌',
            'pendiente_pago': '💳',
        }

        estado_actual = solicitud.estado
        emoji = emoji_estados.get(estado_actual, '📋')
        mensaje_estado = mensajes_estado.get(
            estado_actual, f'Tu solicitud está ahora en estado: {solicitud.get_estado_display()}')

        subject = f'{emoji} Actualización de Solicitud #{solicitud.numero_orden} - Grúa Style'
        message = f"""
Hola {user.username},

Hay una actualización en tu solicitud de servicio:

📋 INFORMACIÓN DE LA SOLICITUD:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Número de Orden: {solicitud.numero_orden}
- Estado Anterior: {estado_anterior}
- Estado Actual: {solicitud.get_estado_display()}
- Fecha de Actualización: {timezone.now().strftime('%d/%m/%Y %H:%M')}

{emoji} MENSAJE:
{mensaje_estado}

📍 RECORDATORIO DEL SERVICIO:
- Origen: {solicitud.direccion_origen}
- Destino: {solicitud.direccion_destino}
- Fecha de Servicio: {solicitud.fecha_servicio.strftime('%d/%m/%Y %H:%M')}

🌐 Ver detalles completos:
http://127.0.0.1:8000/dashboard/

📞 ¿Preguntas o cambios?
- Email: soporte@gruastyle.com
- Teléfono: +56 9 1234 5678

Gracias por usar Grúa Style,
Equipo Grúa Style 🚗🎨
        """

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        print(f"✅ Actualización de estado enviada a: {user.email}")
        print(f"   Orden: {solicitud.numero_orden}")
        print(f"   Estado: {estado_anterior} → {estado_actual}")

        return True

    except Exception as e:
        print(f"❌ Error enviando actualización: {e}")
        print(f"   Tipo de error: {type(e)}")
        return False


def verificar_codigo_reset(user, codigo_ingresado):
    """Verifica código de reset"""
    try:
        # Buscar código válido (no expirado y no usado)
        codigo_obj = CodigoVerificacion.objects.filter(
            user=user,
            codigo=codigo_ingresado,
            tipo='reset_password',
            usado=False
        ).first()

        if codigo_obj:
            # Verificar si no ha expirado (10 minutos)
            tiempo_limite = timezone.timedelta(minutes=10)
            if timezone.now() - codigo_obj.fecha_creacion > tiempo_limite:
                print(f"⏱️ Código expirado para {user.username}")
                return None

            return codigo_obj

        print(f"❌ Código inválido para {user.username}: {codigo_ingresado}")
        return None

    except Exception as e:
        print(f"❌ Error verificando código: {e}")
        return None
