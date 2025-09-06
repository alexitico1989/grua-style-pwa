from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Configuracion(models.Model):
    tarifa_base = models.DecimalField(max_digits=10, decimal_places=2, default=15000)
    tarifa_por_km = models.DecimalField(max_digits=10, decimal_places=2, default=1200)
    tarifa_minima = models.DecimalField(max_digits=10, decimal_places=2, default=20000)
    hora_inicio_operacion = models.TimeField(default='07:00')
    hora_fin_operacion = models.TimeField(default='22:00')
    radio_cobertura_km = models.DecimalField(max_digits=6, decimal_places=2, default=50)
    tiempo_maximo_espera_minutos = models.IntegerField(default=60)
    email_notificaciones = models.EmailField(default='admin@gruaexpress.cl')
    enviar_sms = models.BooleanField(default=False)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración'
        verbose_name_plural = 'Configuraciones'
    
    def __str__(self):
        return f"Configuración - Tarifa base: ${self.tarifa_base}"

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15)
    rut = models.CharField(max_length=12, unique=True)
    direccion = models.CharField(max_length=255)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.telefono}"
    
    class Meta:
        ordering = ['-fecha_registro']

class CodigoVerificacion(models.Model):
    TIPO_CHOICES = [
        ('reset_password', 'Reset Password'),
        ('verificacion_email', 'Email Verification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=6)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    usado = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.codigo} ({self.tipo})"
    
    class Meta:
        verbose_name = 'Código de Verificación'
        verbose_name_plural = 'Códigos de Verificación'
        ordering = ['-fecha_creacion']

class Conductor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    licencia_conducir = models.CharField(max_length=20)
    telefono = models.CharField(max_length=15)
    vehiculo_asignado = models.CharField(max_length=100, null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.telefono}"
    
    class Meta:
        verbose_name = 'Conductor'
        verbose_name_plural = 'Conductores'
        ordering = ['user__first_name']

class SolicitudServicio(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('pendiente_pago', 'Pendiente de Pago'),
        ('pendiente_confirmacion', 'Pendiente de Confirmación'),
        ('procesando_pago', 'Procesando Pago'),
        ('pago_rechazado', 'Pago Rechazado'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia Bancaria'),
        ('mercadopago_card', 'Tarjeta (Mercado Pago)'),
        ('mercadopago_transfer', 'Transferencia (Mercado Pago)'),
    ]

    TIPO_SERVICIO_CHOICES = [
        ('grua', 'Servicio de Grúa'),
        ('asistencia', 'Asistencia Mecánica'),
        ('bateria', 'Carga de Batería'),
    ]
    
    # Campos básicos
    cliente = models.ForeignKey(User, on_delete=models.CASCADE)
    numero_orden = models.CharField(max_length=20, unique=True, blank=True)
    direccion_origen = models.CharField(max_length=255)
    direccion_destino = models.CharField(max_length=255)
    fecha_servicio = models.DateTimeField()
    descripcion_problema = models.TextField()
    distancia_km = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True)
    estado = models.CharField(
        max_length=25, choices=ESTADO_CHOICES, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Campos de pago actualizados
    metodo_pago = models.CharField(
        max_length=30, choices=METODO_PAGO_CHOICES, null=True, blank=True)
    costo_total = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    # Nuevos campos para guardar tarifas aplicadas
    tarifa_base_aplicada = models.IntegerField(default=30000, help_text="Tarifa base aplicada al momento de la solicitud")
    tarifa_km_aplicada = models.IntegerField(default=1500, help_text="Tarifa por km aplicada al momento de la solicitud")
    pagado = models.BooleanField(default=False)
    
    # Campos de vehículo
    tipo_vehiculo = models.CharField(max_length=50, null=True, blank=True)
    marca_vehiculo = models.CharField(max_length=50, null=True, blank=True)
    modelo_vehiculo = models.CharField(max_length=50, null=True, blank=True)
    placa_vehiculo = models.CharField(max_length=20, null=True, blank=True)
    
    tipo_servicio_categoria = models.CharField(
        max_length=20, 
        choices=TIPO_SERVICIO_CHOICES, 
        default='grua',
        help_text="Tipo de servicio solicitado"
    )

    def save(self, *args, **kwargs):
        if not self.numero_orden:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_suffix = str(uuid.uuid4())[:8].upper()
            self.numero_orden = f"GR{timestamp}{random_suffix}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.numero_orden} - {self.cliente.username}"
    
    class Meta:
        verbose_name = 'Solicitud de Servicio'
        verbose_name_plural = 'Solicitudes de Servicio'
        ordering = ['-fecha_solicitud']

class MercadoPagoPayment(models.Model):
    """Modelo principal para pagos de Mercado Pago"""
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('approved', 'Aprobado'),
        ('authorized', 'Autorizado'),
        ('in_process', 'En proceso'),
        ('rejected', 'Rechazado'),
        ('cancelled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
        ('charged_back', 'Contracargo'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Tarjeta de Crédito'),
        ('debit_card', 'Tarjeta de Débito'),
        ('bank_transfer', 'Transferencia Bancaria'),
        ('cash', 'Efectivo'),
        ('wallet', 'Billetera Digital'),
    ]
    
    # Relaciones
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    solicitud_servicio = models.OneToOneField(
        SolicitudServicio, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='mercadopago_payment'
    )
    
    # IDs de Mercado Pago
    mercadopago_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    preference_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Información del pago
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency_id = models.CharField(max_length=3, default='CLP')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_detail = models.CharField(max_length=100, blank=True)
    
    # Método de pago
    payment_method_type = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_method_id = models.CharField(max_length=30, blank=True)
    installments = models.IntegerField(default=1)
    
    # Información del pagador
    payer_email = models.EmailField()
    payer_identification_type = models.CharField(max_length=10, default='RUN')
    payer_identification_number = models.CharField(max_length=20)
    
    # Metadatos
    external_reference = models.CharField(max_length=100, unique=True)
    idempotency_key = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)
    
    # Información adicional para emergencias
    emergency_contact = models.CharField(max_length=15, blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"MP Pago {self.mercadopago_id} - {self.status} - ${self.transaction_amount}"
    
    class Meta:
        verbose_name = 'Pago Mercado Pago'
        verbose_name_plural = 'Pagos Mercado Pago'
        ordering = ['-created_at']

class MercadoPagoWebhook(models.Model):
    """Log completo de webhooks para auditoría"""
    WEBHOOK_TYPES = [
        ('payment', 'Payment'),
        ('plan', 'Plan'),
        ('subscription', 'Subscription'),
        ('invoice', 'Invoice'),
        ('point_integration_wh', 'Point Integration'),
    ]
    
    webhook_id = models.CharField(max_length=100, unique=True)
    webhook_type = models.CharField(max_length=30, choices=WEBHOOK_TYPES)
    action = models.CharField(max_length=50, blank=True)
    data_id = models.CharField(max_length=100)
    
    # Datos completos del webhook
    raw_data = models.JSONField()
    
    # Estado del procesamiento
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    # Relación con el pago si existe
    payment = models.ForeignKey(
        MercadoPagoPayment, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Webhook {self.webhook_id} - {self.webhook_type} - {self.data_id}"
    
    class Meta:
        verbose_name = 'Webhook Mercado Pago'
        verbose_name_plural = 'Webhooks Mercado Pago'
        ordering = ['-created_at']

class Vehiculo(models.Model):
    TIPO_CHOICES = [
        ('grua_liviana', 'Grúa Liviana'),
        ('grua_pesada', 'Grúa Pesada'),
        ('auxilio_mecanico', 'Auxilio Mecánico'),
    ]
    
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('en_servicio', 'En Servicio'),
        ('mantenimiento', 'En Mantenimiento'),
        ('fuera_servicio', 'Fuera de Servicio'),
    ]
    
    patente = models.CharField(max_length=10, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    año = models.IntegerField()
    capacidad_carga = models.DecimalField(max_digits=6, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible')
    latitud_actual = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud_actual = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    conductor_asignado = models.ForeignKey(Conductor, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.marca} {self.modelo} - {self.patente}"
    
    class Meta:
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
        ordering = ['patente']

class HistorialPago(models.Model):
    """Modelo genérico para historial de pagos (mantiene compatibilidad)"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('anulado', 'Anulado'),
    ]
    
    solicitud = models.ForeignKey(SolicitudServicio, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=30)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    authorization_code = models.CharField(max_length=50, null=True, blank=True)
    fecha_transaccion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    detalles = models.TextField(null=True, blank=True)
    
    # Relación con Mercado Pago
    mercadopago_payment = models.ForeignKey(
        MercadoPagoPayment, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    def __str__(self):
        return f"Pago #{self.id} - {self.solicitud.numero_orden} - ${self.monto}"
    
    class Meta:
        verbose_name = 'Historial de Pago'
        verbose_name_plural = 'Historiales de Pago'
        ordering = ['-fecha_transaccion']

class AsignacionServicio(models.Model):
    ESTADO_CHOICES = [
        ('asignada', 'Asignada'),
        ('en_camino', 'En Camino'),
        ('en_sitio', 'En Sitio'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    solicitud = models.OneToOneField(SolicitudServicio, on_delete=models.CASCADE)
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='asignada')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_inicio_viaje = models.DateTimeField(null=True, blank=True)
    fecha_llegada = models.DateTimeField(null=True, blank=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Asignación #{self.id} - {self.solicitud.numero_orden}"
    
    class Meta:
        verbose_name = 'Asignación de Servicio'
        verbose_name_plural = 'Asignaciones de Servicio'
        ordering = ['-fecha_asignacion']

class TipoMembresia(models.Model):
    """Modelo para los tipos de membresías disponibles"""
    TIPOS_CHOICES = [
        ('basico', 'Básico'),
        ('premium', 'Premium'),
        ('vip', 'VIP'),
    ]
    
    nombre = models.CharField(max_length=50, choices=TIPOS_CHOICES, unique=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    servicios_incluidos = models.IntegerField(help_text="Cantidad de servicios incluidos por mes (0 = ilimitado)")
    descuento_porcentaje = models.IntegerField(default=0, help_text="Porcentaje de descuento en servicios")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Tipo de Membresía"
        verbose_name_plural = "Tipos de Membresías"
    
    def __str__(self):
        return self.get_nombre_display()

class Membresia(models.Model):
    """Modelo para las membresías de los usuarios"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('activa', 'Activa'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
        ('suspendida', 'Suspendida'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='membresias')
    tipo_membresia = models.ForeignKey(TipoMembresia, on_delete=models.CASCADE)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    servicios_utilizados = models.IntegerField(default=0, help_text="Servicios utilizados en el mes actual")
    auto_renovar = models.BooleanField(default=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Membresía"
        verbose_name_plural = "Membresías"
        ordering = ['-fecha_inicio']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.tipo_membresia.nombre} ({self.estado})"
    
    @property
    def servicios_disponibles(self):
        """Calcula servicios disponibles restantes"""
        if self.tipo_membresia.servicios_incluidos == 0:  # Ilimitado
            return "Ilimitado"
        return max(0, self.tipo_membresia.servicios_incluidos - self.servicios_utilizados)
    
    @property
    def esta_activa(self):
        """Verifica si la membresía está activa y no vencida"""
        from django.utils import timezone
        return (self.estado == 'activa' and 
                self.fecha_vencimiento > timezone.now())
    
    def puede_usar_servicio(self):
        """Verifica si puede usar un servicio más"""
        if not self.esta_activa:
            return False
        if self.tipo_membresia.servicios_incluidos == 0:  # Ilimitado
            return True
        return self.servicios_utilizados < self.tipo_membresia.servicios_incluidos

class PagoMembresia(models.Model):
    """Modelo para registrar los pagos de membresías"""
    METODO_PAGO_CHOICES = [
        ('mercadopago_card', 'Tarjeta (Mercado Pago)'),
        ('mercadopago_transfer', 'Transferencia (Mercado Pago)'),
        ('transferencia', 'Transferencia Bancaria'),
        ('efectivo', 'Efectivo'),
    ]
    
    ESTADO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('fallido', 'Fallido'),
        ('reembolsado', 'Reembolsado'),
    ]
    
    membresia = models.ForeignKey(Membresia, on_delete=models.CASCADE, related_name='pagos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=30, choices=METODO_PAGO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_PAGO_CHOICES, default='pendiente')
    
    mercadopago_payment = models.ForeignKey(
        MercadoPagoPayment, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    orden_compra = models.CharField(max_length=50, unique=True)
    numero_transferencia = models.CharField(max_length=100, blank=True, null=True)
    comprobante_transferencia = models.ImageField(upload_to='comprobantes/', blank=True, null=True)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)
    datos_adicionales = models.JSONField(blank=True, null=True, help_text="Datos adicionales del pago")
    
    class Meta:
        verbose_name = "Pago de Membresía"
        verbose_name_plural = "Pagos de Membresías"
        ordering = ['-fecha_pago']
    
    def __str__(self):
        return f"Pago {self.orden_compra} - {self.usuario.username} (${self.monto})"
    
    def generar_orden_compra(self):
        """Genera un número de orden único"""
        import uuid
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"MEM_{timestamp}_{unique_id}"

class DisponibilidadServicio(models.Model):
    """Modelo para controlar la disponibilidad del servicio de grúa"""
    activo = models.BooleanField(default=True, help_text="Si el servicio está disponible o no")
    mensaje_personalizado = models.CharField(
        max_length=200, 
        blank=True, 
        default="Servicio temporalmente no disponible",
        help_text="Mensaje que se muestra cuando el servicio no está disponible"
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        help_text="Usuario que realizó la última actualización"
    )
    
    class Meta:
        verbose_name = "Disponibilidad del Servicio"
        verbose_name_plural = "Disponibilidad del Servicio"
        ordering = ['-fecha_actualizacion']
    
    def __str__(self):
        return f"Servicio {'ACTIVO' if self.activo else 'INACTIVO'} - {self.fecha_actualizacion.strftime('%d/%m/%Y %H:%M')}"
    
    @classmethod
    def esta_disponible(cls):
        """Método para verificar si el servicio está disponible"""
        try:
            disponibilidad = cls.objects.first()
            return disponibilidad.activo if disponibilidad else True
        except:
            return True
    
    @classmethod
    def obtener_mensaje(cls):
        """Obtener mensaje personalizado cuando no está disponible"""
        try:
            disponibilidad = cls.objects.first()
            return disponibilidad.mensaje_personalizado if disponibilidad else "Servicio temporalmente no disponible"
        except:
            return "Servicio temporalmente no disponible"
    
    @classmethod
    def cambiar_estado(cls, activo, mensaje=None, usuario=None):
        """Cambiar el estado de disponibilidad"""
        try:
            disponibilidad, created = cls.objects.get_or_create(defaults={
                'activo': activo,
                'mensaje_personalizado': mensaje or "Servicio temporalmente no disponible",
                'actualizado_por': usuario
            })
            
            if not created:
                disponibilidad.activo = activo
                if mensaje:
                    disponibilidad.mensaje_personalizado = mensaje
                disponibilidad.actualizado_por = usuario
                disponibilidad.save()
            
            return disponibilidad
        except Exception as e:
            print(f"Error cambiando estado de disponibilidad: {e}")
            return None

    def save(self, *args, **kwargs):
        # Solo permitir un registro de disponibilidad
        if not self.pk and DisponibilidadServicio.objects.exists():
            raise ValueError("Solo puede existir un registro de disponibilidad")
        super().save(*args, **kwargs)

class NotificacionAdmin(models.Model):
    """Modelo para notificaciones del administrador"""
    TIPO_CHOICES = [
        ('nueva_solicitud', 'Nueva Solicitud'),
        ('pago_confirmado', 'Pago Confirmado'),
        ('servicio_completado', 'Servicio Completado'),
    ]
    
    titulo = models.CharField(max_length=100)
    mensaje = models.TextField()
    solicitud = models.ForeignKey(SolicitudServicio, on_delete=models.CASCADE, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notificación Admin"
        verbose_name_plural = "Notificaciones Admin"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.titulo} - {'Leída' if self.leida else 'No leída'}"
    
# Agregar estos modelos al final de tu models.py

