ALLOWED_HOSTS = [
    "health.sclab.in",
    "13.204.125.52",
]

CSRF_TRUSTED_ORIGINS = [
    "https://health.sclab.in",
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
