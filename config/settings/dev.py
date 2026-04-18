from .base import *

DEBUG = True
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '192.168.1.200',
    '*',
    
    '192.168.1.*'
]

CSRF_TRUSTED_ORIGINS = [
    'https://rkaanb.pythonanywhere.com',
    'http://rkaanb.pythonanywhere.com',
    'http://192.168.1.200:8000',
    'http://192.168.1.110:8000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

import os

DB_NAME = os.getenv("DB_NAME", "restoran_db")
DB_USER = os.getenv("DB_USER", "restoran_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "RestoranDB_2026")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'CONN_MAX_AGE': 60,
        'OPTIONS': {},
    }
}