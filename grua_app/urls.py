from django.urls import path
from django.http import HttpResponse
import json
from . import views


def manifest_view(request):
    """Vista para servir el manifest.json dinámicamente"""
    manifest = {
        "name": "Grúa Style - Servicio de Grúa",
        "short_name": "Grúa Style",
        "description": "Solicita servicios de grúa con estilo. Rápido, seguro y confiable las 24 horas.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#2d5bff",
        "orientation": "portrait-primary",
        "categories": ["business", "utilities", "transportation"],
        "lang": "es-CL",
        "icons": [
            {
                "src": "/static/pwa/icon-72x72.png",
                "sizes": "72x72",
                "type": "image/png"
            },
            {
                "src": "/static/pwa/icon-96x96.png",
                "sizes": "96x96",
                "type": "image/png"
            },
            {
                "src": "/static/pwa/icon-128x128.png",
                "sizes": "128x128",
                "type": "image/png"
            },
            {
                "src": "/static/pwa/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/pwa/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ],
        "shortcuts": [
            {
                "name": "Solicitar Grúa",
                "short_name": "Solicitar",
                "description": "Crear nueva solicitud de grúa",
                "url": "/solicitar-servicio/",
                "icons": [{"src": "/static/pwa/icon-192x192.png", "sizes": "192x192"}]
            },
            {
                "name": "Dashboard",
                "short_name": "Panel",
                "description": "Ver historial de solicitudes",
                "url": "/dashboard/",
                "icons": [{"src": "/static/pwa/icon-192x192.png", "sizes": "192x192"}]
            }
        ]
    }

    return HttpResponse(json.dumps(manifest), content_type='application/json')


def service_worker_view(request):
    """Vista para servir el service worker"""
    try:
        with open('static/pwa/sw.js', 'r', encoding='utf-8') as f:
            content = f.read()
        response = HttpResponse(content, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        return response
    except FileNotFoundError:
        return HttpResponse('console.log("Service worker not found");', content_type='application/javascript')


urlpatterns = [
    # PWA URLs
    path('manifest.json', manifest_view, name='manifest'),
    path('sw.js', service_worker_view, name='service_worker'),

    # Páginas principales
    path('', views.home, name='home'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('registro/', views.registro, name='registro'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('historial-servicios/', views.dashboard, name='historial_servicios'),

    # Servicios
    path('solicitar-servicio/', views.solicitar_servicio,
         name='solicitar_servicio'),
    path('confirmacion/<int:solicitud_id>/',
         views.confirmacion_solicitud, name='confirmacion_solicitud'),

    # PDF y Documentos
    path('pdf/solicitud/<int:solicitud_id>/',
         views.descargar_pdf_solicitud, name='descargar_pdf_solicitud'),
    path('pdf/comprobante/<int:solicitud_id>/',
         views.descargar_pdf_comprobante, name='descargar_pdf_comprobante'),
    path('imprimir/<int:solicitud_id>/',
         views.imprimir_solicitud, name='imprimir_solicitud'),
    path('reenviar-comprobante/<int:solicitud_id>/',
         views.reenviar_comprobante, name='reenviar_comprobante'),

    # Pagos
    path('procesar-pago/<int:solicitud_id>/',
         views.procesar_pago, name='procesar_pago'),
    path('transferencia/<int:solicitud_id>/',
         views.procesar_transferencia, name='procesar_transferencia'),
    path('efectivo/<int:solicitud_id>/',
         views.procesar_efectivo, name='procesar_efectivo'),
    path('confirmacion-transferencia/<int:solicitud_id>/',
         views.confirmacion_transferencia, name='confirmacion_transferencia'),
    path('confirmacion-efectivo/<int:solicitud_id>/',
         views.confirmacion_efectivo, name='confirmacion_efectivo'),

    # WebPay
    path('webpay/iniciar/<int:solicitud_id>/',
         views.iniciar_pago_webpay, name='iniciar_pago_webpay'),
    path('webpay/return/', views.webpay_return, name='webpay_return'),
    path('pago-exitoso/<int:solicitud_id>/',
         views.pago_exitoso, name='pago_exitoso'),

    # Reset de contraseña
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'),
    path('reset-password-confirm/', views.reset_password_confirm,
         name='reset_password_confirm'),
    path('resend-reset-code/', views.resend_reset_code, name='resend_reset_code'),
]
