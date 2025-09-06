from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Cliente, SolicitudServicio


class CustomUserCreationForm(UserCreationForm):
    # CAMPOS DE USUARIO
    first_name = forms.CharField(
        max_length=15,
        required=True,
        label="Nombre",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre (solo uno)'
        }),
        help_text='Ingresa solo tu primer nombre (máximo 15)'
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label="Apellido",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu apellido'
        })
    )
    
    email = forms.EmailField(
        required=True,
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )

    # CAMPOS DE CLIENTE
    telefono = forms.CharField(
        max_length=15,
        required=True,
        label="Teléfono",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+56 9 1234 5678'
        })
    )

    rut = forms.CharField(
        max_length=12,
        required=True,
        label="RUT",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12.345.678-9'
        })
    )

    direccion = forms.CharField(
        max_length=255,
        required=True,
        label="Dirección",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu dirección completa'
        })
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2', 'telefono', 'rut', 'direccion')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar widgets de campos heredados
        self.fields['username'].label = "Nombre de Usuario"
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Elige un nombre de usuario único'
        })
        self.fields['password1'].label = "Contraseña"
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Crea una contraseña segura'
        })
        self.fields['password2'].label = "Confirmar Contraseña"
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
            telefono_limpio = telefono.replace(' ', '').replace('+', '').replace('-', '')

            if Cliente.objects.filter(telefono=telefono).exists():
                raise forms.ValidationError(
                    '❌ Este número de teléfono ya está registrado.'
                )

        return telefono
    
    def clean_first_name(self):
        """Validar que el nombre no tenga espacios y sea corto"""
        first_name = self.cleaned_data.get('first_name')
        
        if first_name:
            # Verificar que no tenga espacios (solo un nombre)
            if ' ' in first_name:
                raise forms.ValidationError(
                    '❌ Ingresa solo un nombre, sin espacios.'
                )
            
            # Verificar longitud
            if len(first_name) > 15:
                raise forms.ValidationError(
                    '❌ El nombre no puede tener más de 15 caracteres.'
                )
        
        return first_name

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

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


class EditarPerfilForm(forms.Form):
    """Formulario para editar perfil de usuario"""
    
    # CAMPOS DE USUARIO
    first_name = forms.CharField(
        max_length=30,
        required=True,
        label="Nombre",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu nombre'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label="Apellido",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu apellido'
        })
    )
    
    email = forms.EmailField(
        required=True,
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        })
    )
    
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Nombre de Usuario",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu nombre de usuario'
        })
    )

    # CAMPOS DE CLIENTE
    telefono = forms.CharField(
        max_length=15,
        required=True,
        label="Teléfono",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+56 9 1234 5678'
        })
    )

    rut = forms.CharField(
        max_length=12,
        required=True,
        label="RUT",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12.345.678-9',
            'readonly': True  # El RUT no debería cambiar
        })
    )

    direccion = forms.CharField(
        max_length=255,
        required=True,
        label="Dirección",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu dirección completa'
        })
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Cargar datos actuales
        try:
            cliente = user.cliente
            self.fields['telefono'].initial = cliente.telefono
            self.fields['rut'].initial = cliente.rut
            self.fields['direccion'].initial = cliente.direccion
        except:
            pass
            
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['email'].initial = user.email
        self.fields['username'].initial = user.username

    def clean_username(self):
        """Validar que el nombre de usuario no exista (excepto el actual)"""
        username = self.cleaned_data.get('username')
        if username and username != self.user.username:
            if User.objects.filter(username=username).exists():
                raise forms.ValidationError(
                    '❌ Este nombre de usuario ya está en uso. Por favor, elige otro.'
                )
        return username

    def clean_email(self):
        """Validar que el email no exista (excepto el actual)"""
        email = self.cleaned_data.get('email')
        if email and email != self.user.email:
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError(
                    '❌ Este correo electrónico ya está registrado.'
                )
        return email

    def clean_telefono(self):
        """Validar que el teléfono no exista (excepto el actual)"""
        telefono = self.cleaned_data.get('telefono')
        if telefono:
            try:
                telefono_actual = self.user.cliente.telefono
                if telefono != telefono_actual:
                    if Cliente.objects.filter(telefono=telefono).exists():
                        raise forms.ValidationError(
                            '❌ Este número de teléfono ya está registrado.'
                        )
            except:
                if Cliente.objects.filter(telefono=telefono).exists():
                    raise forms.ValidationError(
                        '❌ Este número de teléfono ya está registrado.'
                    )
        return telefono

    def save(self):
        """Guardar los cambios en usuario y cliente"""
        # Actualizar usuario
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        self.user.username = self.cleaned_data['username']
        self.user.save()
        
        # Actualizar o crear cliente
        try:
            cliente = self.user.cliente
            cliente.telefono = self.cleaned_data['telefono']
            cliente.direccion = self.cleaned_data['direccion']
            cliente.save()
        except:
            Cliente.objects.create(
                user=self.user,
                telefono=self.cleaned_data['telefono'],
                rut=self.cleaned_data['rut'],
                direccion=self.cleaned_data['direccion']
            )
        
        return self.user


