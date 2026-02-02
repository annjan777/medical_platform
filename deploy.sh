#!/bin/bash

# Production deployment script for DigitalOcean
set -e

# Configuration
APP_NAME="medical-platform"
SERVER_USER="root"
SERVER_IP="your-server-ip"
APP_DIR="/var/www/$APP_NAME"
BACKUP_DIR="/var/backups/$APP_NAME"

echo "🚀 Starting deployment of $APP_NAME..."

# Create backup
echo "📦 Creating backup..."
ssh $SERVER_USER@$SERVER_IP "
    mkdir -p $BACKUP_DIR
    cd $APP_DIR
    tar -czf $BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S).tar.gz \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='venv' \
        --exclude='media' \
        .
"

# Deploy to production
echo "🔄 Deploying to production..."
ssh $SERVER_USER@$SERVER_IP "
    cd $APP_DIR
    
    # Pull latest code
    git pull origin main
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    pip install -r requirements.txt
    
    # Run database migrations
    python manage.py migrate
    
    # Collect static files
    python manage.py collectstatic --noinput
    
    # Restart services
    sudo systemctl reload gunicorn
    sudo systemctl reload nginx
    
    # Run health check
    curl -f http://localhost/health/ || exit 1
"

echo "✅ Deployment completed successfully!"

# Health check
echo "🏥 Running health check..."
sleep 5
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$SERVER_IP/health/)

if [ $HEALTH_STATUS -eq 200 ]; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed with status $HEALTH_STATUS"
    echo "🔄 Rolling back..."
    # Implement rollback logic here
    exit 1
fi

echo "🎉 Deployment is live and healthy!"
