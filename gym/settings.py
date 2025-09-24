import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent  # C:\gym

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] 
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-1234567890-esto-es-un-ejemplo")

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# When set to ``False`` the application will load vendor libraries from the
# local ``static/`` directory instead of using the CDN copies.  This is useful
# for environments without Internet access.
USE_CDN = False

# Subresource integrity hashes for the CDN hosted assets.  They are kept in a
# separate mapping so they can easily be updated without touching the
# templates.
CDN_INTEGRITY = {
    "bootstrap_css": "",
    "bootstrap_js": "",
    "bootstrap_icons_css": "",
    "select2_css": "",
    "select2_js": "",
    "jquery": "",
    "tabulator_css": "",
    "tabulator_js": "",
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gymapp',
    'widget_tweaks',

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

ROOT_URLCONF = 'gym.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'gym.context_processors.cdn',
            ],
        },
    },
]

WSGI_APPLICATION = 'gym.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_L10N = True
USE_TZ = True
