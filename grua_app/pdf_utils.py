from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
import io

# DEBUG: Verificar que el archivo se está cargando
print("🔍 DEBUG: pdf_utils.py se está cargando...")

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.platypus.flowables import HRFlowable
    print("✅ reportlab importado correctamente")
    PDF_UTILS_AVAILABLE = True
except ImportError as e:
    print(f"❌ DEBUG: Error importando reportlab en pdf_utils.py: {e}")
    PDF_UTILS_AVAILABLE = False


def generar_pdf_solicitud(solicitud):
    """
    Genera un PDF con los detalles de la solicitud usando ReportLab
    """
    if not PDF_UTILS_AVAILABLE:
        return None
    
    try:
        # Crear buffer
        buffer = io.BytesIO()
        
        # Crear documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a365d'),
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#1a365d'),
            backColor=colors.HexColor('#f8fafc'),
            borderPadding=8
        )
        
        normal_style = styles['Normal']
        
        # Contenido del PDF
        story = []
        
        # Título
        story.append(Paragraph("🚛 GRÚA STYLE", title_style))
        story.append(Paragraph("Solicitud de Servicio", heading_style))
        story.append(Spacer(1, 20))
        
        # Información de la solicitud
        story.append(Paragraph("DETALLES DE LA SOLICITUD", heading_style))
        
        # Crear tabla con información básica (campos que seguramente existen)
        data = [
            ['ID Solicitud:', f'#{solicitud.id}'],
            ['Cliente:', f'{solicitud.cliente.first_name} {solicitud.cliente.last_name}'],
            ['Email:', solicitud.cliente.email],
            ['Fecha Solicitud:', solicitud.fecha_solicitud.strftime('%d/%m/%Y %H:%M')],
            ['Estado:', solicitud.get_estado_display()],
        ]
        
        # Agregar campos opcionales solo si existen
        try:
            if hasattr(solicitud.cliente, 'cliente') and hasattr(solicitud.cliente.cliente, 'telefono'):
                data.append(['Teléfono:', solicitud.cliente.cliente.telefono])
        except:
            pass
            
        try:
            if hasattr(solicitud, 'ubicacion_origen') and solicitud.ubicacion_origen:
                data.append(['Ubicación Origen:', solicitud.ubicacion_origen])
        except:
            pass
            
        try:
            if hasattr(solicitud, 'ubicacion_destino') and solicitud.ubicacion_destino:
                data.append(['Ubicación Destino:', solicitud.ubicacion_destino])
        except:
            pass
            
        try:
            if hasattr(solicitud, 'tipo_servicio') and solicitud.tipo_servicio:
                data.append(['Tipo Servicio:', solicitud.tipo_servicio])
        except:
            pass
            
        try:
            if hasattr(solicitud, 'descripcion') and solicitud.descripcion:
                data.append(['Descripción:', solicitud.descripcion])
        except:
            pass
            
        try:
            if hasattr(solicitud, 'costo_estimado') and solicitud.costo_estimado:
                data.append(['Costo Estimado:', f'${solicitud.costo_estimado:,.0f} CLP'])
        except:
            pass
        
        # Estilo de tabla
        table = Table(data, colWidths=[4*cm, 12*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Información adicional
        story.append(Paragraph("INFORMACIÓN DEL SERVICIO", heading_style))
        story.append(Paragraph(f"Esta solicitud fue generada el {timezone.now().strftime('%d/%m/%Y a las %H:%M')}.", normal_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Para cualquier consulta, contáctenos:", normal_style))
        story.append(Paragraph("📧 Email: contacto@gruastyle.cl", normal_style))
        story.append(Paragraph("📱 Teléfono: +56 9 1234 5678", normal_style))
        story.append(Paragraph("🌐 Web: www.gruastyle.cl", normal_style))
        
        # Línea separadora
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a365d')))
        story.append(Spacer(1, 12))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=1
        )
        story.append(Paragraph("Grúa Style - Servicio de Grúas Profesional", footer_style))
        
        # Construir PDF
        doc.build(story)
        
        # Obtener PDF
        buffer.seek(0)
        
        # Crear respuesta HTTP
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="solicitud_{solicitud.id}.pdf"'
        
        return response
        
    except Exception as e:
        print(f"❌ Error generando PDF de solicitud: {e}")
        import traceback
        traceback.print_exc()
        return None


def generar_pdf_comprobante(solicitud):
    """
    Genera un PDF del comprobante de pago usando ReportLab
    """
    if not PDF_UTILS_AVAILABLE:
        return None
    
    try:
        # Crear buffer
        buffer = io.BytesIO()
        
        # Crear documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, 
                              topMargin=72, bottomMargin=18)
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            textColor=colors.HexColor('#1a365d'),
            alignment=1  # Center
        )
        
        comprobante_style = ParagraphStyle(
            'ComprobanteTitle',
            parent=styles['Heading2'],
            fontSize=20,
            spaceAfter=20,
            textColor=colors.HexColor('#1a365d'),
            alignment=1
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor=colors.HexColor('#1a365d'),
            backColor=colors.HexColor('#f8fafc'),
            borderPadding=8
        )
        
        normal_style = styles['Normal']
        
        # Contenido del PDF
        story = []
        
        # Título
        story.append(Paragraph("🚛 GRÚA STYLE", title_style))
        story.append(Paragraph("COMPROBANTE DE SERVICIO", comprobante_style))
        story.append(Spacer(1, 30))
        
        # Información del comprobante
        story.append(Paragraph("DATOS DEL SERVICIO", heading_style))
        
        # Crear tabla con información del comprobante (campos básicos)
        data = [
            ['Comprobante N°:', f'COMP-{solicitud.id:04d}'],
            ['Cliente:', f'{solicitud.cliente.first_name} {solicitud.cliente.last_name}'],
            ['Email:', solicitud.cliente.email],
            ['Fecha Servicio:', solicitud.fecha_solicitud.strftime('%d/%m/%Y')],
            ['Hora Servicio:', solicitud.fecha_solicitud.strftime('%H:%M')],
            ['Estado:', solicitud.get_estado_display()],
        ]
        
        # Agregar campos opcionales
        try:
            if hasattr(solicitud.cliente, 'cliente') and hasattr(solicitud.cliente.cliente, 'rut'):
                data.append(['RUT Cliente:', solicitud.cliente.cliente.rut])
        except:
            pass
            
        try:
            if hasattr(solicitud, 'ubicacion_origen') and solicitud.ubicacion_origen:
                data.append(['Origen:', solicitud.ubicacion_origen])
        except:
            pass
            
        try:
            if hasattr(solicitud, 'ubicacion_destino') and solicitud.ubicacion_destino:
                data.append(['Destino:', solicitud.ubicacion_destino])
        except:
            pass
            
        try:
            if hasattr(solicitud, 'tipo_servicio') and solicitud.tipo_servicio:
                data.append(['Servicio:', solicitud.tipo_servicio])
        except:
            pass
        
        # Estilo de tabla
        table = Table(data, colWidths=[5*cm, 11*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#1a365d')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Sección de total (si existe costo estimado)
        try:
            if hasattr(solicitud, 'costo_estimado') and solicitud.costo_estimado:
                story.append(Paragraph("RESUMEN DE COSTOS", heading_style))
                
                total_data = [
                    ['Servicio de Grúa:', f'${solicitud.costo_estimado:,.0f}'],
                    ['Total a Pagar:', f'${solicitud.costo_estimado:,.0f} CLP']
                ]
                
                total_table = Table(total_data, colWidths=[10*cm, 6*cm])
                total_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a365d')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#1a365d')),
                    ('TEXTCOLOR', (0, 1), (-1, 1), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('FONTSIZE', (0, 1), (-1, 1), 16),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
                ]))
                
                story.append(total_table)
                story.append(Spacer(1, 30))
        except:
            pass
        
        # Información adicional
        story.append(Paragraph("INFORMACIÓN ADICIONAL", heading_style))
        story.append(Paragraph(f"Comprobante generado el {timezone.now().strftime('%d/%m/%Y a las %H:%M')}.", normal_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Este documento es válido como comprobante de servicio.", normal_style))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Contacto:", normal_style))
        story.append(Paragraph("📧 contacto@gruastyle.cl | 📱 +56 9 1234 5678", normal_style))
        
        # Línea separadora
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1a365d')))
        story.append(Spacer(1, 12))
        
        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=1
        )
        story.append(Paragraph("Grúa Style - Servicio Profesional de Grúas y Asistencia Vehicular", footer_style))
        
        # Construir PDF
        doc.build(story)
        
        # Obtener PDF
        buffer.seek(0)
        
        # Crear respuesta HTTP
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="comprobante_{solicitud.id}.pdf"'
        
        return response
        
    except Exception as e:
        print(f"❌ Error generando PDF de comprobante: {e}")
        import traceback
        traceback.print_exc()
        return None