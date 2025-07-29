from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import SolicitudServicio, Cliente

# Configurar SolicitudServicio en el admin


@admin.register(SolicitudServicio)
class SolicitudServicioAdmin(admin.ModelAdmin):
    list_display = [
        'numero_orden',
        'cliente',
        'estado',
        'metodo_pago',
        'costo_total',
        'fecha_solicitud',
        'pagado'
    ]

    list_filter = [
        'estado',
        'metodo_pago',
        'pagado',
        'fecha_solicitud'
    ]

    search_fields = [
        'numero_orden',
        'cliente__username',
        'direccion_origen',
        'direccion_destino'
    ]

    readonly_fields = [
        'id',
        'fecha_solicitud',
        'webpay_token',
        'webpay_buy_order',
        'webpay_authorization_code'
    ]

    fieldsets = (
        ('Información Básica', {
            'fields': (
                'numero_orden',
                'cliente',
                'estado',
                'fecha_solicitud'
            )
        }),
        ('Detalles del Servicio', {
            'fields': (
                'direccion_origen',
                'direccion_destino',
                'fecha_servicio',
                'distancia_km',
                'descripcion_problema'
            )
        }),
        ('Información de Pago', {
            'fields': (
                'metodo_pago',
                'costo_total',
                'pagado',
                'webpay_token',
                'webpay_buy_order',
                'webpay_authorization_code'
            )
        })
    )

    # Acciones personalizadas
    def marcar_como_confirmada(self, request, queryset):
        queryset.update(estado='confirmada')
        self.message_user(
            request, f'{queryset.count()} solicitudes marcadas como confirmadas.')
    marcar_como_confirmada.short_description = "Marcar como confirmada"

    def marcar_como_completada(self, request, queryset):
        queryset.update(estado='completada')
        self.message_user(
            request, f'{queryset.count()} solicitudes marcadas como completadas.')
    marcar_como_completada.short_description = "Marcar como completada"

    actions = [marcar_como_confirmada, marcar_como_completada]

# Configurar Cliente en el admin


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['user', 'telefono', 'rut']
    search_fields = ['user__username', 'user__email', 'telefono', 'rut']

# Personalizar el admin de Usuario


class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name',
                    'last_name', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']


# Re-registrar User con la configuración personalizada
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Personalizar títulos del admin
admin.site.site_header = "GrúaExpress - Administración"
admin.site.site_title = "GrúaExpress Admin"
admin.site.index_title = "Panel de Administración"
