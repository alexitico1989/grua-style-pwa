from django.urls import path
from django.http import HttpResponse
import json
from . import views

# 🆕 IMPORTAR VISTAS DE MERCADO PAGO
#from .views.payment_views import (
    #PaymentSelectionView,
    #MercadoPagoCheckoutView, 
    #BankTransferView,
    #PaymentResultView,
    #MercadoPagoWebhookView,
    #PaymentStatusView
#)


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

    # Perfil de usuario
    path('perfil/', views.perfil, name='perfil'),
    path('editar-perfil/', views.editar_perfil, name='editar_perfil'),
    path('cambiar-password/', views.cambiar_password, name='cambiar_password'),
    # ===== VISTA ESPECÍFICA PARA HISTORIAL (CORREGIDA) =====
    path('historial-servicios/', views.historial_servicios, name='historial_servicios'),

    # Membresías
    path('membresias/', views.membresias, name='membresias'),
    path('pago-membresia/', views.pago_membresia, name='pago_membresia'),
    path('procesar-pago-membresia/', views.procesar_pago_membresia, name='procesar_pago_membresia'),
    path('cancelar-membresia/', views.cancelar_membresia, name='cancelar_membresia'),
    path('membresia/result/<int:membresia_id>/', views.membresia_payment_result, name='membresia_payment_result'),
    path('membresia/transferencia/<int:membresia_id>/', views.confirmacion_transferencia_membresia, name='confirmacion_transferencia_membresia'),
    # ===== PÁGINAS ADICIONALES =====
    path('servicios/', views.servicios, name='servicios'),
    path('precios/', views.precios, name='precios'),
    path('contacto/', views.contacto, name='contacto'),
    
    
    # ===== PÁGINAS DE SERVICIOS ESPECIALIZADOS =====
    path('asistencia-mecanica/', views.asistencia_mecanica, name='asistencia_mecanica'),
    path('carga-bateria/', views.carga_bateria, name='carga_bateria'),

    # ===== SERVICIOS DE GRÚA =====
    path('solicitar-servicio/', views.solicitar_servicio, name='solicitar_servicio'),
    path('confirmacion/<int:solicitud_id>/', views.confirmacion_solicitud, name='confirmacion_solicitud'),
    path('detalles/<int:solicitud_id>/', views.ver_detalles_solicitud, name='ver_detalles_solicitud'),
    # Agregar estas URLs para manejo de pagos pendientes
    path('completar-pago-pendiente/<int:solicitud_id>/', views.completar_pago_pendiente, name='completar_pago_pendiente'),
    path('cambiar-a-efectivo/<int:solicitud_id>/', views.cambiar_a_efectivo, name='cambiar_a_efectivo'),
    path('cambiar-a-transferencia/<int:solicitud_id>/', views.cambiar_a_transferencia, name='cambiar_a_transferencia'),
    path('cancelar-solicitud-pendiente/<int:solicitud_id>/', views.cancelar_solicitud_pendiente, name='cancelar_solicitud_pendiente'),
    # URL para limpiar pagos expirados manualmente (solo administradores)
    path('admin/limpiar-solicitudes/', views.limpiar_solicitudes_manual, name='limpiar_solicitudes'),
    path('eliminar-solicitud-pendiente/<int:solicitud_id>/', views.eliminar_solicitud_pendiente, name='eliminar_solicitud_pendiente'),
    path('cambiar-a-mercadopago/<int:solicitud_id>/', views.cambiar_a_mercadopago, name='cambiar_a_mercadopago'),

    # 🆕 ===== NUEVAS RUTAS DE MERCADO PAGO =====
    # Selección y checkout de pagos
    #path('payment/select/<int:solicitud_id>/', PaymentSelectionView.as_view(), name='payment_selection'),
    #path('payment/mercadopago/<int:solicitud_id>/', MercadoPagoCheckoutView.as_view(), name='mercadopago_checkout'),
    #path('payment/transfer/<int:solicitud_id>/', BankTransferView.as_view(), name='bank_transfer'),
    #path('payment/result/<int:payment_id>/', PaymentResultView.as_view(), name='payment_result'),
    
    # APIs de Mercado Pago
    #path('api/mercadopago/webhook/', MercadoPagoWebhookView.as_view(), name='mercadopago_webhook'),
    #path('api/payment-status/<int:payment_id>/', PaymentStatusView.as_view(), name='payment_status'),

    # ===== RUTAS COMPLETAS DE ASISTENCIA MECÁNICA =====
    # Vista principal de asistencia
    path('solicitar-asistencia/', views.solicitar_asistencia, name='solicitar_asistencia'),
    
    # Pagos directos para asistencia mecánica
    path('procesar-efectivo-asistencia/', views.procesar_efectivo_directo_asistencia, 
         name='procesar_efectivo_directo_asistencia'),
    path('procesar-transferencia-asistencia/', views.procesar_transferencia_directo_asistencia, 
         name='procesar_transferencia_directo_asistencia'),
    path('iniciar-webpay-asistencia/', views.iniciar_pago_webpay_directo_asistencia, 
         name='iniciar_pago_webpay_directo_asistencia'),
    
    # Confirmaciones para asistencia mecánica
    path('confirmacion-efectivo-asistencia/<int:solicitud_id>/', 
         views.confirmacion_efectivo_asistencia, name='confirmacion_efectivo_asistencia'),
    path('confirmacion-transferencia-asistencia/<int:solicitud_id>/', 
         views.confirmacion_transferencia_asistencia, name='confirmacion_transferencia_asistencia'),

    # PDF y Documentos
    path('pdf/solicitud/<int:solicitud_id>/', views.descargar_pdf_solicitud, name='descargar_pdf_solicitud'),
    path('pdf/comprobante/<int:solicitud_id>/', views.descargar_pdf_comprobante, name='descargar_pdf_comprobante'),
    path('imprimir/<int:solicitud_id>/', views.imprimir_solicitud, name='imprimir_solicitud'),
    path('reenviar-comprobante/<int:solicitud_id>/', views.reenviar_comprobante, name='reenviar_comprobante'),
   
    # 🆕 ===== API DE GEOCODIFICACIÓN =====
    path('api/geocodificar/', views.geocodificar_coordenadas, name='geocodificar_coordenadas'),
    
    # 🆕 ===== SISTEMA COMPLETO DE MERCADO PAGO =====
    path('payment/select/<int:solicitud_id>/', views.payment_selection, name='payment_selection'),
    path('payment/mercadopago/<int:solicitud_id>/', views.mercadopago_checkout, name='mercadopago_checkout'),
    path('payment/result/<int:solicitud_id>/', views.payment_result, name='payment_result'),
    path('payment/transfer/<int:solicitud_id>/', views.bank_transfer_mp, name='bank_transfer_mp'),
   
    # 🔄 ===== PAGOS EXISTENTES (MANTENIDOS PARA COMPATIBILIDAD) =====
    # Nota: Estas rutas se mantienen para no romper funcionalidad existente
    # Gradualmente se pueden migrar a usar las nuevas rutas de Mercado Pago
    path('procesar-pago/<int:solicitud_id>/', views.procesar_pago, name='procesar_pago'),
    path('transferencia/<int:solicitud_id>/', views.procesar_transferencia, name='procesar_transferencia'),
    path('efectivo/<int:solicitud_id>/', views.procesar_efectivo, name='procesar_efectivo'),
    path('confirmacion-transferencia/<int:solicitud_id>/', 
         views.confirmacion_transferencia, name='confirmacion_transferencia'),
    path('confirmacion-efectivo/<int:solicitud_id>/', 
         views.confirmacion_efectivo, name='confirmacion_efectivo'),

    # 🗑️ WebPay (DEPRECATED - Reemplazado por Mercado Pago)
    # Mantenidas para compatibilidad, pero se recomienda usar las nuevas rutas de MP
    path('webpay/iniciar/<int:solicitud_id>/', views.iniciar_pago_webpay, name='iniciar_pago_webpay'),
    path('webpay/return/', views.webpay_return, name='webpay_return'),
    path('pago-exitoso/<int:solicitud_id>/', views.pago_exitoso, name='pago_exitoso'),

    # Reset de contraseña
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-code/', views.verify_reset_code, name='verify_reset_code'),
    path('reset-password-confirm/', views.reset_password_confirm, name='reset_password_confirm'),
    path('resend-reset-code/', views.resend_reset_code, name='resend_reset_code'),
    
    # 🆕 ===== RUTAS ADICIONALES ÚTILES =====
    # Tracking de servicios (si no existe)
    # path('tracking/<int:solicitud_id>/', views.tracking_servicio, name='tracking_servicio'),
]