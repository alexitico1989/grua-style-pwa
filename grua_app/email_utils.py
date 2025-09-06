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


def get_base_email_template():
    """Template base simplificado y compatible para todos los emails"""
    return """
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333333;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
        }
        
        .email-container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .header {
            background: linear-gradient(135deg, #00D563 0%, #00B050 100%);
            padding: 30px 20px;
            text-align: center;
            color: #ffffff;
        }
        
        .logo {
            width: 60px;
            height: 60px;
            background-color: #ffffff;
            border-radius: 50%;
            margin: 0 auto 15px auto;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            font-weight: normal;
            color: #00D563;
            line-height: 1;
            text-align: center;
            vertical-align: middle;
        }
        
        .company-name {
            color: #ffffff;
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .tagline {
            color: #ffffff;
            font-size: 14px;
            opacity: 0.9;
        }
        
        .content {
            padding: 30px 20px;
            background-color: #ffffff;
        }
        
        .message-box {
            background-color: #e8f5e8;
            border: 2px solid #00D563;
            border-radius: 8px;
            padding: 20px;
            text-align: center;
            margin-bottom: 25px;
        }
        
        .message-box.warning {
            background-color: #fff3cd;
            border-color: #ffc107;
        }
        
        .message-box.error {
            background-color: #f8d7da;
            border-color: #dc3545;
        }
        
        .message-box.success {
            background-color: #d4edda;
            border-color: #28a745;
        }
        
        .message-box h2 {
            color: #00D563;
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 8px;
        }
        
        .message-box.warning h2 {
            color: #856404;
        }
        
        .message-box.error h2 {
            color: #721c24;
        }
        
        .message-box.success h2 {
            color: #155724;
        }
        
        .message-box p {
            color: #333333;
            font-size: 14px;
            margin: 0;
        }
        
        .intro-text {
            color: #333333;
            font-size: 16px;
            margin-bottom: 25px;
            text-align: center;
            line-height: 1.6;
        }
        
        .highlight {
            color: #00D563;
            font-weight: bold;
        }
        
        .info-section {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        
        .info-title {
            color: #00D563;
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 15px;
            border-bottom: 2px solid #00D563;
            padding-bottom: 8px;
        }
        
        .info-item {
            color: #333333;
            margin: 10px 0;
            padding: 8px 0;
            font-size: 14px;
            border-bottom: 1px solid #e9ecef;
        }
        
        .info-item:last-child {
            border-bottom: none;
        }
        
        .info-link {
            color: #00D563;
            text-decoration: none;
            font-weight: bold;
        }
        
        .info-link:hover {
            text-decoration: underline;
        }
        
        .code-display {
            background-color: #00D563;
            color: #ffffff;
            font-size: 32px;
            font-weight: bold;
            font-family: 'Courier New', monospace;
            text-align: center;
            padding: 25px;
            border-radius: 8px;
            letter-spacing: 8px;
            margin: 25px 0;
            border: 3px solid #00B050;
        }
        
        .table-section {
            background-color: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            overflow: hidden;
            margin: 20px 0;
        }
        
        .table-header {
            background-color: #00D563;
            color: #ffffff;
            padding: 15px 20px;
            font-weight: bold;
            font-size: 16px;
        }
        
        .table-row {
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #333333;
            font-size: 14px;
        }
        
        .table-row:last-child {
            border-bottom: none;
            background-color: #e8f5e8;
            font-weight: bold;
        }
        
        .cta-section {
            text-align: center;
            margin: 30px 0;
            padding: 25px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }
        
        .cta-title {
            color: #00D563;
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
        }
        
        .cta-button {
            display: inline-block;
            background-color: #00D563;
            color: #ffffff;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            font-size: 16px;
            margin: 10px;
            border: 2px solid #00D563;
        }
        
        .cta-button:hover {
            background-color: #00B050;
            border-color: #00B050;
            color: #ffffff;
            text-decoration: none;
        }
        
        .footer {
            background-color: #333333;
            padding: 25px 20px;
            text-align: center;
            color: #ffffff;
            font-size: 12px;
        }
        
        .footer-company {
            color: #00D563;
            font-weight: bold;
            font-size: 14px;
        }
        
        .feature-box {
            margin: 15px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-left: 4px solid #00D563;
            border-radius: 6px;
        }
        
        .feature-title {
            color: #333333;
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 5px;
        }
        
        .feature-text {
            color: #333333;
            font-size: 14px;
            line-height: 1.5;
        }
        
        .status-confirmed { color: #28a745; font-weight: bold; }
        .status-processing { color: #ffc107; font-weight: bold; }
        .status-completed { color: #28a745; font-weight: bold; }
        .status-cancelled { color: #dc3545; font-weight: bold; }
        .status-pending { color: #6c757d; font-weight: bold; }
        
        /* Responsive para móviles */
            @media only screen and (max-width: 600px) {
            .email-container {
                margin: 10px;
                border-radius: 8px;
            }
            
            .header {
                padding: 25px 15px;
            }
            
            .content {
                padding: 20px 15px;
            }
            
            .company-name {
                font-size: 24px;
            }
            
            .code-display {
                font-size: 24px;
                letter-spacing: 4px;
                padding: 20px;
            }
            
            .table-row {
                flex-direction: column;
                align-items: flex-start;
                gap: 5px;
                padding: 12px 15px;
            }
            
            .table-row span:first-child {
                font-weight: bold;
                color: #00D563;
                font-size: 14px;
            }
            
            .table-row span:last-child,
            .table-row strong {
                font-size: 14px;
                word-break: break-all;
                margin-top: 2px;
            }
            
            .cta-button {
                display: block;
                margin: 10px 0;
                width: 100%;
                box-sizing: border-box;
            }
        }
    </style>
    """

