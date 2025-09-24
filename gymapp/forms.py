from django import forms
from django.forms import inlineformset_factory
from .models import Member, Rutina, DetalleRutina, Payment
from datetime import date


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


# === Form de pago por plan ===
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["member", "mes", "plan"]
        widgets = {
            # usamos type="month" en vez de date
            "mes": forms.DateInput(
                attrs={"type": "month"},
                format="%Y-%m"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aceptar formato año-mes
        self.fields["mes"].input_formats = ["%Y-%m", "%Y-%m-%d"]

    def clean_mes(self):
        """
        Normalizo la fecha al primer día del mes.
        """
        mes = self.cleaned_data["mes"]
        return mes.replace(day=1)


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
