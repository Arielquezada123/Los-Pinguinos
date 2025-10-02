from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView
from gestorUser.views import signUp, postlogin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name="index.html"), name='index'),
    
    # Incluyendo las URLs de autenticación de Django para login/logout
    path('cuentas/', include("django.contrib.auth.urls")),  # Esto incluye login, logout y demás
    
    # Si tienes una vista personalizada para el registro
    path('signUp/', signUp, name="signUp"),

    # Ruta post-login si tienes una vista personalizada
    path('interfaz/', postlogin, name="post_login"),
]
