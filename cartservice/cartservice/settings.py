from pathlib import Path
from os import getenv
from dotenv import load_dotenv
import mongoengine

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
    'cart.apps.CartConfig',
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

ROOT_URLCONF = 'cartservice.urls'

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

WSGI_APPLICATION = 'cartservice.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# MongoDB
MONGO_HOST = getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(getenv('MONGO_PORT', '27017'))
MONGO_DB = getenv('MONGO_DB', 'cartservice')
MONGO_USER = getenv('MONGO_USER', '')
MONGO_PASSWORD = getenv('MONGO_PASSWORD', '')

_mongo_kwargs = dict(db=MONGO_DB, host=MONGO_HOST, port=MONGO_PORT)
if MONGO_USER:
    _mongo_kwargs['username'] = MONGO_USER
    _mongo_kwargs['password'] = MONGO_PASSWORD
    _mongo_kwargs['authentication_source'] = 'admin'

mongoengine.connect(**_mongo_kwargs)

# Redis cache
REDIS_URL = getenv('REDIS_URL', 'redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'TIMEOUT': 3600,
    }
}

KAFKA_BOOTSTRAP_SERVERS = getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

JWT_SECRET_KEY = getenv('JWT_SECRET_KEY', 'jwt-secret-change-in-prod')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'cart.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

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
