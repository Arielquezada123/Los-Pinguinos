# watermilimiter/sensores/forms.py
from django import forms
from .models import Dispositivo

class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
 
        fields = ['nombre', 'id_dispositivo_mqtt', 'latitud', 'longitud']
        labels = {
            'nombre': 'Nombre del Sensor',
            'id_dispositivo_mqtt': 'ID del Dispositivo',
        }
        
        widgets = {
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['nombre'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Ej: Sensor Jardín'})
        self.fields['id_dispositivo_mqtt'].widget.attrs.update({
            'class': 'form-control', 
            'placeholder': 'Ej: sensor001',
            'aria-describedby': 'id_help'
        })