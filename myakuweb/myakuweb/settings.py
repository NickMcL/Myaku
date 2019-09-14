"""Django settings for myakuweb project."""

import os
from typing import Dict, List

from myaku.utils import get_value_from_env_file, get_value_from_env_variable

debug_mode_flag = os.environ.get('DJANGO_DEBUG_MODE', 1)
if int(debug_mode_flag) == 1:
    DEBUG = True
else:
    DEBUG = False

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if DEBUG:
    if os.environ.get('DJANGO_SECRET_KEY_FILE') is not None:
        SECRET_KEY = get_value_from_env_file('DJANGO_SECRET_KEY_FILE')
    else:
        SECRET_KEY = 'DevUseOnlySecretKey'
else:
    # Always use secret key from docker secret in prod
    SECRET_KEY = get_value_from_env_file('DJANGO_SECRET_KEY_FILE')

if DEBUG:
    ALLOWED_HOSTS: List[str] = []
else:
    allowed_hosts_filedata = get_value_from_env_file(
        'MYAKUWEB_ALLOWED_HOSTS_FILE'
    )
    ALLOWED_HOSTS = [
        host for host in allowed_hosts_filedata.split() if len(host) > 0
    ]


# Application definition

INSTALLED_APPS = [
    'search.apps.SearchConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
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

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'

ROOT_URLCONF = 'myakuweb.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'myakuweb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES: Dict = {}


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.'
                'NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATICFILES_DIRS = [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),
]

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

if DEBUG:
    STATIC_URL = os.environ.get('MYAKUWEB_STATIC_URL', '/static/')
else:
    STATIC_URL = get_value_from_env_variable('MYAKUWEB_STATIC_URL')

# Other misc settings

APPEND_SLASH = False
