# grua_app/views/payment_views.py
import json
import uuid
import mercadopago
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from ..models import SolicitudServicio, MercadoPagoPayment, MercadoPagoWebhook, HistorialPago

# Configurar logging
logger = logging.getLogger(__name__)

class PaymentSelectionView(View):
    """Vista para seleccionar método de pago"""
    
    @method_decorator(login_required)
    def get(self, request, solicitud_id):
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Verificar si ya existe un pago pendiente o aprobado
        existing_payment = MercadoPagoPayment.objects.filter(
            solicitud_servicio=solicitud,
            status__in=['pending', 'approved', 'authorized']
        ).first()
        
        if existing_payment:
            messages.info(request, f'Ya existe un pago {existing_payment.status} para esta solicitud.')
            return redirect('dashboard')
        
        context = {
            'solicitud': solicitud,
            'precio_total': solicitud.costo_total or 25000,  # Precio por defecto
            'bank_info': settings.BANK_TRANSFER_INFO,
            'currency': 'CLP'
        }
        return render(request, 'grua_app/payment_selection.html', context)

class MercadoPagoCheckoutView(View):
    """Vista para checkout con tarjeta usando Mercado Pago"""
    
    def __init__(self):
        self.sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    
    @method_decorator(login_required)
    def get(self, request, solicitud_id):
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Verificar si ya existe un pago pendiente o aprobado
        existing_payment = MercadoPagoPayment.objects.filter(
            solicitud_servicio=solicitud,
            status__in=['pending', 'approved', 'authorized']
        ).first()
        
        if existing_payment:
            messages.warning(request, 'Ya existe un pago en proceso para esta solicitud.')
            return redirect('payment_selection', solicitud_id=solicitud.id)
        
        context = {
            'solicitud': solicitud,
            'public_key': settings.MERCADOPAGO_PUBLIC_KEY,
            'amount': float(solicitud.costo_total or 25000),
            'currency': 'CLP',
            'max_installments': settings.PAYMENT_CONFIG.get('max_installments', 6)
        }
        return render(request, 'grua_app/mercadopago_checkout.html', context)
    
    @method_decorator(csrf_exempt)
    def post(self, request, solicitud_id):
        try:
            solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
            data = json.loads(request.body)
            
            logger.info(f"Procesando pago MP para solicitud {solicitud.id}")
            
            # Generar referencias únicas
            idempotency_key = str(uuid.uuid4())
            external_reference = f"grua_{solicitud.id}_{int(timezone.now().timestamp())}"
            
            # Preparar datos del pago
            payment_data = {
                "transaction_amount": float(solicitud.costo_total or 25000),
                "token": data["token"],
                "description": f"Servicio de grúa - Orden #{solicitud.numero_orden}",
                "payment_method_id": data["payment_method_id"],
                "installments": int(data.get("installments", 1)),
                "payer": {
                    "email": data["payer"]["email"],
                    "identification": {
                        "type": data["payer"]["identification"]["type"],
                        "number": data["payer"]["identification"]["number"]
                    }
                },
                "external_reference": external_reference,
                "notification_url": f"{settings.BASE_HOST}/api/mercadopago/webhook/",
                "statement_descriptor": "GRUA STYLE",  # Aparece en el resumen de tarjeta
            }
            
            # Headers con idempotencia
            request_options = mercadopago.config.RequestOptions()
            request_options.custom_headers = {
                'x-idempotency-key': idempotency_key
            }
            
            # Crear pago en Mercado Pago
            result = self.sdk.payment().create(payment_data, request_options)
            
            logger.info(f"Respuesta MP: Status {result['status']}")
            
            if result["status"] == 201:
                payment_response = result["response"]
                
                # Crear registro en BD
                mp_payment = MercadoPagoPayment.objects.create(
                    user=request.user,
                    solicitud_servicio=solicitud,
                    mercadopago_id=payment_response["id"],
                    transaction_amount=payment_response["transaction_amount"],
                    currency_id="CLP",
                    status=payment_response["status"],
                    status_detail=payment_response["status_detail"],
                    payment_method_type='credit_card' if 'credit' in data["payment_method_id"] else 'debit_card',
                    payment_method_id=payment_response["payment_method_id"],
                    installments=payment_response["installments"],
                    payer_email=payment_response["payer"]["email"],
                    payer_identification_type=payment_response["payer"]["identification"]["type"],
                    payer_identification_number=payment_response["payer"]["identification"]["number"],
                    external_reference=external_reference,
                    idempotency_key=idempotency_key,
                    description=payment_data["description"]
                )
                
                # Crear registro en historial de pagos
                HistorialPago.objects.create(
                    solicitud=solicitud,
                    monto=payment_response["transaction_amount"],
                    metodo_pago='mercadopago_card',
                    estado='pendiente' if payment_response["status"] == 'pending' else 'aprobado',
                    transaction_id=payment_response["id"],
                    mercadopago_payment=mp_payment,
                    detalles=f"Pago con {payment_response['payment_method_id']} - {payment_response['installments']} cuotas"
                )
                
                # Actualizar solicitud
                solicitud.metodo_pago = 'mercadopago_card'
                if payment_response["status"] == 'approved':
                    solicitud.estado = 'confirmada'
                    solicitud.pagado = True
                else:
                    solicitud.estado = 'pendiente_confirmacion'
                solicitud.save()
                
                logger.info(f"Pago creado: MP ID {payment_response['id']}, Status: {payment_response['status']}")
                
                return JsonResponse({
                    "status": "success",
                    "payment_id": payment_response["id"],
                    "payment_status": payment_response["status"],
                    "message": self._get_status_message(payment_response["status"]),
                    "redirect_url": reverse('payment_result', kwargs={'payment_id': mp_payment.id})
                })
            else:
                logger.error(f"Error MP: {result}")
                return JsonResponse({
                    "status": "error",
                    "message": "Error procesando el pago. Intenta nuevamente."
                }, status=400)
                
        except Exception as e:
            logger.error(f"Error procesando pago: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": "Error del sistema. Contacta soporte."
            }, status=500)
    
    def _get_status_message(self, status):
        """Obtiene mensaje según el estado del pago"""
        messages = {
            'approved': '¡Pago aprobado! Tu grúa está confirmada.',
            'pending': 'Pago en verificación. Te confirmaremos pronto.',
            'authorized': 'Pago autorizado. Procesando...',
            'in_process': 'Pago en proceso. Por favor espera.',
            'rejected': 'Pago rechazado. Intenta con otro método.',
        }
        return messages.get(status, 'Estado de pago desconocido.')

