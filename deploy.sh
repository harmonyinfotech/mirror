#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting deployment..."

# Update system
echo "📦 Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install dependencies
echo "📦 Installing system dependencies..."
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx

# Create project directory
echo "📁 Setting up project directory..."
sudo mkdir -p /var/www/mirror
sudo chown -R $USER:$USER /var/www/mirror

# Clone repository
echo "📥 Cloning repository..."
cd /var/www/mirror
git clone https://github.com/harmonyinfotech/mirror.git .

# Set up Python virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn

# Create logs directory
echo "📝 Setting up log directories..."
sudo mkdir -p /var/log/mirror
sudo chown -R $USER:$USER /var/log/mirror

# Set up systemd service
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/mirror.service << EOF
[Unit]
Description=mirror.is text sharing service
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=/var/www/mirror
Environment="PATH=/var/www/mirror/venv/bin"
ExecStart=/var/www/mirror/venv/bin/gunicorn -c gunicorn_config.py app:app

[Install]
WantedBy=multi-user.target
EOF

# Set up Nginx
echo "🌐 Configuring Nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/mirror
sudo ln -sf /etc/nginx/sites-available/mirror /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "🔍 Testing Nginx configuration..."
sudo nginx -t

# Start services
echo "🎬 Starting services..."
sudo systemctl daemon-reload
sudo systemctl start mirror
sudo systemctl enable mirror
sudo systemctl restart nginx

# Set up SSL (comment out if not ready for SSL)
echo "🔒 Setting up SSL certificate..."
sudo certbot --nginx -d mirror.is --non-interactive --agree-tos --email your@email.com

echo "✨ Deployment complete! Your application should be running at https://mirror.is"
echo "📝 Check logs with: sudo journalctl -u mirror"
echo "🔄 To restart the application: sudo systemctl restart mirror"
