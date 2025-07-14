from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=15)
    rut = models.CharField(max_length=12, unique=True)
    direccion = models.CharField(max_length=255)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    def str(self):
        return f"{self.user.username} - {self.telefono}"
    class Meta:
        ordering = ['-fecha_registro']
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
    def save(self, args, **kwargs):
        if not self.numero_orden:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_suffix = str(uuid.uuid4())[:8].upper()
            self.numero_orden = f"GR{timestamp}{random_suffix}"
        super().save(args, kwargs)
    def str(self):
        return f"{self.numero_orden} - {self.cliente.username}"
    class Meta:
        ordering = ['-fecha_solicitud']
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
        ordering = ['-fecha_creacion']
