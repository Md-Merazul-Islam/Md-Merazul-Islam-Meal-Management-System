
from celery.schedules import schedule
import stripe
from celery.schedules import crontab
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import timedelta
load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

ALLOWED_HOSTS = ['*']  # Allow host

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',

    'corsheaders',
    'django_celery_beat',


    # Local apps
    'auths',
    'products',
    'autoemail',
    'contacts',
    'areas',
    'newsletter',
    'subscriptions',
    'order_app',
    'weekly_order_manage',
    'week_order_admin',
    # 'v2_order_app',

    # for superbase data basee
    "whitenoise.runserver_nostatic",

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    "corsheaders.middleware.CorsMiddleware",  # corse headers middleware

    # for superbase data basee
    # ...
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # ...
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

ROOT_URLCONF = 'project_root.urls'  # project_root is the name of the project

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates',],
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

WSGI_APPLICATION = 'project_root.wsgi.application'
# WSGI_APPLICATION = 'project_root.wsgi.app'


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

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# extra settings add from me --------------------------------


# extra settings add from me --------------------------------
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',

]

SITE_ID = 1


LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        "rest_framework.authentication.SessionAuthentication",
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        # 'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    # 'EXCEPTION_HANDLER': 'utils.utils.custom_exception_handler',


}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=70),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}


EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

AUTH_USER_MODEL = 'auths.CustomUser'

SESSION_COOKIE_AGE = 3600  # 1 hour in seconds

# corse
CORS_ALLOW_ALL_ORIGINS = True
CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:5500',
    'http://127.0.0.1:5501',
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'https://*.127.0.0.1',
    'https://api.preisslersfruestueck.at',
    'https://preisslersfruestueck.at',
    'https://api.preisslersfruehstueck.at',
    'https://preisslersfruehstueck.at',


]

CSRF_TRUSTED_ORIGINS = [
    'https://*.127.0.0.1',
    'http://localhost:8000',
    'http://127.0.0.1:5500',
    'http://127.0.0.1:5501',
    'http://127.0.0.1:8000',
    'http://localhost:3000',
    'http://localhost:5173',
    'https://api.preisslersfruestueck.at',
    'https://api.preisslersfruehstueck.at',
    'https://api.preisslersfruehstueck.at',
    'https://preisslersfruehstueck.at',
]


CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'DELETE',
    'PATCH',
    'OPTIONS'
]


# --- Email  Backend --------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 2525

EMAIL_USE_TLS = True
# # for email notification
EMAIL_HOST_USER = '889678001@smtp-brevo.com'
EMAIL_HOST_PASSWORD = 'BdcV982PfYmnWgEK'
DEFAULT_FROM_EMAIL = 'ashrafulsifat26@gmail.com'
BEKARY_EMAIL = 'bluskybooking.io@gmail.com'

ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')


SECRET_KEY = os.environ.get('SECRET_KEY')

DEBUG = True


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'gepixelt_db',
#         'USER': 'gepixelt_user',
#         'PASSWORD': 'password',
#         'HOST': 'db',
#         'PORT': '5432',
#     }
# }


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'postgres',
#         'USER': 'postgres.cmestvoziqiqpceercse',
#         'PASSWORD': 'viu8@UPQnuAQbKm',
#         'HOST': 'aws-0-ap-southeast-1.pooler.supabase.com',
#         'PORT': '5432',
#     }
# }


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

STATIC_URL = "/static/"

# # DigitalOcean Spaces Credentials
AWS_S3_ENDPOINT_URL = os.getenv(
    "AWS_S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_REGION = "nyc3"

AWS_S3_ADDRESSING_STYLE = "virtual"


# Public media file access (change ACL if needed)
AWS_S3_OBJECT_PARAMETERS = {
    "CacheControl": "max-age=86400",
    "ACL": "public-read",
}

MEDIA_URL = f"https://{AWS_S3_ENDPOINT_URL}/"
# DigitalOcean Spaces Bucket URL
MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"

STRIPE_TEST_SECRET_KEY = os.getenv("STRIPE_TEST_SECRET_KEY")
STRIPE_TEST_PUBLIC_KEY = os.getenv("STRIPE_TEST_PUBLIC_KEY")
STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET")

CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Berlin'  # Timezone
# CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_SCHEDULE = {

    # send_daily_product_list_email_with_monitoring
    'send-daily-product-list-with-monitoring': {
        'task': 'weekly_order_manage.tasks.send_daily_product_list_email_with_monitoring',
        # This will run at 8:00 AM every day
        'schedule': crontab(hour=8, minute=0),
        # 'schedule': crontab(minute='*/1'),
    },
    # send_daily_product_list_email
    'send-daily-product-list': {
        'task': 'weekly_order_manage.tasks.send_daily_product_list_email',
        # Schedule at 10:00 PM German time (Europe/Berlin)
        'schedule': crontab(hour=22, minute=0),
        # 'schedule': crontab(minute='*/1'),
    },

    # Run every minute for testing (change to weekly/Monday in production)
    'process_weekly_charges_schedule': {
        'task': 'weekly_order_manage.tasks.process_weekly_charges',
        # change to crontab(hour=0, minute=0, day_of_week=1) for Mondays
        'schedule': crontab(hour=0, minute=0, day_of_week=1),
        # 'schedule': crontab(minute='*/1'),
    },

    # Check and update expired orders daily at midnight
    'check-and-update-expired-orders': {
        'task': 'weekly_order_manage.tasks.check_and_update_expired_orders',
        # Run daily at midnight
        'schedule': crontab(hour=0, minute=0),
    },

    # Send email for expired orders daily at midnight
    'send-expired-order-email': {
        'task': 'weekly_order_manage.tasks.send_expired_order_email',
        # Run daily at midnight
        'schedule': crontab(hour=0, minute=0),
    },



}


CELERY_BEAT_SCHEDULE_FILENAME = '/data/celerybeat-schedule'


PAYPAL_MODE = 'sandbox'
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_TEST_CLIENT_ID')
PAYPAL_CLIENT_SECRET = os.getenv('PAYPAL_TEST_SECRET_KEY')


LOG_DIR = os.path.join(BASE_DIR, 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
            'formatter': 'verbose',
        },
    },

    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },

    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'myapp': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    },
}
