# grua_app/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Configuracion, Cliente, CodigoVerificacion, Conductor, 
    SolicitudServicio, Vehiculo, HistorialPago, AsignacionServicio,
    TipoMembresia, Membresia, PagoMembresia,
    MercadoPagoPayment, MercadoPagoWebhook, DisponibilidadServicio, NotificacionAdmin  # 🆕 NUEVOS MODELOS
)
 
@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ('tarifa_base', 'tarifa_por_km', 'tarifa_minima', 'fecha_actualizacion')
    fieldsets = (
        ('Tarifas', {
            'fields': ('tarifa_base', 'tarifa_por_km', 'tarifa_minima')
        }),
        ('Operación', {
            'fields': ('hora_inicio_operacion', 'hora_fin_operacion', 'radio_cobertura_km', 'tiempo_maximo_espera_minutos')
        }),
        ('Notificaciones', {
            'fields': ('email_notificaciones', 'enviar_sms')
        }),
    )

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('user', 'telefono', 'rut', 'fecha_registro')
    list_filter = ('fecha_registro',)
    search_fields = ('user__username', 'user__email', 'telefono', 'rut')
    readonly_fields = ('fecha_registro',)

@admin.register(CodigoVerificacion)
class CodigoVerificacionAdmin(admin.ModelAdmin):
    list_display = ('user', 'codigo', 'tipo', 'fecha_creacion', 'usado')
    list_filter = ('tipo', 'usado', 'fecha_creacion')
    search_fields = ('user__username', 'codigo')
    readonly_fields = ('fecha_creacion',)

@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ('user', 'licencia_conducir', 'telefono', 'vehiculo_asignado', 'activo')
    list_filter = ('activo', 'fecha_registro')
    search_fields = ('user__username', 'licencia_conducir', 'telefono')
    readonly_fields = ('fecha_registro',)

