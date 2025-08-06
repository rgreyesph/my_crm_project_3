# crm_project/settings.py (FINAL EB PREP VERSION - Response #155)

from pathlib import Path
import os
import dj_database_url # Import dj-database-url
from dotenv import load_dotenv
from django.middleware.security import SecurityMiddleware
from django.http import HttpResponsePermanentRedirect

print("DEBUG: All environment variables:", os.environ)
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file (for local development primarily)
# Ensures it reads .env from BASE_DIR (my_crm_project/.env)
load_dotenv(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# DEBUG automatically False unless explicitly 'True' in environment
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
print(f"DEBUG: DEBUG={DEBUG}")
# ALLOWED_HOSTS read from environment variable, split by comma
# Use a distinct name for prod hosts env var, default to empty string

DEFAULT_HOSTS = [
    'crm.herkings.com',
    'localhost',
    '127.0.0.1',
    '172.31.0.50',  # Internal EC2 IP for health checks
    'HerkingsCRM-env.eba-cmqakci9.ap-southeast-1.elasticbeanstalk.com',
    '.ap-southeast-1.compute.amazonaws.com',
]
ALLOWED_HOSTS_STR = os.environ.get('ALLOWED_HOSTS_PROD', ','.join(DEFAULT_HOSTS)).strip("'\"").split('#')[0].strip()
# ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(',') if host.strip()] #
ALLOWED_HOSTS = list(set(host.strip() for host in ALLOWED_HOSTS_STR.split(',') if host.strip()))
if not DEBUG:
    # ALLOWED_HOSTS.append('.elasticbeanstalk.com') #
    ALLOWED_HOSTS.extend(['.elasticbeanstalk.com', '.compute.amazonaws.com'])  # Cover ELB/EC2 IPs
if not DEBUG and not os.environ.get('ALLOWED_HOSTS_PROD'):
    print("WARNING: ALLOWED_HOSTS_PROD not set, using defaults.")
print(f"DEBUG: ALLOWED_HOSTS={ALLOWED_HOSTS}")

# Application definition
INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'dal_legacy_static',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic', # Whitenoise (place high)
    'django.contrib.staticfiles', # Must come AFTER whitenoise if using runserver_nostatic
    'django.contrib.humanize',
    # Third-party apps
    'django_filters',
    'django_ses_gateway',
    'crispy_forms',
    'crispy_bootstrap5',
    # Our custom apps: (Using AppConfig paths)
    'users.apps.UsersConfig',
    'core.apps.CoreConfig',
    'crm_entities.apps.CrmEntitiesConfig',
    'sales_territories.apps.SalesTerritoriesConfig',
    'sales_pipeline.apps.SalesPipelineConfig',
    'activities.apps.ActivitiesConfig',
    'sales_performance.apps.SalesPerformanceConfig',
]
# Exempt health check from HTTPS redirect
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
if SECURE_SSL_REDIRECT:
    class CustomSecurityMiddleware(SecurityMiddleware):
        def process_request(self, request):
            if request.path == '/health/' or request.path == '/':
                return None  # Skip HTTPS redirect for health check
            return super().process_request(request)

MIDDLEWARE = [
    # 'django.middleware.security.SecurityMiddleware', #
    'crm_project.middleware.CustomSecurityMiddleware',  # Replace SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware', # Whitenoise middleware (after Security)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Use original project name
ROOT_URLCONF = 'crm_project.urls'

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

# Use original project name
WSGI_APPLICATION = 'crm_project.wsgi.application'

# Database (Using dj-database-url for flexibility)
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"DEBUG: DATABASE_URL={DATABASE_URL}")
# Check if running in Elastic Beanstalk environment which sets RDS variables
# Fallback to building URL from RDS vars if DATABASE_URL isn't explicitly set in EB Env Properties
if not DATABASE_URL and 'RDS_DB_NAME' in os.environ:
     print("INFO: DATABASE_URL not set, building from RDS_* vars.")
     db_user = os.environ.get('RDS_USERNAME')
     db_pass = os.environ.get('RDS_PASSWORD')
     db_host = os.environ.get('RDS_HOSTNAME')
     db_port = os.environ.get('RDS_PORT')
     db_name = os.environ.get('RDS_DB_NAME')
     if db_user and db_pass and db_host and db_port and db_name:
          DATABASE_URL = f"postgres://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
     else:
          print("WARNING: Missing RDS_* environment variables, cannot build DATABASE_URL.")

if DATABASE_URL:
    # Require SSL for RDS connections in production (set DATABASE_SSL=True in Env Properties)
    SSL_REQUIRE = os.environ.get('DATABASE_SSL', 'True' if not DEBUG else 'False') == 'True'
    DATABASES = {'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600, ssl_require=SSL_REQUIRE)}
    print(f"INFO: Configured database using DATABASE_URL (SSL Require: {SSL_REQUIRE})")
else:
    # Fallback to local SQLite ONLY IF DEBUG is True
    if DEBUG:
         print("WARNING: DATABASE_URL or RDS_* environment variables not set, falling back to local SQLite.")
         DATABASES = { 'default': { 'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3', } }
    else:
         # Don't allow fallback to SQLite in production if DB isn't configured
         raise ValueError("Database configuration not found in environment variables for production!")


# Password validation
AUTH_PASSWORD_VALIDATORS = [ {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',}, ]

# Internationalization
LANGUAGE_CODE = 'en-us'; TIME_ZONE = 'Asia/Manila'; USE_I18N = True; USE_TZ = True

# Crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'; CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Static files (CSS, JavaScript, Images) - Configured for Whitenoise
STATIC_URL = '/static/'
# Directory where `collectstatic` will gather files for deployment.
# Whitenoise serves files from this directory in production.
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Directories where Django looks for static files during development (in addition to app static dirs)
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]  # Optional, for development
# Whitenoise storage backend (handles compression and caching headers)
'''
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
'''
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",  # No manifest/hashed for admin/DAL
    },
}
# Media files (User Uploads) - Not configured yet, defaults to local file system
# MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'mediafiles'
# Configure S3 later if needed for production media storage

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Login URLs
LOGIN_URL = 'login'; LOGIN_REDIRECT_URL = 'core:dashboard'; LOGOUT_REDIRECT_URL = '/'
AUTH_USER_MODEL = 'users.CustomUser'

# HTTPS Settings (Read from environment variables set by EB)
# Default to False if the variable isn't explicitly 'True'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'False') == 'True'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
#SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 0)) # Default to 0 (off)
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False') == 'True'
SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', 'False') == 'True'

# Trust X-Forwarded-Proto header from AWS ALB for determining request scheme
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Final check for SECRET_KEY in production
if not DEBUG and not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set for production environment!")

# ==============================================================================
# EMAIL CONFIGURATION
# ==============================================================================
if DEBUG:
    # For local development, all emails will be printed to your console/terminal.
    # This backend doesn't need any other settings to work.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'local-dev@example.com' # A placeholder for local dev

else:
    # In production, use Django's standard SMTP backend to connect to AWS SES.
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

    # The AWS SES SMTP server address for your region. This is what you correctly identified.
    EMAIL_HOST = 'email-smtp.ap-southeast-1.amazonaws.com'

    # Your SMTP credentials, which Django will read from the environment variables.
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

    # The "From" address for emails, read from an environment variable.
    # This MUST be an email or domain verified in your SES console.
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL')

    # Standard SMTP settings for a secure TLS connection.
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    
WHITENOISE_KEEP_ONLY_HASHED_FILES = False  # Keep un-hashed for admin/DAL compatibility