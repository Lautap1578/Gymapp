from django import forms
from django.forms import inlineformset_factory
from .models import Member, Rutina, DetalleRutina



class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'dni', 'nombre_apellido', 'telefono', 'direccion', 'gmail', 'edad',
            'historial_deportivo', 'experiencias_gimnasios', 'historial_lesivo',
            'enfermedades', 'objetivos', 'frecuencia_semana'
        ]
        widgets = {
            'historial_deportivo': forms.Textarea(attrs={'rows': 3}),
            'experiencias_gimnasios': forms.Textarea(attrs={'rows': 3}),
            'historial_lesivo': forms.Textarea(attrs={'rows': 3}),
            'enfermedades': forms.Textarea(attrs={'rows': 3}),
            'objetivos': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_gmail(self):
        gmail = self.cleaned_data.get('gmail')
        if gmail:
            gmail = gmail.lower()
            if not gmail.endswith("@gmail.com"):
                raise forms.ValidationError("El correo debe terminar en @gmail.com")
            self.cleaned_data['gmail'] = gmail
        return gmail


class MemberInfoForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'historial_deportivo',
            'experiencias_gimnasios',
            'historial_lesivo',
            'enfermedades',
            'objetivos',
            'frecuencia_semana',
        ]
        widgets = {
            'historial_deportivo': forms.Textarea(attrs={'rows': 3}),
            'experiencias_gimnasios': forms.Textarea(attrs={'rows': 3}),
            'historial_lesivo': forms.Textarea(attrs={'rows': 3}),
            'enfermedades': forms.Textarea(attrs={'rows': 3}),
            'objetivos': forms.Textarea(attrs={'rows': 3}),
        }


DetalleRutinaFormSet = inlineformset_factory(
    Rutina,
    DetalleRutina,
    fields=[
        "categoria",
        "ejercicio",
        "series",
        "repeticiones",
        "peso",
        "descanso",
        "rir",
        "sensaciones",
        "notas",
        "es_calentamiento",
    ],
    extra=0,
    can_delete=False,
)