class BankTransferView(View):
    """Vista para mostrar datos de transferencia bancaria"""
    
    @method_decorator(login_required)
    def get(self, request, solicitud_id):
        solicitud = get_object_or_404(SolicitudServicio, id=solicitud_id, cliente=request.user)
        
        # Generar referencia única para transferencia
        external_reference = f"transfer_grua_{solicitud.id}_{int(timezone.now().timestamp())}"
        
        # Crear registro de pago pendiente por transferencia
        mp_payment = MercadoPagoPayment.objects.create(
            user=request.user,
            solicitud_servicio=solicitud,
            transaction_amount=solicitud.costo_total or 25000,
            currency_id="CLP",
            status='pending',
            payment_method_type='bank_transfer',
            payer_email=request.user.email,
            payer_identification_type='RUN',
            payer_identification_number=getattr(request.user, 'cliente', {}).get('rut', '') or '11111111-1',
            external_reference=external_reference,
            idempotency_key=str(uuid.uuid4()),
            description=f"Transferencia - Orden #{solicitud.numero_orden}"
        )
        
        # Crear historial de pago
        HistorialPago.objects.create(
            solicitud=solicitud,
            monto=mp_payment.transaction_amount,
            metodo_pago='transferencia',
            estado='pendiente',
            mercadopago_payment=mp_payment,
            detalles="Pago pendiente por transferencia bancaria"
        )
        
        # Actualizar solicitud
        solicitud.metodo_pago = 'transferencia'
        solicitud.estado = 'pendiente_confirmacion'
        solicitud.save()
        
        context = {
            'solicitud': solicitud,
            'payment': mp_payment,
            'bank_info': settings.BANK_TRANSFER_INFO,
            'reference_number': external_reference,
            'amount': mp_payment.transaction_amount
        }
        return render(request, 'grua_app/bank_transfer.html', context)

