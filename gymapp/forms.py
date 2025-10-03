from django import forms
from django.forms import inlineformset_factory
from .models import Member, Rutina, DetalleRutina, Payment, Ejercicio
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


class DetalleRutinaPayloadForm(forms.Form):
    """Valida las filas enviadas por el editor moderno de rutinas."""

    MAX_FILAS = 200

    categoria = forms.CharField(
        required=False,
        max_length=DetalleRutina._meta.get_field("categoria").max_length,
    )
    ejercicio_id = forms.IntegerField(required=False, min_value=1)
    ejercicio = forms.IntegerField(required=False, min_value=1)
    series = forms.CharField(
        required=False,
        max_length=DetalleRutina._meta.get_field("series").max_length,
    )
    reps = forms.CharField(
        required=False,
        max_length=DetalleRutina._meta.get_field("repeticiones").max_length,
    )
    kilos = forms.CharField(
        required=False,
        max_length=DetalleRutina._meta.get_field("peso").max_length,
    )
    descanso = forms.CharField(
        required=False,
        max_length=DetalleRutina._meta.get_field("descanso").max_length,
    )
    rir = forms.CharField(
        required=False,
        max_length=DetalleRutina._meta.get_field("rir").max_length,
    )
    sensaciones = forms.CharField(required=False, max_length=2000)
    notas = forms.CharField(required=False, max_length=2000)
    es_calentamiento = forms.BooleanField(required=False)

    def clean_categoria(self):
        categoria = self.cleaned_data.get("categoria") or ""
        return categoria.strip()

    def clean_series(self):
        series = self.cleaned_data.get("series") or ""
        return series.strip()

    def clean_reps(self):
        reps = self.cleaned_data.get("reps") or ""
        return reps.strip()

    def clean_kilos(self):
        kilos = self.cleaned_data.get("kilos") or ""
        return kilos.strip()

    def clean_descanso(self):
        descanso = self.cleaned_data.get("descanso") or ""
        return descanso.strip()

    def clean_rir(self):
        rir = self.cleaned_data.get("rir") or ""
        return rir.strip()

    def clean_sensaciones(self):
        sensaciones = self.cleaned_data.get("sensaciones") or ""
        return sensaciones.strip()

    def clean_notas(self):
        notas = self.cleaned_data.get("notas") or ""
        return notas.strip()

    def clean(self):
        cleaned = super().clean()
        # Homogeneizar: preferimos ejercicio_id si está presente.
        ejercicio_id = cleaned.get("ejercicio_id")
        ejercicio_alt = cleaned.get("ejercicio")
        elegido = ejercicio_id or ejercicio_alt

        if elegido:
            if not Ejercicio.objects.filter(id=elegido).exists():
                # Asociar el error al campo provisto originalmente
                campo_error = "ejercicio_id" if ejercicio_id else "ejercicio"
                self.add_error(campo_error, "El ejercicio seleccionado no existe.")
            else:
                cleaned["ejercicio_id"] = elegido
        else:
            cleaned["ejercicio_id"] = None
        return cleaned
