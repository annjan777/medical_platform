# CI/CD Deployment Guide

## GitHub Secrets Setup

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

### Database & Basic
- `SECRET_KEY`: Generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- `DATABASE_URL`: Your production database connection string
- `REDIS_URL`: Your Redis connection string

### Server Access
- `PRODUCTION_HOST`: Your DigitalOcean server IP
- `PRODUCTION_USER`: Server username (usually root or deploy)
- `PRODUCTION_SSH_KEY`: Your private SSH key (paste the entire key including -----BEGIN/END lines)

### Staging (optional)
- `STAGING_HOST`: Staging server IP
- `STAGING_USER`: Staging server username
- `STAGING_SSH_KEY`: Staging SSH key

### Notifications (optional)
- `SLACK_WEBHOOK`: Slack webhook URL for deployment notifications

## DigitalOcean Setup

### Option 1: DigitalOcean App Platform (Recommended)
1. Install `doctl`: `brew install doctl` or follow official docs
2. Authenticate: `doctl auth init`
3. Create app: `doctl apps create --spec .do/app.yaml`

### Option 2: Droplet Setup
1. Create Ubuntu 22.04 Droplet
2. SSH into server: `ssh root@your-server-ip`
3. Run setup script:

```bash
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib redis-server git

# Create app user
adduser deploy
usermod -aG sudo deploy

# Create app directory
mkdir -p /var/www/medical_platform
chown deploy:deploy /var/www/medical_platform

# Clone repository
cd /var/www/medical_platform
git clone https://github.com/your-username/medical_platform.git .

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup database
sudo -u postgres createdb medical_platform
sudo -u postgres createuser --interactive
```

### Systemd Services

Create `/etc/systemd/system/gunicorn.service`:
```ini
[Unit]
Description=gunicorn daemon
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/var/www/medical_platform
ExecStart=/var/www/medical_platform/venv/bin/gunicorn --workers 3 --bind unix:/var/www/medical_platform/gunicorn.sock config.wsgi:application

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/nginx.service` (if not exists):
```ini
[Unit]
Description=A high performance web server and a reverse proxy server
After=network.target

[Service]
Type=forking
PIDFile=/run/nginx.pid
ExecStartPre=/usr/sbin/nginx -t
ExecStart=/usr/sbin/nginx
ExecReload=/usr/sbin/nginx -s reload
ExecStop=/usr/sbin/nginx -s quit
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable services:
```bash
sudo systemctl enable gunicorn nginx
sudo systemctl start gunicorn nginx
```

## Deployment Workflow

### Automatic (GitHub Actions)
1. Push to `develop` → Deploys to staging
2. Push to `main` → Runs tests → Deploys to production

### Manual (SSH)
```bash
# Make deploy script executable
chmod +x deploy.sh

# Deploy to production
./deploy.sh
```

### Docker Deployment
```bash
# Build and run locally
docker-compose up --build

# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

## Environment Files

1. Copy `.env.example` to `.env`
2. Update values for your environment
3. Never commit `.env` to version control

## Health Checks

- Health endpoint: `GET /health/`
- Returns: `{"status": "healthy", "timestamp": "..."}`
- Monitored by: Nginx health check, GitHub Actions

## Rollback Strategy

If deployment fails:
1. GitHub Actions will stop on error
2. Manual rollback: `git checkout previous-commit-tag`
3. Database migrations are designed to be reversible

## Monitoring

### Application Monitoring
- Sentry for error tracking
- Django logging to `/var/log/medical_platform/`
- Nginx access logs

### Server Monitoring
- DigitalOcean monitoring dashboard
- Custom health checks via `/health/` endpoint

## Security Considerations

1. **SSH Keys**: Use key-based authentication only
2. **Firewall**: Configure UFW to allow only necessary ports
3. **SSL**: Use Let's Encrypt for HTTPS
4. **Environment Variables**: Never commit secrets
5. **Database**: Use strong passwords and limit access
6. **Backups**: Regular database and file backups

## SSL Certificate Setup

```bash
# Install Certbot
apt install certbot python3-certbot-nginx

# Get SSL certificate
certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal
crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Troubleshooting

### Common Issues
1. **Database connection**: Check DATABASE_URL format
2. **Static files**: Run `collectstatic` after deployment
3. **Permissions**: Ensure correct file ownership
4. **Port conflicts**: Check if ports 80/443 are available

### Logs
- Application: `tail -f /var/log/medical_platform/django.log`
- Nginx: `tail -f /var/log/nginx/error.log`
- Gunicorn: `journalctl -u gunicorn -f`

### Performance Tuning
- Adjust Gunicorn workers based on CPU cores
- Configure Nginx caching for static files
- Optimize database queries
- Use Redis for session storage
