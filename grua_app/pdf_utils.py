# grua_app/pdf_utils.py
# Sistema de generación de PDF

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa
import io


def generar_pdf_solicitud(solicitud):
    """Genera PDF de la solicitud de servicio"""
    try:
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

        # Contexto para el template
        context = {
            'solicitud': solicitud,
            'tarifa_base': tarifa_base,
            'tarifa_por_km': tarifa_por_km,
            'costo_km': costo_km,
            'total': total,
            'fecha_generacion': timezone.now(),
        }

        # Renderizar template HTML
        html_string = render_to_string(
            'grua_app/pdf/solicitud_pdf.html', context)

        # Crear archivo PDF
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(
            html_string.encode("UTF-8")), result)

        if not pdf.err:
            # Crear respuesta HTTP
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="solicitud_{solicitud.numero_orden}.pdf"'
            response.write(result.getvalue())
            return response

        return None

    except Exception as e:
        print(f"❌ Error generando PDF: {e}")
        return None


def generar_pdf_comprobante(solicitud):
    """Genera PDF del comprobante de pago"""
    try:
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

        # Contexto para el template
        context = {
            'solicitud': solicitud,
            'tarifa_base': tarifa_base,
            'tarifa_por_km': tarifa_por_km,
            'costo_km': costo_km,
            'total': total,
            'fecha_generacion': timezone.now(),
            'es_comprobante': True,
        }

        # Renderizar template HTML
        html_string = render_to_string(
            'grua_app/pdf/comprobante_pdf.html', context)

        # Crear archivo PDF
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(
            html_string.encode("UTF-8")), result)

        if not pdf.err:
            # Crear respuesta HTTP
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="comprobante_{solicitud.numero_orden}.pdf"'
            response.write(result.getvalue())
            return response

        return None

    except Exception as e:
        print(f"❌ Error generando comprobante PDF: {e}")
        return None
