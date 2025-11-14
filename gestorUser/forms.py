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

    username = forms.CharField(label="Nombre completo del Cliente", max_length=150, required=True)
    direccion = forms.CharField(label="Dirección del Cliente", widget=forms.Textarea(attrs={'rows': 3}), required=True)
    rut_cliente = forms.CharField(label="RUT del Cliente", max_length=12, required=True)
    nombre_sensor = forms.CharField(label="Nombre del Sensor", max_length=100, required=True)
    id_dispositivo_mqtt = forms.CharField(label="ID del Dispositivo", max_length=100, required=True)
    
    latitud = forms.FloatField(
        label="Latitud",
        required=True,
        widget=forms.NumberInput(attrs={'step': 'any'}) # Campo numérico
    )
    longitud = forms.FloatField(
        label="Longitud",
        required=True,
        widget=forms.NumberInput(attrs={'step': 'any'}) # Campo numérico
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['direccion'].widget.attrs.update({'class': 'form-control'})
        self.fields['rut_cliente'].widget.attrs.update({'class': 'form-control', 'placeholder': '12.345.678-9'})
        self.fields['nombre_sensor'].widget.attrs.update({'class': 'form-control'})
        self.fields['id_dispositivo_mqtt'].widget.attrs.update({'class': 'form-control'})

    @transaction.atomic
    def save(self, empresa_admin):
        data = self.cleaned_data
        nuevo_user_auth = User.objects.create_user(
            username=data['username'],
            password=User.objects.make_random_password()
        )
        nuevo_user_perfil = nuevo_user_auth.usuario
        nuevo_user_perfil.rol = Usuario.Rol.CLIENTE
        nuevo_user_perfil.empresa_asociada = empresa_admin
        nuevo_user_perfil.direccion = data['direccion']
        nuevo_user_perfil.rut_cliente = data['rut_cliente']
        nuevo_user_perfil.save()

        Dispositivo.objects.create(
            usuario=nuevo_user_perfil,
            id_dispositivo_mqtt=data['id_dispositivo_mqtt'],
            nombre=data['nombre_sensor'],
            latitud=data['latitud'],
            longitud=data['longitud']
        )
        
        return nuevo_user_perfil