def format_local_datetime(dt):
    """Convierte datetime a zona horaria local y formatea"""
    return timezone.localtime(dt).strftime('%d/%m/%Y %H:%M')

def format_service_datetime(dt):
    """Formatea fecha de servicio (ya corregida en la base de datos)"""
    return dt.strftime('%d/%m/%Y %H:%M')


def enviar_email_bienvenida(user):
    """Envía email de bienvenida HTML al usuario usando Resend"""
    try:
        from django.core.mail import EmailMultiAlternatives
        
        subject = 'Bienvenido a Grúa Style'
        
        # Email HTML con iconos FontAwesome
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>¡Bienvenido a Grúa Style!</title>
    {get_base_email_template()}
</head>
<body>
    <div class="email-container">
        <div class="header">
            
            <h1 class="company-name">Grúa Style</h1>
            <p class="tagline">Servicio Premium 24/7</p>
        </div>
        
        <div class="content">
            <div class="message-box success">
                <h2>¡Bienvenido {user.first_name or user.username}!</h2>
                <p>Tu cuenta ha sido creada exitosamente</p>
            </div>
            
            <p class="intro-text">
                Nos alegra que te hayas unido a <strong style="color: #00D563;">Grúa Style</strong>, 
                la plataforma premium en servicios de grúa en la Región Metropolitana.
            </p>
            
            <div style="margin: 30px 0;">
                <h3 style="color: #00D563; font-size: 20px; font-weight: bold; margin-bottom: 20px; text-align: center;">
                    Con tu cuenta podrás:
                </h3>
                
                <div class="feature-box">
                    <div class="feature-title">Solicitar servicios fácilmente</div>
                    <div class="feature-text">
                        Ubica tu vehículo en el mapa y solicita ayuda al instante
                    </div>
                </div>
                
                <div class="feature-box">
                    <div class="feature-title">Múltiples métodos de pago</div>
                    <div class="feature-text">
                        Paga con Webpay, transferencia o efectivo según tu preferencia
                    </div>
                </div>
                
                <div class="feature-box">
                    <div class="feature-title">Seguimiento en tiempo real</div>
                    <div class="feature-text">
                        Monitorea el estado de tu solicitud desde tu dashboard
                    </div>
                </div>
                
                <div class="feature-box">
                    <div class="feature-title">Servicio Premium 24/7</div>
                    <div class="feature-text">
                        Estamos disponibles las 24 horas cuando nos necesites
                    </div>
                </div>
            </div>
            
            <div class="cta-section">
                <h3 class="cta-title">¡Comienza ahora!</h3>
                <a href="http://www.gruastyle.com/login/" class="cta-button">
                    Acceder a mi cuenta
                </a>
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Necesitas ayuda?</h3>
                <p style="color: #555555; margin-bottom: 20px;">
                    Si tienes alguna pregunta o necesitas asistencia:
                </p>
                <div class="info-item">
                    Email: <a href="mailto:contacto@gruastyle.com" class="info-link">contacto@gruastyle.com</a>
                </div>
                <div class="info-item">
                    Telefono: <a href="tel:+56989085315" class="info-link">+56 9 8908 5315</a>
                </div>
                <div class="info-item">
                    WhatsApp: <a href="https://wa.me/56989085315" class="info-link">+56 9 8908 5315</a>
                </div>
                <div class="info-item">
                    Web: <a href="http://www.gruastyle.com" class="info-link">www.gruastyle.com</a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div style="margin-bottom: 15px;">
                <span class="footer-company">Grúa Style</span>
            </div>
            <p>Este email fue enviado automáticamente. Por favor no responder a este mensaje.</p>
            <p>&copy; 2025 Grúa Style. Todos los derechos reservados.</p>
            <p style="color: #00D563; font-weight: 500;">Servicio Premium 24/7 en la Región Metropolitana</p>
        </div>
    </div>
