from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Usuario
from sensores.models import Dispositivo
from django.db import transaction

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


 
class EmpresaCreaClienteForm(forms.Form):
    """
    Formulario para que una Empresa cree un Cliente, un Usuario,
    y un Dispositivo, todo en un solo paso.
    """
    username = forms.CharField(label="Nombre del Cliente", max_length=150, required=True)
    direccion = forms.CharField(label="Dirección del Cliente", widget=forms.Textarea(attrs={'rows': 3}), required=True)

    nombre_sensor = forms.CharField(label="Nombre del Sensor", max_length=100, required=True)
    id_dispositivo_mqtt = forms.CharField(label="ID del Dispositivo (MQTT)", max_length=100, required=True)
    
    latitud = forms.FloatField(widget=forms.HiddenInput(), required=True)
    longitud = forms.FloatField(widget=forms.HiddenInput(), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ej: juan_perez'})
        self.fields['direccion'].widget.attrs.update({'class': 'form-control'})
        self.fields['nombre_sensor'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ej: Medidor Principal Casa'})
        self.fields['id_dispositivo_mqtt'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ej: sensor_casa_123'})

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya existe.")
        return username

    def clean_id_dispositivo_mqtt(self):
        id_mqtt = self.cleaned_data.get('id_dispositivo_mqtt')
        if Dispositivo.objects.filter(id_dispositivo_mqtt=id_mqtt).exists():
            raise forms.ValidationError("Este ID de dispositivo ya está registrado en el sistema.")
        return id_mqtt

    @transaction.atomic 
    def save(self, empresa_admin):
        """
        Guarda el User, Usuario (perfil) y Dispositivo.
        'empresa_admin' es el objeto 'Usuario' del admin de la empresa logueado.
        """
        data = self.cleaned_data
        
        
        nuevo_user_auth = User.objects.create_user(
            username=data['username'],
            password=User.objects.make_random_password() 
        )
        
        nuevo_user_perfil = nuevo_user_auth.usuario #
        nuevo_user_perfil.rol = Usuario.Rol.CLIENTE
        nuevo_user_perfil.empresa_asociada = empresa_admin 
        nuevo_user_perfil.direccion = data['direccion']
        nuevo_user_perfil.save()
        
        Dispositivo.objects.create(
            usuario=nuevo_user_perfil,
            id_dispositivo_mqtt=data['id_dispositivo_mqtt'],
            nombre=data['nombre_sensor'],
            latitud=data['latitud'],
            longitud=data['longitud']
        )
        
        return nuevo_user_perfil