"""
Django settings for main project.

Secrets come from .env; everything else is defined here.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["SECRET_KEY"]

DEBUG = os.environ.get("DEBUG", "True") == "True"


ALLOWED_HOSTS = ["*"]




INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'main.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'main.wsgi.application'



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get("POSTGRES_DB", "assignment"),
        'USER': os.environ.get("POSTGRES_USER", "neondb_owner"),
        'PASSWORD': os.environ["POSTGRES_PASSWORD"],
        'HOST': os.environ.get(
            "POSTGRES_HOST",
            "ep-blue-unit-a177g4f4-pooler.ap-southeast-1.aws.neon.tech",
        ),
        'PORT': os.environ.get("POSTGRES_PORT", "5432"),
        'OPTIONS': {
            'sslmode': os.environ.get("POSTGRES_SSLMODE", "require"),
            'prepare_threshold': None,
        },
    }
}



CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient'},
    }
}


AUTH_USER_MODEL = 'api.User'

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




REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['api.auth.ActiveUserJWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['api.permissions.IsActiveLocalUser'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
    'UNAUTHENTICATED_USER': None,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]



ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = "claude-haiku-4-5-20251001"
AI_TIMEOUT_SECONDS = 6
AI_MAX_RETRIES = 1
PUSH_PREVIEW_MAX_CHARS = 120

WORKER_BATCH_SIZE = 200
WORKER_POLL_SECONDS = 1


COUNTS_CACHE_SECONDS = 2


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
