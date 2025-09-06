"""
Django settings for grua_platform project.
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-your-secret-key-here')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'grua_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← AGREGADO PARA SERVIR ESTÁTICOS
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'grua_platform.urls'

# ✅ CONFIGURACIÓN CORREGIDA DE TEMPLATES
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'grua_app.context_processors.disponibilidad_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'grua_platform.wsgi.application'

# Database
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-CL'  # ← CAMBIADO PARA CHILE
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# ✅ CONFIGURACIÓN COMPLETA DE ARCHIVOS ESTÁTICOS
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# ✅ DIRECTORIOS DE ARCHIVOS ESTÁTICOS (CORREGIDO)
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Carpeta principal
    BASE_DIR / 'grua_app' / 'static',  # ← AGREGAR ESTA LÍNEA
]

# ✅ CONFIGURACIÓN PARA WHITENOISE (SERVIR ESTÁTICOS EN PRODUCCIÓN)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ✅ CONFIGURACIÓN DE LOGIN CORREGIDA
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'alexismkt1989@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'iifv wcls xqtq vekg')
DEFAULT_FROM_EMAIL = 'alexismkt1989@gmail.com'
EMAIL_USE_SSL = False
SERVER_EMAIL = 'alexismkt1989@gmail.com'

# CSRF trusted origins for deployment
CSRF_TRUSTED_ORIGINS = [
    'https://gruastyle.com',
    'https://www.gruastyle.com',
    'https://grua-style-pwa-production.up.railway.app',
    'https://grua-style-pwa-production-e1a8f1c34a86.herokuapp.com',
    'https://web-production-f080f.up.railway.app',
    'https://*.railway.app',
]

# Configuración CSRF para Railway
if 'RAILWAY_ENVIRONMENT' in os.environ or 'railway' in os.environ.get('RAILWAY_DEPLOYMENT_ID', ''):
    CSRF_COOKIE_SECURE = False
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False

# ========================================
# 🆕 CONFIGURACIÓN MERCADO PAGO
# ========================================

# Función para obtener variables de entorno con valores por defecto
def get_env_var(var_name, default_value=''):
    return os.environ.get(var_name, default_value)

# Credenciales Mercado Pago
MERCADOPAGO_PUBLIC_KEY = 'APP_USR-c040be87-5ea3-48e7-ad51-9be676f8a4c4'
MERCADOPAGO_ACCESS_TOKEN = 'APP_USR-5083384518821496-081312-681624599b206b49d80fb21f12356329-2544553674'
MERCADOPAGO_WEBHOOK_SECRET = 'webhook-secret-temporal'
MERCADOPAGO_SANDBOX = False

# URL base para webhooks
BASE_HOST = get_env_var('BASE_HOST', 'http://127.0.0.1:8000')

# Datos de transferencia bancaria para mostrar al usuario
BANK_TRANSFER_INFO = {
    'bank_name': 'Banco de Chile',
    'account_type': 'Cuenta Corriente',
    'account_number': '123456789',
    'rut': '12.345.678-9',
    'account_holder': 'Grúa Style SpA',
    'email': 'pagos@gruastyle.cl',
    'phone': '+56 9 1234 5678'
}

# Configuración de tarifas
PAYMENT_CONFIG = {
    'currency': 'CLP',
    'max_installments': 6,  # Máximo 6 cuotas
    'min_amount': 10000,    # Monto mínimo $10.000 CLP
    'webhook_timeout': 30,  # Timeout para webhooks en segundos
}

# Debug settings print (para development)
if DEBUG:
    print(f"🔍 DEBUG SETTINGS.PY:")
    print(f" EMAIL_HOST_USER: {EMAIL_HOST_USER}")
    print(f" MERCADOPAGO_SANDBOX: {MERCADOPAGO_SANDBOX}")
    print(f" BASE_HOST: {BASE_HOST}")
    print(f" MERCADOPAGO_PUBLIC_KEY: {MERCADOPAGO_PUBLIC_KEY[:20]}..." if MERCADOPAGO_PUBLIC_KEY else "No configurado")

# ========================================
# SISTEMA DE NOTIFICACIONES
# ========================================

# Email del administrador para alertas
NOTIFICATIONS_ADMIN_EMAIL = 'monardes.luis@gmail.com'  # CAMBIA POR TU EMAIL REAL

# ========================================
# SISTEMA DE NOTIFICACIONES TELEGRAM
# ========================================

# Token del bot de Telegram (obtenido de @BotFather)
TELEGRAM_BOT_TOKEN = '8379152044:AAHoS8b2RCdZ2SBGENvVkIlYT3RpmqXjuE8'  # Reemplazar con el token real

# Chat ID del administrador (obtenido de @userinfobot)
TELEGRAM_ADMIN_CHAT_ID = '6810175002'  # Reemplazar con tu chat ID

# ========================================
# CONFIGURACIÓN PARA PRODUCCIÓN
# ========================================

# Detectar si estamos en Railway (producción)
if 'RAILWAY_ENVIRONMENT' in os.environ:
    DEBUG = False
    ALLOWED_HOSTS = ['gruastyle.com', 'www.gruastyle.com', '*.railway.app', '*.up.railway.app']
    
    # Base de datos PostgreSQL en Railway
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
    
    # Configuración HTTPS y seguridad
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    
    # URLs base para producción
    BASE_HOST = 'https://www.gruastyle.com'
    
    print("🚀 MODO PRODUCCIÓN ACTIVADO")
else:
    print("💻 MODO DESARROLLO LOCAL")