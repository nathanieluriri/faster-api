#!/usr/bin/env bash
set -e

# ===== CONFIG (EDIT ONLY THESE) =====
DOMAIN_NAME="$1"
APP_PORT="$2"

# ===== VALIDATION =====
if [[ -z "$DOMAIN_NAME" || -z "$APP_PORT" ]]; then
  echo "Usage: $0 <domain_name> <app_port>"
  exit 1
fi

NGINX_AVAILABLE="/etc/nginx/sites-available/$DOMAIN_NAME"
NGINX_ENABLED="/etc/nginx/sites-enabled/$DOMAIN_NAME"

echo "🚀 Setting up Nginx + Let's Encrypt for:"
echo "   Domain: $DOMAIN_NAME"
echo "   Port:   $APP_PORT"
echo

# ===== INSTALL PACKAGES =====
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# ===== CREATE NGINX CONFIG =====
if [[ ! -f "$NGINX_AVAILABLE" ]]; then
sudo tee "$NGINX_AVAILABLE" > /dev/null <<EOF
server {
    server_name $DOMAIN_NAME;

    client_max_body_size 25m;

    proxy_read_timeout 180s;
    proxy_connect_timeout 30s;
    proxy_send_timeout 180s;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location = /health {
        proxy_pass http://127.0.0.1:$APP_PORT/health;
        proxy_set_header Host \$host;
    }

    listen 80;
    listen [::]:80;
}
EOF
else
  echo "⚠️ Nginx config already exists, skipping creation"
fi

# ===== ENABLE SITE =====
if [[ ! -L "$NGINX_ENABLED" ]]; then
  sudo ln -s "$NGINX_AVAILABLE" "$NGINX_ENABLED"
fi

# ===== REMOVE DEFAULT SITE (SAFE) =====
if [[ -L "/etc/nginx/sites-enabled/default" ]]; then
  sudo rm /etc/nginx/sites-enabled/default
fi

# ===== TEST & RELOAD NGINX =====
sudo nginx -t
sudo systemctl reload nginx

# ===== SSL CERTIFICATE =====
sudo certbot --nginx -d "$DOMAIN_NAME" --non-interactive --agree-tos -m admin@"$DOMAIN_NAME" --redirect

# ===== DONE =====
echo
echo "✅ Setup complete!"
echo "🌐 https://$DOMAIN_NAME"
