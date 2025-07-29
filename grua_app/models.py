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
    ]
    
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('webpay', 'WebPay'),
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
        max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Campos de pago
    metodo_pago = models.CharField(
        max_length=20, choices=METODO_PAGO_CHOICES, null=True, blank=True)
    costo_total = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    pagado = models.BooleanField(default=False)
    
    # Campos WebPay
    webpay_token = models.CharField(max_length=100, null=True, blank=True)
    webpay_buy_order = models.CharField(max_length=50, null=True, blank=True)
    webpay_authorization_code = models.CharField(
        max_length=50, null=True, blank=True)
    
    # NUEVOS CAMPOS DE VEHÍCULO
    tipo_vehiculo = models.CharField(max_length=50, null=True, blank=True)
    marca_vehiculo = models.CharField(max_length=50, null=True, blank=True)
    modelo_vehiculo = models.CharField(max_length=50, null=True, blank=True)
    placa_vehiculo = models.CharField(max_length=20, null=True, blank=True)
    
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
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('anulado', 'Anulado'),
    ]
    
    solicitud = models.ForeignKey(SolicitudServicio, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    authorization_code = models.CharField(max_length=50, null=True, blank=True)
    fecha_transaccion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    detalles = models.TextField(null=True, blank=True)
    
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

# ===== MODELOS DE MEMBRESÍAS =====

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
        ('webpay', 'WebPay'),
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
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_PAGO_CHOICES, default='pendiente')
    
    # Campos para WebPay
    token_webpay = models.CharField(max_length=100, blank=True, null=True)
    orden_compra = models.CharField(max_length=50, unique=True)
    
    # Campos para transferencia
    numero_transferencia = models.CharField(max_length=100, blank=True, null=True)
    comprobante_transferencia = models.ImageField(upload_to='comprobantes/', blank=True, null=True)
    
    fecha_pago = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    
    # Campos adicionales
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