</body>
</html>"""

        # Texto plano como fallback
        text_content = f"""
¡Bienvenido a Grúa Style, {user.first_name or user.username}!

Tu cuenta ha sido creada exitosamente.

Para acceder: http://www.gruastyle.com/login/

Contacto:
- Email: contacto@gruastyle.com
- Teléfono: +56 9 8908 5315

¡Gracias por unirte a Grúa Style!
        """

        # Crear email con HTML y texto plano
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

        print(f"✅ Email HTML de bienvenida enviado exitosamente a: {user.email}")
        return True

    except Exception as e:
        print(f"❌ Error enviando email de bienvenida: {e}")
        print(f"   Tipo de error: {type(e)}")
        return False


def enviar_codigo_reset_password(user):
    """Envía código de reset por email usando Resend"""
    try:
        from django.core.mail import EmailMultiAlternatives
        
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
        subject = 'Código para restablecer contraseña - Grúa Style'
        
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Código de Reset - Grúa Style</title>
    {get_base_email_template()}
</head>
<body>
    <div class="email-container">
        <div class="header">
            
            <h1 class="company-name">Grúa Style</h1>
            <p class="tagline">Servicio Premium 24/7</p>
        </div>
        
        <div class="content">
            <div class="message-box warning">
                <h2>Código de Verificación</h2>
                <p>Has solicitado restablecer tu contraseña</p>
            </div>
            
            <p class="intro-text">
                Hola <strong style="color: #00D563;">{user.username}</strong>,<br>
                Usa el siguiente código para restablecer tu contraseña:
            </p>
            
            <div class="code-display">
                {codigo}
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Información importante</h3>
                <div class="info-item">
                    Este código es válido por <strong>10 minutos únicamente</strong>
                </div>
                <div class="info-item">
                    Para restablecer tu contraseña:
                </div>
                <div style="margin-left: 20px; color: #555555;">
                    <div style="margin: 5px 0;">1. Regresa a la página web</div>
                    <div style="margin: 5px 0;">2. Ingresa este código de 6 dígitos</div>
                    <div style="margin: 5px 0;">3. Crea tu nueva contraseña</div>
                </div>
            </div>
            
            <div class="message-box">
                <h3 style="color: #00D563; margin-bottom: 10px;">Seguridad</h3>
                <p>Si no solicitaste este cambio, puedes ignorar este mensaje de forma segura. Tu cuenta permanece protegida.</p>
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Necesitas ayuda?</h3>
                <div class="info-item">
                    Email: <a href="mailto:contacto@gruastyle.com" class="info-link">contacto@gruastyle.com</a>
                </div>
                <div class="info-item">
                    Telefono: <a href="tel:+56989085315" class="info-link">+56 9 8908 5315</a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div style="margin-bottom: 15px;">
                <span class="footer-company">Grúa Style</span>
            </div>
            <p>Este email fue enviado automáticamente. Por favor no responder a este mensaje.</p>
            <p>&copy; 2025 Grúa Style. Todos los derechos reservados.</p>
        </div>
    </div>
</body>
</html>"""

        text_content = f"""
Hola {user.username},

Has solicitado restablecer tu contraseña en Grúa Style.

Tu código de verificación es: {codigo}

Este código es válido por 10 minutos únicamente.

Para restablecer tu contraseña:
1. Regresa a la página web
2. Ingresa este código de 6 dígitos
3. Crea tu nueva contraseña

Si no solicitaste este cambio, puedes ignorar este mensaje.

Contacto:
- Email: contacto@gruastyle.com
- Teléfono: +56 9 8908 5315

Saludos,
Equipo Grúa Style
        """

        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

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
        from django.core.mail import EmailMultiAlternatives
        
        user = solicitud.cliente

        # Usar las tarifas que se aplicaron al momento de crear la solicitud
        tarifa_base = getattr(solicitud, 'tarifa_base_aplicada', 30000)
        tarifa_por_km = getattr(solicitud, 'tarifa_km_aplicada', 1500)
        total = solicitud.costo_total  # Usar el total calculado y guardado

        if solicitud.distancia_km:
            costo_km = float(solicitud.distancia_km) * tarifa_por_km
        else:
            costo_km = 0

        # Preparar email
        subject = f'Comprobante de Solicitud #{solicitud.numero_orden} - Grúa Style'
        
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comprobante de Solicitud - Grúa Style</title>
    {get_base_email_template()}