@admin.register(SolicitudServicio)
class SolicitudServicioAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'cliente', 'estado', 'metodo_pago', 'pagado', 'fecha_solicitud')
    list_filter = ('estado', 'metodo_pago', 'pagado', 'fecha_solicitud')
    search_fields = ('numero_orden', 'cliente__username', 'direccion_origen', 'direccion_destino')
    
    # 🔄 CAMPOS ACTUALIZADOS - REMOVIDOS LOS DE WEBPAY
    readonly_fields = ('numero_orden', 'fecha_solicitud', 'fecha_actualizacion')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('numero_orden', 'cliente', 'estado', 'fecha_solicitud', 'fecha_actualizacion')
        }),
        ('Servicio', {
            'fields': ('direccion_origen', 'direccion_destino', 'fecha_servicio', 'descripcion_problema', 'distancia_km')
        }),
        ('Vehículo del Cliente', {
            'fields': ('tipo_vehiculo', 'marca_vehiculo', 'modelo_vehiculo', 'placa_vehiculo'),
            'classes': ('collapse',)
        }),
        ('Pago', {
            'fields': ('metodo_pago', 'costo_total', 'pagado'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('cliente')

# 🆕 ADMIN PARA MERCADO PAGO
@admin.register(MercadoPagoPayment)
class MercadoPagoPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'mercadopago_id', 'user', 'status', 'payment_method_type', 
        'transaction_amount', 'created_at', 'link_to_solicitud'
    )
    list_filter = ('status', 'payment_method_type', 'currency_id', 'created_at')
    search_fields = (
        'mercadopago_id', 'external_reference', 'user__username', 
        'payer_email', 'payer_identification_number'
    )
    readonly_fields = (
        'mercadopago_id', 'preference_id', 'status', 'status_detail',
        'payment_method_id', 'installments', 'idempotency_key',
        'created_at', 'updated_at', 'approved_at'
    )
    
    fieldsets = (
        ('Información del Pago', {
            'fields': (
                'mercadopago_id', 'preference_id', 'status', 'status_detail',
                'transaction_amount', 'currency_id'
            )
        }),
        ('Método de Pago', {
            'fields': (
                'payment_method_type', 'payment_method_id', 'installments'
            )
        }),
        ('Información del Pagador', {
            'fields': (
                'user', 'payer_email', 'payer_identification_type', 
                'payer_identification_number'
            )
        }),
        ('Metadatos', {
            'fields': (
                'external_reference', 'description', 'idempotency_key',
                'emergency_contact', 'special_instructions'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    def link_to_solicitud(self, obj):
        if obj.solicitud_servicio:
            link = reverse("admin:grua_app_solicitudservicio_change", 
                          args=[obj.solicitud_servicio.id])
            return format_html('<a href="{}">Ver Solicitud</a>', link)
        return "Sin solicitud"
    link_to_solicitud.short_description = "Solicitud"

@admin.register(MercadoPagoWebhook)
class MercadoPagoWebhookAdmin(admin.ModelAdmin):
    list_display = (
        'webhook_id', 'webhook_type', 'data_id', 'processed', 
        'retry_count', 'created_at', 'link_to_payment'
    )
    list_filter = ('webhook_type', 'processed', 'created_at')
    search_fields = ('webhook_id', 'data_id', 'webhook_type')
    readonly_fields = (
        'webhook_id', 'webhook_type', 'action', 'data_id', 
        'raw_data', 'created_at', 'processed_at'
    )
    
    fieldsets = (
        ('Información del Webhook', {
            'fields': ('webhook_id', 'webhook_type', 'action', 'data_id')
        }),
        ('Estado del Procesamiento', {
            'fields': ('processed', 'processed_at', 'retry_count', 'error_message')
        }),
        ('Datos Raw', {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
    )
    
    def link_to_payment(self, obj):
        if obj.payment:
            link = reverse("admin:grua_app_mercadopagopayment_change", 
                          args=[obj.payment.id])
            return format_html('<a href="{}">Ver Pago</a>', link)
        return "Sin pago"
    link_to_payment.short_description = "Pago"

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'tipo', 'marca', 'modelo', 'estado', 'conductor_asignado')
    list_filter = ('tipo', 'estado', 'marca')
    search_fields = ('patente', 'marca', 'modelo')
    readonly_fields = ('fecha_registro', 'fecha_actualizacion')

@admin.register(HistorialPago)
class HistorialPagoAdmin(admin.ModelAdmin):
    list_display = ('solicitud', 'monto', 'metodo_pago', 'estado', 'fecha_transaccion', 'link_to_mp_payment')
    list_filter = ('metodo_pago', 'estado', 'fecha_transaccion')
    search_fields = ('solicitud__numero_orden', 'transaction_id')
    readonly_fields = ('fecha_transaccion', 'fecha_actualizacion')
    
    def link_to_mp_payment(self, obj):
        if obj.mercadopago_payment:
            link = reverse("admin:grua_app_mercadopagopayment_change", 
                          args=[obj.mercadopago_payment.id])
            return format_html('<a href="{}">Ver MP</a>', link)
        return "Sin MP"
    link_to_mp_payment.short_description = "Mercado Pago"

@admin.register(AsignacionServicio)
class AsignacionServicioAdmin(admin.ModelAdmin):
    list_display = ('solicitud', 'conductor', 'vehiculo', 'estado', 'fecha_asignacion')
    list_filter = ('estado', 'fecha_asignacion')
    search_fields = ('solicitud__numero_orden', 'conductor__user__username')
    readonly_fields = ('fecha_asignacion',)

@admin.register(TipoMembresia)
class TipoMembresiaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio', 'servicios_incluidos', 'descuento_porcentaje', 'activo')
    list_filter = ('activo', 'nombre')
    readonly_fields = ('fecha_creacion',)

@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo_membresia', 'estado', 'fecha_inicio', 'fecha_vencimiento', 'servicios_utilizados')
    list_filter = ('estado', 'tipo_membresia', 'auto_renovar')
    search_fields = ('usuario__username', 'usuario__email')
    readonly_fields = ('fecha_inicio',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('usuario', 'tipo_membresia')

@admin.register(DisponibilidadServicio)
class DisponibilidadServicioAdmin(admin.ModelAdmin):
    list_display = ('activo', 'mensaje_personalizado', 'fecha_actualizacion', 'actualizado_por')
    list_filter = ('activo', 'fecha_actualizacion')
    search_fields = ('mensaje_personalizado',)
    readonly_fields = ('fecha_actualizacion',)
    
    def has_add_permission(self, request):
        # Solo permitir un registro
        return not DisponibilidadServicio.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar el registro
        return False

@admin.register(PagoMembresia)
class PagoMembresiaAdmin(admin.ModelAdmin):
    list_display = ('orden_compra', 'usuario', 'monto', 'metodo_pago', 'estado', 'fecha_pago', 'link_to_mp_payment')
    list_filter = ('metodo_pago', 'estado', 'fecha_pago')
    search_fields = ('orden_compra', 'usuario__username', 'numero_transferencia')
    readonly_fields = ('fecha_pago',)
    
    fieldsets = (
        ('Información del Pago', {
            'fields': ('orden_compra', 'usuario', 'membresia', 'monto', 'metodo_pago', 'estado')
        }),
        ('Mercado Pago', {
            'fields': ('mercadopago_payment',),
            'classes': ('collapse',)
        }),
        ('Transferencia Bancaria', {
            'fields': ('numero_transferencia', 'comprobante_transferencia'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_pago', 'fecha_confirmacion'),
            'classes': ('collapse',)
        }),
        ('Adicional', {
            'fields': ('notas', 'datos_adicionales'),
            'classes': ('collapse',)
        }),
    )
    
    def link_to_mp_payment(self, obj):
        if obj.mercadopago_payment:
            link = reverse("admin:grua_app_mercadopagopayment_change", 
                          args=[obj.mercadopago_payment.id])
            return format_html('<a href="{}">Ver MP</a>', link)
        return "Sin MP"
    link_to_mp_payment.short_description = "Mercado Pago"

# Personalización del admin principal
admin.site.site_header = "Grúa Style - Administración"
admin.site.site_title = "Grúa Style Admin"
admin.site.index_title = "Panel de Control"

@admin.register(NotificacionAdmin)
class NotificacionAdminConfig(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'leida', 'fecha_creacion', 'solicitud')
    list_filter = ('tipo', 'leida', 'fecha_creacion')
    search_fields = ('titulo', 'mensaje')
    readonly_fields = ('fecha_creacion',)
    ordering = ['-fecha_creacion']
    
    def has_add_permission(self, request):
        # Solo permitir ver, no crear manualmente
        return False