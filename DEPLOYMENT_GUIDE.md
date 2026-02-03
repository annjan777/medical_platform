# Medical Platform Deployment Guide

## Quick Setup

### 1. Install Dependencies

**For Production:**
```bash
pip install -r requirements-prod.txt
```

**For Development:**
```bash
pip install -r requirements-dev.txt
```

### 2. Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=medical_platform
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis (for caching/background tasks)
REDIS_URL=redis://localhost:6379/0

# Sentry (for error tracking)
SENTRY_DSN=your-sentry-dsn-here
```

### 3. Database Setup

```bash
# Create database
createdb medical_platform

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 4. Start Server

**Development:**
```bash
python manage.py runserver 0.0.0.0:8000
```

**Production (with Gunicorn):**
```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## Production Deployment

### Using Gunicorn + Nginx

1. **Install Gunicorn:**
   ```bash
   pip install gunicorn
   ```

2. **Create Gunicorn service file:**
   ```bash
   sudo nano /etc/systemd/system/medical-platform.service
   ```

3. **Service file content:**
   ```ini
   [Unit]
   Description=Medical Platform Django Application
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/medical_platform
   ExecStart=/path/to/venv/bin/gunicorn config.wsgi:application --workers 3 --bind unix:/path/to/medical_platform/medical_platform.sock

   [Install]
   WantedBy=multi-user.target
   ```

4. **Start and enable service:**
   ```bash
   sudo systemctl start medical-platform
   sudo systemctl enable medical-platform
   ```

### Using Docker

1. **Create Dockerfile:**
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   COPY requirements-prod.txt .
   RUN pip install -r requirements-prod.txt

   COPY . .

   EXPOSE 8000

   CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
   ```

2. **Build and run:**
   ```bash
   docker build -t medical-platform .
   docker run -p 8000:8000 medical-platform
   ```

## Environment-Specific Settings

### Development
- Use `requirements-dev.txt`
- Set `DEBUG=True`
- Use SQLite database
- Enable Django Debug Toolbar

### Production
- Use `requirements-prod.txt`
- Set `DEBUG=False`
- Use PostgreSQL database
- Configure proper logging
- Use Redis for caching
- Set up static file serving

## Common Issues

### 1. ModuleNotFoundError: No module named 'django'
```bash
# Make sure you're in the virtual environment
source venv/bin/activate
pip install -r requirements-prod.txt
```

### 2. Database connection errors
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database exists
psql -l
```

### 3. Static files not loading
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check STATIC_ROOT in settings.py
```

### 4. Permission errors
```bash
# Fix file permissions
sudo chown -R www-data:www-data /path/to/medical_platform
sudo chmod -R 755 /path/to/medical_platform
```

## Monitoring

### Health Check Endpoint
Add to `urls.py`:
```python
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({'status': 'healthy'})

urlpatterns = [
    path('health/', health_check, name='health_check'),
    # ... other urls
]
```

### Logging
Configure in `settings.py`:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Security

1. **Update SECRET_KEY**: Use a strong, unique secret key
2. **HTTPS**: Enable SSL/TLS in production
3. **Firewall**: Configure proper firewall rules
4. **Regular Updates**: Keep dependencies updated
5. **Backups**: Regular database backups