</head>
<body>
    <div class="email-container">
        <div class="header">
            
            <h1 class="company-name">Grúa Style</h1>
            <p class="tagline">Servicio Premium 24/7</p>
        </div>
        
        <div class="content">
            <div class="message-box success">
                <h2>¡Solicitud Creada Exitosamente!</h2>
                <p>Tu servicio ha sido registrado correctamente</p>
            </div>
            
            <p class="intro-text">
                Hola <strong style="color: #00D563;">{user.username}</strong>,<br>
                Tu solicitud de servicio ha sido creada y procesada exitosamente.
            </p>
            
            <div class="info-section">
            <h3 class="info-title">Detalles de la Solicitud</h3>
            <div class="feature-box">
                <div class="feature-title">Número de Orden</div>
                <div class="feature-text" style="color: #00D563; font-weight: bold;">{solicitud.numero_orden}</div>
            </div>
            <div class="feature-box">
                <div class="feature-title">Estado</div>
                <div class="feature-text" style="color: #00D563; font-weight: bold;">{solicitud.get_estado_display()}</div>
            </div>
            <div class="feature-box">
                <div class="feature-title">Fecha de Solicitud</div>
                <div class="feature-text">{format_local_datetime(solicitud.fecha_solicitud)}</div>
            </div>
            <div class="feature-box">
                <div class="feature-title">Fecha de Servicio</div>
                <div class="feature-text">{format_service_datetime(solicitud.fecha_servicio)}</div>
            </div>
        </div>
            
            <div class="info-section">
                <h3 class="info-title">Ubicaciones</h3>
                <div class="info-item">
                    Origen: <strong>{solicitud.direccion_origen}</strong>
                </div>
                <div class="info-item">
                    Destino: <strong>{solicitud.direccion_destino}</strong>
                </div>
                {f'<div class="info-item">Distancia: <strong>{solicitud.distancia_km} km</strong></div>' if solicitud.distancia_km else ''}
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Problema Reportado</h3>
                <p style="color: #555555; padding: 10px; background: #f8f9fa; border-radius: 8px; margin: 0;">
                    {solicitud.descripcion_problema}
                </p>
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Detalle de Costos</h3>
                <div class="feature-box">
                    <div class="feature-title">Tarifa Base</div>
                    <div class="feature-text">${tarifa_base:,}</div>
                </div>
                {f'<div class="feature-box"><div class="feature-title">Costo por Distancia ({solicitud.distancia_km} km)</div><div class="feature-text">${costo_km:,.0f}</div></div>' if solicitud.distancia_km else ''}
                <div class="feature-box" style="background-color: #e8f5e8; border-left-color: #00D563;">
                    <div class="feature-title" style="color: #00D563; font-size: 18px;">TOTAL A PAGAR</div>
                    <div class="feature-text" style="color: #00D563; font-weight: bold; font-size: 20px;">${total:,.0f}</div>
                </div>
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Próximos Pasos</h3>
                <div class="feature-box">
                    <div class="feature-title">Contacto del conductor</div>
                    <div class="feature-text">Nuestro conductor se pondrá en contacto contigo para coordinar</div>
                </div>
            </div>
            
            <div class="cta-section">
                <h3 class="cta-title">Gestiona tu solicitud</h3>
                <a href="http://www.gruastyle.com/dashboard/" class="cta-button">
                    Ir al Dashboard
                </a>
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Necesitas ayuda?</h3>
                <div class="info-item">
                    Email: <a href="mailto:contacto@gruastyle.com" class="info-link">contacto@gruastyle.com</a>
                </div>
                <div class="info-item">
                    Telefono: <a href="tel:+56989085315" class="info-link">+56 9 8908 5315</a>
                </div>
                <div class="info-item">
                    WhatsApp: <a href="https://wa.me/56989085315" class="info-link">+56 9 8908 5315</a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div style="margin-bottom: 15px;">
                <span class="footer-company">Grúa Style</span>
            </div>
            <p>Este email fue enviado automáticamente. Por favor no responder a este mensaje.</p>
            <p>&copy; 2025 Grúa Style. Todos los derechos reservados.</p>
        </div>
    </div>