# MÉTODOS DE PAGO DISPONIBLES
METODOS_PAGO_CHOICES = [
    ('efectivo', 'Pago en Efectivo'),
    ('transferencia', 'Transferencia Bancaria'),
    ('mercadopago_card', 'Tarjeta Débito/Crédito - Mercado Pago'),
    ('mercadopago_transfer', 'Transferencia - Mercado Pago'),
]


class SolicitudServicioForm(forms.ModelForm):
    # NUEVO CAMPO: Método de pago
    metodo_pago = forms.ChoiceField(
        choices=METODOS_PAGO_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
            'required': True
        }),
        label="Método de Pago",
        help_text="⚠️ Importante: No podrás cambiar esta opción después de enviar la solicitud.",
        required=True
    )

    class Meta:
        model = SolicitudServicio
        fields = [
            'direccion_origen',
            'direccion_destino',
            'fecha_servicio',
            'descripcion_problema',
            'tipo_vehiculo',
            'marca_vehiculo',
            'modelo_vehiculo',
            'placa_vehiculo',
            'distancia_km',
            'metodo_pago'  # AGREGADO
        ]
        widgets = {
            'direccion_origen': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección donde está tu vehículo',
                'required': True
            }),
            'direccion_destino': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección de destino',
                'required': True
            }),
            'fecha_servicio': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': True
            }, format='%Y-%m-%dT%H:%M'),
            'descripcion_problema': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe el problema de tu vehículo',
                'required': True
            }),
            'distancia_km': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'placeholder': 'Distancia en kilómetros (opcional)',
                'min': '0'
            }),
            'tipo_vehiculo': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }, choices=[
                ('', 'Selecciona tipo de vehículo'),
                ('auto', 'Automóvil'),
                ('camioneta', 'Camioneta'),
                ('moto', 'Motocicleta'),
                ('camion', 'Camión'),
                ('otro', 'Otro')
            ]),
            'marca_vehiculo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Toyota, Chevrolet, Ford',
                'required': True
            }),
            'modelo_vehiculo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ej: Corolla, Spark, Focus',
                'required': True
            }),
            'placa_vehiculo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: ABCD12 o AB1234',
                'required': True
            })
        }
        labels = {
            'direccion_origen': 'Dirección de Origen',
            'direccion_destino': 'Dirección de Destino',
            'fecha_servicio': 'Fecha y Hora del Servicio',
            'descripcion_problema': 'Descripción del Problema',
            'marca_vehiculo': 'Marca del Vehículo',        # 🆕 AGREGAR
            'modelo_vehiculo': 'Modelo del Vehículo',      # 🆕 AGREGAR
            'ano_vehiculo': 'Año del Vehículo',            # 🆕 AGREGAR
            'color_vehiculo': 'Color del Vehículo',        # 🆕 AGREGAR
            'distancia_km': 'Distancia Estimada (km)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar zona horaria para fecha_servicio
        if self.instance and self.instance.pk:
            from django.utils import timezone
            if self.instance.fecha_servicio:
                # Convertir a zona horaria local
                fecha_local = timezone.localtime(self.instance.fecha_servicio)
                self.fields['fecha_servicio'].initial = fecha_local

    def clean_fecha_servicio(self):
        """Validar que la fecha no sea muy en el pasado (permitir hasta 1 hora atrás)"""
        fecha_servicio = self.cleaned_data.get('fecha_servicio')
        if fecha_servicio:
            from django.utils import timezone
            from datetime import timedelta

            # CORRECCIÓN: Hacer la fecha timezone-aware en zona horaria de Chile
            if fecha_servicio.tzinfo is None:
                fecha_servicio = timezone.make_aware(fecha_servicio, timezone.get_current_timezone())

            # Permitir fechas hasta 1 hora en el pasado (para compensar diferencias de zona horaria)
            limite_pasado = timezone.now() - timedelta(hours=1)

            if fecha_servicio < limite_pasado:
                raise forms.ValidationError(
                    f'❌ La fecha del servicio debe ser después del {limite_pasado.strftime("%d/%m/%Y %H:%M")}.'
                )
        return fecha_servicio

    def clean_metodo_pago(self):
        """Validar que el método de pago sea válido"""
        metodo_pago = self.cleaned_data.get('metodo_pago')
        metodos_validos = [choice[0] for choice in METODOS_PAGO_CHOICES]
        
        if metodo_pago not in metodos_validos:
            raise forms.ValidationError(
                '❌ Método de pago no válido. Por favor, selecciona una opción válida.'
            )
        
        return metodo_pago

    def clean_distancia_km(self):
        """Validar que la distancia sea positiva si se proporciona"""
        distancia_km = self.cleaned_data.get('distancia_km')
        if distancia_km is not None and distancia_km < 0:
            raise forms.ValidationError(
                '❌ La distancia no puede ser negativa.'
            )
        return distancia_km