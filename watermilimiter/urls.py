from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import TemplateView
from gestorUser.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name="index.html"), name='index'),
    
    path('cuentas/', include("django.contrib.auth.urls")),  # Esto incluye login, logout y demás
    
    path('signUp/', signUp, name="signUp"),

    path('interfaz/', postlogin, name="post_login"),
]