</body>
</html>"""

        text_content = f"""
Hola {user.username},

¡Tu solicitud de servicio ha sido creada exitosamente!

DETALLES DE LA SOLICITUD:
- Número de Orden: {solicitud.numero_orden}
- Estado: {solicitud.get_estado_display()}
- Fecha de Solicitud: {format_local_datetime(solicitud.fecha_solicitud)}
- Fecha de Servicio: {format_service_datetime(solicitud.fecha_servicio)}

UBICACIONES:
- Origen: {solicitud.direccion_origen}
- Destino: {solicitud.direccion_destino}
{f'- Distancia: {solicitud.distancia_km} km' if solicitud.distancia_km else ''}

PROBLEMA REPORTADO:
{solicitud.descripcion_problema}

DETALLE DE COSTOS:
- Tarifa Base: ${tarifa_base:,}
{f'- Costo por Distancia ({solicitud.distancia_km} km): ${costo_km:,.0f}' if solicitud.distancia_km else ''}
- TOTAL A PAGAR: ${total:,.0f}

PRÓXIMOS PASOS:
1. Confirma tu método de pago
2. Nuestro conductor se pondrá en contacto contigo

Gestiona tu solicitud: http://www.gruastyle.com/dashboard/

Contacto:
- Email: contacto@gruastyle.com
- Teléfono: +56 9 8908 5315

¡Gracias por confiar en Grúa Style!

