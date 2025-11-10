from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView
from gestorUser.views import *
from sensores import views as sensores_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name="index.html"), name='index'),
    
    path('cuentas/', include("django.contrib.auth.urls")),
    
    path('signUp/', signUp, name="signUp"),

    path('interfaz/', postlogin, name="post_login"),
    
    path('historial/', sensores_views.historial_pagina_view, name='historial_pagina'),
    path('mapa/', sensores_views.mapa_pagina_view, name='mapa_pagina'),
    path('api/popup/<str:id_mqtt>/', sensores_views.popup_lectura_latest, name='api_popup_data'),
    path('consumo/', sensores_views.consumo_pagina_view, name='consumo_pagina'),
    

    # CRUD SENSORES
     path('ingreso/', sensores_views.ingreso_pagina_view, name='ingreso_pagina'),
    path('sensores/', sensores_views.lista_sensores_view, name='lista_sensores'),
    path('sensores/editar/<str:id_mqtt>/', sensores_views.editar_sensor_view, name='editar_sensor'),     
    path('sensores/eliminar/<str:id_mqtt>/', sensores_views.eliminar_sensor_view, name='eliminar_sensor'), 
    ########################################################################################################
    path('api/inicio_data/', sensores_views.api_inicio_data, name='api_inicio_data'),
    path('api/historial/', sensores_views.historial_consumo, name='api_historial'),
    path('api/historial/grafico/', sensores_views.api_historial_agregado, name='api_historial_grafico'),
]