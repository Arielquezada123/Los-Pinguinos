from .models import Alerta
from gestorUser.models import Usuario

def alertas_processor(request):
    """
    Inyecta las alertas no leídas en todas las plantillas.
    """
    if request.user.is_authenticated:
        try:
            # Obtenemos el perfil Usuario asociado al User logueado
            usuario_perfil = request.user.usuario 
            
            # Filtramos las no leídas
            alertas_no_leidas = Alerta.objects.filter(
                usuario=usuario_perfil, 
                leida=False
            ).order_by('-timestamp')
            
            return {
                'alertas_no_leidas': alertas_no_leidas,
                'cantidad_alertas': alertas_no_leidas.count()
            }
        except Usuario.DoesNotExist:
            return {}
        except Exception:
            return {}
            
    return {}