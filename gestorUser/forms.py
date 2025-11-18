from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Usuario
from sensores.models import Dispositivo
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.utils.text import slugify
from django.utils.crypto import get_random_string


class SignUpForm(UserCreationForm):
    Nombres = forms.CharField(max_length=140, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    Apellidos = forms.CharField(max_length=140, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    telefono = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(label="Contraseña",widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label="Contraseña (confirmación)", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'Nombres', 'Apellidos', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'Nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'Apellidos': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.Nombres = self.cleaned_data.get('Nombres')
        user.Apellidos = self.cleaned_data.get('Apellidos')
        user.email = self.cleaned_data.get('email')
        if commit:
            user.save()
        return user
    
    
class LimiteMensualForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['limite_consumo_mensual']
        widgets = {
            'limite_consumo_mensual': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: 10000 Litros'
            }),
        }
        labels = {
            'limite_consumo_mensual': 'Tu Límite Mensual (en Litros)'
        }



class EmpresaCreaClienteForm(forms.Form):
    """
    Formulario para que la Empresa cree un Cliente.
    Username se genera automáticamente.
    """
    first_name = forms.CharField(label="Nombre(s) del Cliente", max_length=150, required=True)
    last_name = forms.CharField(label="Apellido(s) del Cliente", max_length=150, required=True)
    email = forms.EmailField(label="Email del Cliente", required=True)
    direccion = forms.CharField(label="Dirección del Cliente", widget=forms.Textarea(attrs={'rows': 3}), required=True)
    rut_cliente = forms.CharField(label="RUT del Cliente", max_length=12, required=True)


    nombre_sensor = forms.CharField(label="Nombre del Sensor", max_length=100, required=True)
    id_dispositivo_mqtt = forms.CharField(label="ID del Dispositivo ", max_length=100, required=True)
    latitud = forms.FloatField(label="Latitud", required=True, widget=forms.NumberInput(attrs={'step': 'any'}))
    longitud = forms.FloatField(label="Longitud", required=True, widget=forms.NumberInput(attrs={'step': 'any'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['email'].widget.attrs.update({'class': 'form-control'})
        self.fields['direccion'].widget.attrs.update({'class': 'form-control'})
        self.fields['rut_cliente'].widget.attrs.update({'class': 'form-control'})
        self.fields['nombre_sensor'].widget.attrs.update({'class': 'form-control'})
        self.fields['id_dispositivo_mqtt'].widget.attrs.update({'class': 'form-control'})
        self.fields['latitud'].widget.attrs.update({'class': 'form-control', 'id': 'lat-input'})
        self.fields['longitud'].widget.attrs.update({'class': 'form-control', 'id': 'lon-input'})

    def clean_id_dispositivo_mqtt(self):
        id_mqtt = self.cleaned_data.get('id_dispositivo_mqtt')
        if Dispositivo.objects.filter(id_dispositivo_mqtt=id_mqtt).exists():
            raise forms.ValidationError("Este ID de dispositivo ya está registrado en el sistema.")
        return id_mqtt 

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email ya está en uso.")
        return email

    @transaction.atomic
    def save(self, request, organizacion_actual):
        data = self.cleaned_data
        
        base_username = slugify(data['first_name'][0] + data['last_name']).replace('-', '')
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        # --- CORRECCIÓN: Generar contraseña aleatoria ---
        nuevo_password = get_random_string(length=12)

        nuevo_user_auth = User.objects.create_user(
            username=username, 
            email=data['email'],
            password=nuevo_password,
            first_name=data['first_name'].upper(), # --- CORRECCIÓN: Convertir a mayúsculas
            last_name=data['last_name'].upper()    # --- CORRECCIÓN: Convertir a mayúsculas
        )

        # --- RESTAURADO: Configuración del perfil (Faltaba en tu código) ---
        nuevo_user_perfil = nuevo_user_auth.usuario
        nuevo_user_perfil.organizacion_admin = organizacion_actual
        nuevo_user_perfil.direccion = data['direccion']
        nuevo_user_perfil.rut_cliente = data['rut_cliente']
        nuevo_user_perfil.save()
        # ---------------------------------------------------------------

        Dispositivo.objects.create(
            usuario=nuevo_user_perfil,
            id_dispositivo_mqtt=data['id_dispositivo_mqtt'],
            nombre=data['nombre_sensor'],
            latitud=data['latitud'],
            longitud=data['longitud']
        )

        self.enviar_email_bienvenida(request, nuevo_user_auth)
        
        return nuevo_user_perfil

    def enviar_email_bienvenida(self, request, user):
        current_site = get_current_site(request)
        subject = '¡Bienvenido a MiAgua! Activa tu cuenta.'
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        

        empresa_logueada = request.user
        nombre_empresa = empresa_logueada.get_full_name()
        if not nombre_empresa:
            nombre_empresa = empresa_logueada.username

        message = render_to_string('registration/email_bienvenida.html', {
            'user': user,
            'protocol': request.scheme,
            'domain': current_site.domain,
            'uid': uid,
            'token': token,
            'empresa_nombre': nombre_empresa
        })
        
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])