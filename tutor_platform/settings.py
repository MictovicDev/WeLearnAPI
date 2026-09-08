from pathlib import Path
import dj_database_url
from datetime import timedelta
import os
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-only-for-local-dev')

DEBUG = os.getenv('DEBUG', 'False') == 'True'


ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost').split(',')



SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')
# Logging
LOGS_DIR = BASE_DIR / 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} [{levelname}] {name}: {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file_general": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "django.log",
            "maxBytes": 5 * 1024 * 1024,  # 5MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_errors": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "errors.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "level": "ERROR",
            "formatter": "verbose",
        },
        "file_stripe": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "stripe.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file_general", "file_errors"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "file_errors"],
            "level": "ERROR",
            "propagate": False,
        },
        # Use this one explicitly in wallet_views.py / services.py:
        #   import logging
        #   logger = logging.getLogger("paystack")
        "stripe": {
            "handlers": ["console", "file_stripe", "file_errors"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'daphne',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    'drf_spectacular',

    # Local apps
    'users',
    'tutors',
    'bookings',
    'reviews',
    'chat',
    "payment",
    "corsheaders",
    "wallets"
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_APPLICATION_FEE_PERCENT = 0.4

STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
ROOT_URLCONF = 'tutor_platform.urls'

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
            ],
        },
    },
]

ASGI_APPLICATION = 'tutor_platform.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0')],
        },
    },
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "weleardb",
        "USER": "mike",
        "PASSWORD": os.environ.get("DB_PASSWORD", 'hellopass123'),  # set in environment, no hardcoded fallback
        "HOST": "localhost",
        "PORT": "5432",
    }
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

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'https://api.welearnglobal.online',
]

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

GOOGLE_REDIRECT_URI = (
    "http://localhost:8000/google-calendar/callback/"
)

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# drf-spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Tutor Booking Platform API',
    'DESCRIPTION': (
        'A marketplace API connecting students with verified tutors for online '
        'and onsite learning sessions. Supports booking, messaging, reviews, and '
        'admin verification workflows.'
    ),
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'TAGS': [
        {'name': 'Auth', 'description': 'Registration, login, token refresh, logout'},
        {'name': 'Users', 'description': 'Student and tutor profile management'},
        {'name': 'Tutors', 'description': 'Tutor discovery, profiles, and availability'},
        {'name': 'Bookings', 'description': 'Session booking and management'},
        {'name': 'Reviews', 'description': 'Post-session ratings and feedback'},
        {'name': 'Messaging', 'description': 'Student-tutor communication'},
        {'name': 'Admin', 'description': 'Platform admin operations'},
    ],
}

# Celery
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
FRONTEND_URL = 'https://welearnglobal.vercel.app'
CELERY_TIMEZONE = 'Africa/Lagos'

# Email (Namecheap Private Email)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'mail.privateemail.com'
EMAIL_PORT = 465
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'noreply@welearnglobal.online')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')  # set in environment, no hardcoded fallback
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
DEFAULT_PAYMENT_GATEWAY = "stripe"
PAYMENT_SUCCESS_URL = os.getenv("PAYMENT_SUCCESS_URL")
PAYMENT_CANCEL_URL = os.getenv("PAYMENT_CANCEL_URL")


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

print(GOOGLE_CLIENT_ID)
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv(
    "GOOGLE_SERVICE_ACCOUNT_FILE"
)

GOOGLE_CALENDAR_ID = os.getenv(
    "GOOGLE_CALENDAR_ID"
)

print(GOOGLE_CALENDAR_ID)

# settings.py
SESSION_COOKIE_SAMESITE = 'Lax'  # Or 'None' if frontend and backend are on completely separate domains
SESSION_COOKIE_SECURE = True     # Required if SameSite='None' (HTTPS only)

print(GOOGLE_CLIENT_ID)
# print(GOOGLE_OAUTH_CLIENT_ID)
print(GOOGLE_CLIENT_SECRET)

