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
    'payments.apps.PaymentsConfig',
    'rest_framework',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOWED_ORIGINS = getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS_ALLOW_ALL_ORIGINS = DEBUG

ROOT_URLCONF = 'paymentservice.urls'

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

WSGI_APPLICATION = 'paymentservice.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': getenv('DB_NAME', 'paymentservice'),
        'USER': getenv('DB_USER', 'root'),
        'PASSWORD': getenv('DB_PASSWORD', ''),
        'HOST': getenv('DB_HOST', 'localhost'),
        'PORT': getenv('DB_PORT', '3306'),
    }
}

JWT_SECRET_KEY = getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-prod')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'payments.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

STRIPE_SECRET_KEY = getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = getenv('STRIPE_WEBHOOK_SECRET', '')

RAZORPAY_KEY_ID = getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = getenv('RAZORPAY_KEY_SECRET', '')

KAFKA_BOOTSTRAP_SERVERS = getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

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