class PaymentResultView(View):
    """Vista para mostrar resultado del pago"""
    
    @method_decorator(login_required)
    def get(self, request, payment_id):
        payment = get_object_or_404(MercadoPagoPayment, id=payment_id, user=request.user)
        
        context = {
            'payment': payment,
            'solicitud': payment.solicitud_servicio,
            'success': payment.status in ['approved', 'authorized'],
            'pending': payment.status in ['pending', 'in_process'],
            'failed': payment.status in ['rejected', 'cancelled']
        }
        return render(request, 'grua_app/payment_result.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class MercadoPagoWebhookView(View):
    """Vista para manejar webhooks de Mercado Pago"""
    
    def post(self, request):
        try:
            webhook_data = json.loads(request.body)
            webhook_id = webhook_data.get('id')
            webhook_type = webhook_data.get('type')
            action = webhook_data.get('action', '')
            data_id = webhook_data.get('data', {}).get('id')
            
            logger.info(f"Webhook recibido: {webhook_type} - {data_id}")
            
            # Validaciones básicas
            if not all([webhook_id, webhook_type, data_id]):
                logger.warning("Webhook incompleto")
                return HttpResponse(status=400)
            
            if webhook_type != 'payment':
                logger.info(f"Webhook no es de payment: {webhook_type}")
                return HttpResponse(status=200)
            
            # Verificar idempotencia
            webhook_log, created = MercadoPagoWebhook.objects.get_or_create(
                webhook_id=webhook_id,
                defaults={
                    'webhook_type': webhook_type,
                    'action': action,
                    'data_id': data_id,
                    'raw_data': webhook_data
                }
            )
            
            if not created and webhook_log.processed:
                logger.info(f"Webhook ya procesado: {webhook_id}")
                return HttpResponse(status=200)
            
            # Procesar webhook
            self._process_webhook(webhook_log)
            
            return HttpResponse(status=200)
            
        except Exception as e:
            logger.error(f"Error procesando webhook: {str(e)}")
            return HttpResponse(status=500)
    
    def _process_webhook(self, webhook_log):
        """Procesa el webhook y actualiza el estado del pago"""
        try:
            payment_id = webhook_log.data_id
            
            # Obtener datos del pago desde Mercado Pago
            sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            payment_data = sdk.payment().get(payment_id)
            
            if payment_data["status"] != 200:
                raise Exception(f"Error obteniendo pago {payment_id}: {payment_data}")
            
            payment_info = payment_data["response"]
            logger.info(f"Procesando webhook para pago {payment_id}, status: {payment_info['status']}")
            
            # Buscar el pago en nuestra BD
            try:
                mp_payment = MercadoPagoPayment.objects.get(mercadopago_id=payment_id)
                old_status = mp_payment.status
                
                # Actualizar estado del pago
                mp_payment.status = payment_info["status"]
                mp_payment.status_detail = payment_info.get("status_detail", "")
                
                if payment_info["status"] == "approved" and not mp_payment.approved_at:
                    mp_payment.approved_at = timezone.now()
                
                mp_payment.save()
                
                # Actualizar solicitud de servicio
                if mp_payment.solicitud_servicio:
                    solicitud = mp_payment.solicitud_servicio
                    
                    if payment_info["status"] == "approved":
                        solicitud.estado = 'confirmada'
                        solicitud.pagado = True
                        logger.info(f"Solicitud {solicitud.id} confirmada por pago aprobado")
                        
                    elif payment_info["status"] == "rejected":
                        solicitud.estado = 'pago_rechazado'
                        logger.info(f"Solicitud {solicitud.id} marcada como pago rechazado")
                        
                    solicitud.save()
                
                # Actualizar historial de pago
                try:
                    historial = HistorialPago.objects.get(mercadopago_payment=mp_payment)
                    historial.estado = 'aprobado' if payment_info["status"] == 'approved' else 'pendiente'
                    historial.detalles = f"Actualizado vía webhook: {payment_info['status']} - {payment_info.get('status_detail', '')}"
                    historial.save()
                except HistorialPago.DoesNotExist:
                    pass
                
                # Asociar webhook con payment
                webhook_log.payment = mp_payment
                
                logger.info(f"Pago {payment_id} actualizado: {old_status} → {mp_payment.status}")
                
            except MercadoPagoPayment.DoesNotExist:
                logger.warning(f"Pago {payment_id} no encontrado en BD")
            
            # Marcar webhook como procesado
            webhook_log.processed = True
            webhook_log.processed_at = timezone.now()
            webhook_log.save()
            
        except Exception as e:
            # Log del error y marcar reintento
            webhook_log.error_message = str(e)
            webhook_log.retry_count += 1
            webhook_log.save()
            
            logger.error(f"Error procesando webhook {webhook_log.webhook_id}: {str(e)}")
            raise

class PaymentStatusView(View):
    """Vista para consultar estado de pago vía AJAX"""
    
    @method_decorator(login_required)
    def get(self, request, payment_id):
        try:
            payment = get_object_or_404(MercadoPagoPayment, id=payment_id, user=request.user)
            
            return JsonResponse({
                'status': payment.status,
                'status_detail': payment.status_detail,
                'amount': float(payment.transaction_amount),
                'payment_method': payment.payment_method_id,
                'created_at': payment.created_at.isoformat(),
                'solicitud_estado': payment.solicitud_servicio.estado if payment.solicitud_servicio else None
            })
        except Exception as e:
            return JsonResponse({
                'error': 'Payment not found'
            }, status=404)