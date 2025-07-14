from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Cliente, SolicitudServicio


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )

    telefono = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+56 9 1234 5678'
        })
    )

    rut = forms.CharField(
        max_length=12,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12.345.678-9'
        })
    )

    direccion = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu dirección completa'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1',
                  'password2', 'telefono', 'rut', 'direccion')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar widgets de campos heredados
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Elige un nombre de usuario'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Crea una contraseña segura'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirma tu contraseña'
        })

    def clean_username(self):
        """Validar que el nombre de usuario no exista"""
        username = self.cleaned_data.get('username')
        if username:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError(
                    '❌ Este nombre de usuario ya está en uso. Por favor, elige otro.'
                )
        return username

    def clean_email(self):
        """Validar que el email no exista"""
        email = self.cleaned_data.get('email')
        if email:
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError(
                    '❌ Este correo electrónico ya está registrado. ¿Ya tienes una cuenta?'
                )
        return email

    def clean_rut(self):
        """Validar que el RUT no exista y tenga formato válido"""
        rut = self.cleaned_data.get('rut')
        if rut:
            # Limpiar el RUT (quitar puntos y guiones)
            rut_limpio = rut.replace('.', '').replace('-', '').strip()

            # Verificar si el RUT ya existe (buscar tanto con formato como sin formato)
            if Cliente.objects.filter(rut=rut).exists() or Cliente.objects.filter(rut=rut_limpio).exists():
                raise forms.ValidationError(
                    '❌ Este RUT ya está registrado en el sistema. ¿Ya tienes una cuenta?'
                )

            # Validación básica de formato de RUT chileno
            if len(rut_limpio) < 8 or len(rut_limpio) > 9:
                raise forms.ValidationError(
                    '❌ Formato de RUT inválido. Ejemplo: 12.345.678-9'
                )

        return rut

    def clean_telefono(self):
        """Validar que el teléfono no exista"""
        telefono = self.cleaned_data.get('telefono')
        if telefono:
            # Limpiar el teléfono (quitar espacios y caracteres especiales)
            telefono_limpio = telefono.replace(
                ' ', '').replace('+', '').replace('-', '')

            if Cliente.objects.filter(telefono=telefono).exists():
                raise forms.ValidationError(
                    '❌ Este número de teléfono ya está registrado.'
                )

        return telefono

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']

        if commit:
            user.save()
            # Crear perfil de cliente
            Cliente.objects.create(
                user=user,
                telefono=self.cleaned_data['telefono'],
                rut=self.cleaned_data['rut'],
                direccion=self.cleaned_data['direccion']
            )
        return user


class SolicitudServicioForm(forms.ModelForm):
    # NUEVOS CAMPOS DEL VEHÍCULO
    tipo_vehiculo = forms.ChoiceField(
        choices=[
            ('', 'Seleccionar tipo'),
            ('auto', 'Automóvil'),
            ('suv', 'SUV/Camioneta'),
            ('pickup', 'Pick-up'),
            ('moto', 'Motocicleta'),
            ('furgon', 'Furgón'),
            ('otro', 'Otro'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
        })
    )
    
    marca_vehiculo = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Toyota, Chevrolet, Ford'
        })
    )
    
    modelo_vehiculo = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: Corolla, Spark, Ranger'
        })
    )
    
    placa_vehiculo = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: AB-CD-12 o ABCD-12',
            'style': 'text-transform: uppercase'
        })
    )

    class Meta:
        model = SolicitudServicio
        fields = [
            'direccion_origen',
            'direccion_destino',
            'fecha_servicio',
            'descripcion_problema',
            'distancia_km',
            # NUEVOS CAMPOS AGREGADOS
            'tipo_vehiculo',
            'marca_vehiculo', 
            'modelo_vehiculo',
            'placa_vehiculo'
        ]
        widgets = {
            'direccion_origen': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección donde está tu vehículo'
            }),
            'direccion_destino': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección de destino'
            }),
            'fecha_servicio': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'descripcion_problema': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el problema de tu vehículo'
            }),
            'distancia_km': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'Distancia en kilómetros'
            })
        }

    def clean_fecha_servicio(self):
        """Validar que la fecha no sea muy en el pasado (permitir hasta 1 hora atrás)"""
        fecha_servicio = self.cleaned_data.get('fecha_servicio')
        if fecha_servicio:
            from django.utils import timezone
            from datetime import timedelta

            # Permitir fechas hasta 1 hora en el pasado (para compensar diferencias de zona horaria)
            limite_pasado = timezone.now() - timedelta(hours=1)

            if fecha_servicio < limite_pasado:
                raise forms.ValidationError(
                    f'❌ La fecha del servicio debe ser después del {limite_pasado.strftime("%d/%m/%Y %H:%M")}.'
                )
        return fecha_servicio
