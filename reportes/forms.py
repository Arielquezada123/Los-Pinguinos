from django import forms
from .models import Tarifa, ReglaAlerta
from sensores.models import Dispositivo
class TarifaForm(forms.ModelForm):
    class Meta:
        model = Tarifa
 
        fields = [
            'cargo_fijo', 
            'limite_tramo_1', 
            'valor_tramo_1', 
            'valor_tramo_2', 
            'iva'
        ]
        
        labels = {
            'cargo_fijo': 'Cargo Fijo',
            'limite_tramo_1': 'Límite Tramo 1',
            'valor_tramo_1': 'Valor Tramo 1',
            'valor_tramo_2': 'Valor Tramo 2',
            'iva': 'IVA'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            field = self.fields[field_name]
            field.widget.attrs.update({'class': 'form-control'})
class ReglaAlertaForm(forms.ModelForm):

    dias_seleccion = forms.MultipleChoiceField(
        choices=ReglaAlerta.DIAS_SEMANA,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Días Activos"
    )

    class Meta:
        model = ReglaAlerta
        fields = [
            'nombre', 'dispositivo', 
            'flujo_maximo', 'duracion_minima',
            'hora_inicio', 'hora_fin', 
            'enviar_email', 'activa'
        ]
        widgets = {
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'dispositivo': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Riego Nocturno'}),
            'flujo_maximo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'duracion_minima': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'flujo_maximo': 'Flujo Máximo (L/min)',
            'duracion_minima': 'Duración (minutos)',
            'dispositivo': 'Sensor Específico (Opcional)'
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            self.fields['dispositivo'].queryset = Dispositivo.objects.filter(usuario=user)

        if self.instance and self.instance.pk and self.instance.dias_semana:
            self.fields['dias_seleccion'].initial = self.instance.dias_semana.split(',')

    def clean(self):
        cleaned_data = super().clean()
        dias = cleaned_data.get('dias_seleccion')
        if dias:
            self.instance.dias_semana = ",".join(dias)
        return cleaned_data