# grua_app/context_processors.py
from .models import DisponibilidadServicio

def disponibilidad_context(request):
    """
    Context processor para mostrar el estado de disponibilidad del servicio
    en todos los templates de la aplicación
    """
    try:
        # Obtener el estado actual de disponibilidad
        servicio_disponible = DisponibilidadServicio.esta_disponible()
        mensaje_no_disponible = DisponibilidadServicio.obtener_mensaje()
        
        # Obtener información adicional si existe el registro
        disponibilidad_obj = DisponibilidadServicio.objects.first()
        
        context_data = {
            'servicio_disponible': servicio_disponible,
            'mensaje_no_disponible': mensaje_no_disponible,
        }
        
        # Agregar información adicional si existe el objeto
        if disponibilidad_obj:
            context_data.update({
                'fecha_ultima_actualizacion': disponibilidad_obj.fecha_actualizacion,
                'actualizado_por': disponibilidad_obj.actualizado_por,
                'estado_servicio_texto': 'DISPONIBLE' if servicio_disponible else 'NO DISPONIBLE',
                'clase_estado': 'active' if servicio_disponible else 'inactive'
            })
        else:
            # Valores por defecto si no existe el registro
            context_data.update({
                'fecha_ultima_actualizacion': None,
                'actualizado_por': None,
                'estado_servicio_texto': 'DISPONIBLE',
                'clase_estado': 'active'
            })
        
        return context_data
        
    except Exception as e:
        # En caso de error, asumir que el servicio está disponible
        print(f"Error en context processor de disponibilidad: {e}")
        return {
            'servicio_disponible': True,
            'mensaje_no_disponible': 'Servicio temporalmente no disponible',
            'fecha_ultima_actualizacion': None,
            'actualizado_por': None,
            'estado_servicio_texto': 'DISPONIBLE',
            'clase_estado': 'active'
        }