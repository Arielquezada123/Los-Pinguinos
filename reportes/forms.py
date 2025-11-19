from django import forms
from .models import Tarifa

class TarifaForm(forms.ModelForm):
    class Meta:
        model = Tarifa
        # Incluimos solo los campos que la empresa debe editar.
        # 'empresa' se asignará automáticamente en la vista.
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