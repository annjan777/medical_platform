#!/bin/bash

# AWS EC2 Deployment Script for Medical Platform
# Usage: ./deploy-aws.sh

set -e

echo "🚀 Starting AWS Deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
echo "🐍 Installing Python and dependencies..."
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib libpq-dev python3-dev build-essential nginx

# Setup PostgreSQL
echo "🗄️ Setting up PostgreSQL..."
sudo -u postgres createdb medical_platform || echo "Database already exists"
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Clone/Pull code
echo "📥 Setting up application code..."
cd /var/www/
sudo rm -rf medical_platform || true
sudo git clone <your-repo-url> medical_platform
cd medical_platform

# Setup virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements-prod.txt

# Environment setup
echo "⚙️ Setting up environment..."
cp .env.production .env
sed -i "s/your-domain.com/$(hostname)/g" .env
sed -i "s/your-database-password/$(openssl rand -base64 32)/g" .env
sed -i "s/your-very-secret-key-here-change-this-in-production/$(openssl rand -base64 64)/g" .env

# Database migrations
echo "🗄️ Running database migrations..."
export $(cat .env | xargs)
python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser (optional)
echo "👤 Creating superuser (optional)..."
# python manage.py createsuperuser

# Setup Nginx
echo "🌐 Setting up Nginx..."
sudo tee /etc/nginx/sites-available/medical_platform << 'EOF'
server {
    listen 80;
    server_name 13.204.125.52 your-domain.com www.your-domain.com;

    location /static/ {
        alias /var/www/medical_platform/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /var/www/medical_platform/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/medical_platform /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# Setup Gunicorn service
echo "🚀 Setting up Gunicorn service..."
sudo tee /etc/systemd/system/medical-platform.service << 'EOF'
[Unit]
Description=Medical Platform Django Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/medical_platform
ExecStart=/var/www/medical_platform/venv/bin/gunicorn config.wsgi:application --workers 3 --bind unix:/var/www/medical_platform/medical_platform.sock

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable medical-platform
sudo systemctl start medical-platform

# Setup SSL (optional with Let's Encrypt)
echo "🔒 Setting up SSL (optional)..."
# sudo apt install certbot python3-certbot-nginx
# sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Final setup
echo "🔧 Setting permissions..."
sudo chown -R www-data:www-data /var/www/medical_platform
sudo chmod -R 755 /var/www/medical_platform

echo "✅ Deployment complete!"
echo "🌐 Your application should be available at: http://13.204.125.52"
echo "🔧 Don't forget to:"
echo "   1. Update .env with your actual domain and passwords"
echo "   2. Configure DNS to point your-domain.com to 13.204.125.52"
echo "   3. Set up SSL certificate"
echo "   4. Configure AWS Security Groups to allow HTTP/HTTPS traffic"
