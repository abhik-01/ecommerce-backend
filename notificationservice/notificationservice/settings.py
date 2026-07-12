from pathlib import Path
from os import getenv
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = getenv('SECRET_KEY', 'django-insecure-fallback-change-in-prod')
DEBUG = getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'notificationservice.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'notificationservice.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': getenv('DB_NAME', 'notificationservice'),
        'USER': getenv('DB_USER', 'root'),
        'PASSWORD': getenv('DB_PASSWORD', ''),
        'HOST': getenv('DB_HOST', 'localhost'),
        'PORT': getenv('DB_PORT', '3306'),
    }
}

JWT_SECRET_KEY = getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-prod')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'notifications.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

KAFKA_BOOTSTRAP_SERVERS = getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_CONSUMER_GROUP = 'notification-service'
KAFKA_TOPICS = [
    'user.registered',
    'order.created',
    'order.status.updated',
    'payment.completed',
    'payment.failed',
]

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = getenv('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = getenv('DEFAULT_FROM_EMAIL', 'no-reply@ecommerce.com')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
