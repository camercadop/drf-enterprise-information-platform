from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "apps.sys_audit",
    "apps.sys_user_event",
    "apps.sys_health",
    "apps.sys_permissions",
    "apps.tenant_settings",
    "apps.tenants",
    "apps.iam_teams",
    "apps.iam_roles",
    "apps.iam_users",
    "apps.iam_auth",
    "apps.dms_document_types",
    "apps.dms_documents",
    "apps.dms_document_versions",
    "apps.sys_eventbus",
    "apps.dms_ingestion",
    "apps.dms_metadata",
    "storages",
]

AUTH_USER_MODEL = "iam_users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.tenants.middleware.TenantContextMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        **env.db("DATABASE_URL"),
        "CONN_MAX_AGE": env.int("DB_CONN_MAX_AGE", default=600),
        "OPTIONS": {
            "connect_timeout": env.int("DB_CONNECT_TIMEOUT", default=5),
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "socket_connect_timeout": env.int("REDIS_CONNECT_TIMEOUT", default=3),
            "socket_timeout": env.int("REDIS_SOCKET_TIMEOUT", default=3),
            "protocol": 2,
        },
    },
    "schema": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": BASE_DIR / ".cache" / "schema",
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MB

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.tenants.authentication.TenantJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "core.filters.base.SmartFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
        "core.filters.base.SoftDeleteFilterBackend",
        "apps.tenants.filters.TenantFilterBackend",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "core.renderers.APIRenderer",
    ],
    "EXCEPTION_HANDLER": "core.exceptions.handler.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "core.pagination.page.CustomPagination",
    "PAGE_SIZE": 10,
    "NON_FIELD_ERRORS_KEY": "GLOBAL_ERRORS",
    "DEFAULT_SCHEMA_CLASS": "core.openapi.AutoSchema",
    "DEFAULT_SERIALIZER_PLUGINS": [
        "core.serializers.plugins.NonEditableFieldsSerializerPlugin",
        "apps.tenants.plugins.TenantInjectionSerializerPlugin",
        "apps.sys_audit.plugins.AuditSerializerPlugin",
    ],
    "DEFAULT_VIEWSET_PLUGINS": [
        "apps.tenants.plugins.TenantContextViewSetPlugin",
        "apps.sys_audit.plugins.AuditViewSetPlugin",
    ],
}

VIEWSET_FILTER_MULTI_VALUE_SEPARATOR = env(
    "VIEWSET_FILTER_MULTI_VALUE_SEPARATOR", default=","
)

SPECTACULAR_SETTINGS = {
    "TITLE": "DRF Enterprise Information Platform",
    "DESCRIPTION": "Multi-tenant enterprise platform API.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/",
    "SCHEMA_CACHING": True,
    "SCHEMA_CACHE_BACKEND": "schema",
}


LOG_LEVEL = env("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.json.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
            "rename_fields": {
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger",
            },
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}


APP_DMS_INGESTION = {
    "STORAGE_BACKEND": env(
        "DMS_INGESTION_STORAGE_BACKEND",
        default="django.core.files.storage.FileSystemStorage",
    ),
    "STORAGE_LOCATION": env(
        "DMS_INGESTION_STORAGE_LOCATION",
        default=str(BASE_DIR / "media" / "ingestion"),
    ),
    "MAX_FILE_SIZE_BYTES": env.int(
        "DMS_INGESTION_MAX_FILE_SIZE_BYTES",
        default=DATA_UPLOAD_MAX_MEMORY_SIZE,
    ),
    "ALLOWED_MIME_TYPES": [],
    "ALLOWED_EXTENSIONS": [],
    "PIPELINE_PROCESSORS": [
        "apps.dms_ingestion.processors.ChecksumProcessor",
        "apps.dms_ingestion.processors.MetadataProcessor",
    ],
    "STORAGE_NAME_GENERATOR": "apps.dms_ingestion.storage.generate_storage_name",
}

APP_SYS_EVENTBUS = {
    "STREAM_NAME": env("EVENTBUS_STREAM_NAME", default="sys:eventbus"),
    "DLQ_STREAM_NAME": env("EVENTBUS_DLQ_STREAM_NAME", default="sys:eventbus:dlq"),
    "CONSUMER_GROUP": env("EVENTBUS_CONSUMER_GROUP", default="sys_eventbus_group"),
    "CONSUMER_NAME": env("EVENTBUS_CONSUMER_NAME", default="sys_eventbus_consumer"),
    "POLL_INTERVAL_SECONDS": env.int("EVENTBUS_POLL_INTERVAL_SECONDS", default=5),
    "MAX_RETRIES": env.int("EVENTBUS_MAX_RETRIES", default=3),
    "BATCH_SIZE": env.int("EVENTBUS_BATCH_SIZE", default=100),
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULE = {
    "poll-eventbus": {
        "task": "apps.sys_eventbus.tasks.poll_eventbus",
        "schedule": APP_SYS_EVENTBUS["POLL_INTERVAL_SECONDS"],
    },
}

AUTH_RATE_LIMIT = {
    "IP_RATE": env("AUTH_RATE_LIMIT_IP", default="10/minute"),
    "EMAIL_RATE": env("AUTH_RATE_LIMIT_EMAIL", default="5/minute"),
}

AUTH_LOCKOUT = {
    "MAX_ATTEMPTS": env.int("AUTH_LOCKOUT_MAX_ATTEMPTS", default=5),
    "LOCKOUT_DURATION": env.int("AUTH_LOCKOUT_DURATION", default=900),
}

AUTH_SESSION = {
    "MAX_CONCURRENT_SESSIONS": env.int("AUTH_MAX_CONCURRENT_SESSIONS", default=0),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("ACCESS_TOKEN_LIFETIME_MINUTES", default=30)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}
