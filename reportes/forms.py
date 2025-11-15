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
            'cargo_fijo': 'Cargo Fijo Mensual (CLP)',
            'limite_tramo_1': 'Límite Primer Tramo (en m³)',
            'valor_tramo_1': 'Valor Tramo 1 (CLP por m³)',
            'valor_tramo_2': 'Valor Tramo 2 (CLP por m³)',
            'iva': 'IVA (Ej: 0.19 para 19%)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicamos los estilos oscuros de tu dashboard
        for field_name in self.fields:
            field = self.fields[field_name]
            # Usamos las clases de 'crear_cliente.html'
            field.widget.attrs.update({'class': 'form-control'})