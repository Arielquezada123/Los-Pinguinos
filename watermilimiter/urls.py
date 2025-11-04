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
    path('consumo/', sensores_views.consumo_pagina_view, name='consumo_pagina'),
    path('ingreso/', sensores_views.ingreso_pagina_view, name='ingreso_pagina'),
    path('api/historial/', sensores_views.historial_consumo, name='api_historial'),
]