from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView
from gestorUser.views import signUp, postlogin, limite_pagina 
from sensores import views as sensores_views
from reportes.views import reportes_pagina
from reportes import views as reportes_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name="index.html"), name='index'),
    
    path('cuentas/', include("django.contrib.auth.urls")),
    
    path('signUp/', signUp, name="signUp"),

    path('interfaz/', postlogin, name="post_login"),
    path('empresa/inicio/', sensores_views.empresa_dashboard_view, name='empresa_inicio'),


    path('historial/', sensores_views.historial_pagina_view, name='historial_pagina'),
    path('mapa/', sensores_views.mapa_pagina_view, name='mapa_pagina'),
    path('api/popup/<str:id_mqtt>/', sensores_views.popup_lectura_latest, name='api_popup_data'),
    path('consumo/', sensores_views.consumo_pagina_view, name='consumo_pagina'),

    
    path('dashboard/reportes/', reportes_views.reportes_pagina, name='reportes_pagina'),

    path('empresa/crear_cliente/', sensores_views.empresa_crear_cliente_view, name='empresa_crear_cliente'),
    path('empresa/clientes/', sensores_views.empresa_lista_clientes_view, name='empresa_lista_clientes'),
    path('empresa/cliente/<int:cliente_id>/', sensores_views.empresa_ver_cliente_view, name='empresa_ver_cliente'),
    path('empresa/facturacion/', reportes_views.facturacion_view, name='empresa_facturacion'),
    path('empresa/mapa/', sensores_views.empresa_mapa_view, name='empresa_mapa_general'),
    path('empresa/configuracion_tarifas/', reportes_views.configuracion_tarifas_view, name='empresa_configuracion_tarifas'),
    path('empresa/facturacion/<int:ano>/<int:mes>/', reportes_views.facturacion_detalle_mes_view, name='empresa_facturacion_detalle'),
    path('empresa/boleta/<int:boleta_id>/', reportes_views.ver_boleta_view, name='empresa_boleta_detalle'),
    path('empresa/boleta/<int:boleta_id>/pagar/', reportes_views.registrar_pago_view, name='empresa_registrar_pago'),
    
    # CRUD SENSORES
    path('ingreso/', sensores_views.ingreso_pagina_view, name='ingreso_pagina'),
    path('sensores/', sensores_views.lista_sensores_view, name='lista_sensores'),
    path('sensores/editar/<str:id_mqtt>/', sensores_views.editar_sensor_view, name='editar_sensor'),    
    path('sensores/eliminar/<str:id_mqtt>/', sensores_views.eliminar_sensor_view, name='eliminar_sensor'), 
    ########################################################################################################

    path('api/inicio_data/', sensores_views.api_inicio_data, name='api_inicio_data'),
    path('api/historial/', sensores_views.historial_consumo, name='api_historial'),
    path('dashboard/limite/', limite_pagina, name='limite_pagina'),
    path('mis-boletas/', reportes_views.cliente_lista_boletas_view, name='cliente_mis_boletas'),

    path('reglas/', reportes_views.reglas_lista_view, name='reglas_lista'),
    path('reglas/nueva/', reportes_views.reglas_crear_view, name='reglas_crear'),
    path('reglas/editar/<int:regla_id>/', reportes_views.reglas_editar_view, name='reglas_editar'),
    path('reglas/eliminar/<int:regla_id>/', reportes_views.reglas_eliminar_view, name='reglas_eliminar'),
    path('api/historial/grafico/', sensores_views.api_historial_agregado, name='api_historial_grafico'),
    path('boleta/<int:boleta_id>/generar-enviar/', reportes_views.generar_y_enviar_boleta, name='generar_enviar_boleta'),

    
    

   
]
