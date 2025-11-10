from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Usuario

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
            'limite_consumo_mensual': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'limite_consumo_mensual': 'Límite de Consumo Mensual (Litros)'
        }