Saludos cordiales,
Equipo Grúa Style
        """

        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

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
        from django.core.mail import EmailMultiAlternatives
        
        user = solicitud.cliente

        # Mensajes y estilos según el estado
        estados_info = {
            'confirmada': {
                'mensaje': 'Tu solicitud ha sido confirmada y asignada a un conductor.',
                'icono': 'fas fa-check-circle',
                'color': 'success'
            },
            'en_proceso': {
                'mensaje': 'Tu grúa está en camino. Te contactaremos pronto.',
                'icono': 'fas fa-truck',
                'color': 'warning'
            },
            'completada': {
                'mensaje': '¡Servicio completado! Gracias por usar Grúa Style.',
                'icono': 'fas fa-trophy',
                'color': 'success'
            },
            'cancelada': {
                'mensaje': 'Tu solicitud ha sido cancelada.',
                'icono': 'fas fa-times-circle',
                'color': 'error'
            },
            'pendiente_pago': {
                'mensaje': 'Tu solicitud está pendiente de pago.',
                'icono': 'fas fa-credit-card',
                'color': 'warning'
            },
        }

        estado_actual = solicitud.estado
        info_estado = estados_info.get(estado_actual, {
            'mensaje': f'Tu solicitud está ahora en estado: {solicitud.get_estado_display()}',
            'icono': 'fas fa-info-circle',
            'color': ''
        })

        subject = f'Actualización de Solicitud #{solicitud.numero_orden} - Grúa Style'
        
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Actualización de Estado - Grúa Style</title>
    {get_base_email_template()}
</head>
<body>
    <div class="email-container">
        <div class="header">
            
            <h1 class="company-name">Grúa Style</h1>
            <p class="tagline">Servicio Premium 24/7</p>
        </div>
        
        <div class="content">
            <div class="message-box {info_estado['color']}">
                <h2>Actualización de Estado</h2>
                <p>Hay una actualización en tu solicitud de servicio</p>
            </div>
            
            <p class="intro-text">
                Hola <strong style="color: #00D563;">{user.username}</strong>,<br>
                {info_estado['mensaje']}
            </p>
            
            <div class="table-section">
                <div class="table-header">
                    <h3 style="color: #fff; margin: 0;">Información de la Solicitud</h3>
                </div>
                <div class="table-row">
                    <span>Número de Orden:</span>
                    <strong style="color: #00D563;">{solicitud.numero_orden}</strong>
                </div>
                <div class="table-row">
                    <span>Estado Anterior:</span>
                    <span class="status-{estado_anterior.lower().replace(' ', '_')}">{estado_anterior}</span>
                </div>
                <div class="table-row">
                    <span>Estado Actual:</span>
                    <strong class="status-{estado_actual.lower().replace(' ', '_')}">{solicitud.get_estado_display()}</strong>
                </div>
                <div class="table-row">
                    <span>Fecha de Actualización:</span>
                    <span>{format_local_datetime(timezone.now())}</span>
                </div>
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Recordatorio del Servicio</h3>
                <div class="info-item">
                    Origen: <strong>{solicitud.direccion_origen}</strong>
                </div>
                <div class="info-item">
                    Destino: <strong>{solicitud.direccion_destino}</strong>
                </div>
                <div class="info-item">
                    Fecha de Servicio: <strong>{solicitud.fecha_servicio.strftime('%d/%m/%Y %H:%M')}</strong>
                </div>
            </div>
            
            <div class="cta-section">
                <h3 class="cta-title">Ver detalles completos</h3>
                <a href="http://www.gruastyle.com/dashboard/" class="cta-button">
                    Ir al Dashboard
                </a>
            </div>
            
            <div class="info-section">
                <h3 class="info-title">Preguntas o cambios?</h3>
                <div class="info-item">
                    Email: <a href="mailto:contacto@gruastyle.com" class="info-link">contacto@gruastyle.com</a>
                </div>
                <div class="info-item">
                    Telefono: <a href="tel:+56989085315" class="info-link">+56 9 8908 5315</a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <div style="margin-bottom: 15px;">
                <span class="footer-company">Grúa Style</span>
            </div>
            <p>Este email fue enviado automáticamente. Por favor no responder a este mensaje.</p>
            <p>&copy; 2025 Grúa Style. Todos los derechos reservados.</p>
        </div>
    </div>
</body>
</html>"""

        text_content = f"""
Hola {user.username},

Hay una actualización en tu solicitud de servicio:

INFORMACIÓN DE LA SOLICITUD:
- Número de Orden: {solicitud.numero_orden}
- Estado Anterior: {estado_anterior}
- Estado Actual: {solicitud.get_estado_display()}
- Fecha de Actualización: {format_local_datetime(timezone.now())}

MENSAJE:
{info_estado['mensaje']}

RECORDATORIO DEL SERVICIO:
- Origen: {solicitud.direccion_origen}
- Destino: {solicitud.direccion_destino}
- Fecha de Servicio: {format_service_datetime(solicitud.fecha_servicio)}

Ver detalles completos: http://www.gruastyle.com/dashboard/

Preguntas o cambios?
- Email: contacto@gruastyle.com
- Teléfono: +56 9 8908 5315

Gracias por usar Grúa Style,
Equipo Grúa Style
        """

        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

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