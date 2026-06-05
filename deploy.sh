#!/bin/bash
# ================================================================
# StudioSowa — Script de déploiement VPS Hostinger
# Serveur : Ubuntu 24.04 LTS — 168.231.81.133
# Usage : ssh root@168.231.81.133 puis coller ce script
# ================================================================

set -e  # Arrêter en cas d'erreur

echo "══════════════════════════════════════════"
echo "  STUDIOSOWA — Déploiement VPS"
echo "══════════════════════════════════════════"

# ── 1. Mise à jour système ──
echo "[1/8] Mise à jour système..."
apt update && apt upgrade -y

# ── 2. Installation des paquets ──
echo "[2/8] Installation Python, Nginx, Certbot, Git..."
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git ufw

# ── 3. Pare-feu ──
echo "[3/8] Configuration du pare-feu..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# ── 4. Cloner le projet ──
echo "[4/8] Clonage du projet..."
mkdir -p /var/www
if [ -d "/var/www/studiosowa" ]; then
  echo "  → Dossier existant, pull..."
  cd /var/www/studiosowa && git pull
else
  git clone https://github.com/pacadiit/studiosowa.git /var/www/studiosowa
fi
cd /var/www/studiosowa

# ── 5. Environnement Python ──
echo "[5/8] Création environnement Python + dépendances..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# ── 6. Fichier .env ──
echo "[6/8] Configuration .env..."
if [ ! -f ".env" ]; then
cat > .env << 'ENVEOF'
SECRET_KEY=CHANGE_ME_WITH_A_LONG_RANDOM_STRING
ADMIN_PASSWORD=sowa2024!

# Base de données (SQLite par défaut)
DATABASE_URL=

# Cloudinary
CLOUDINARY_CLOUD_NAME=votre-cloud-name
CLOUDINARY_API_KEY=123456789012345
CLOUDINARY_API_SECRET=votre-api-secret

# Email Hostinger
MAIL_SERVER=smtp.hostinger.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=contact@studiosowa.com
MAIL_PASSWORD=Architecte@59390
MAIL_RECIPIENT=contact@studiosowa.com
ENVEOF
echo "  → .env créé. PENSE À CHANGER SECRET_KEY !"
else
  echo "  → .env existe déjà, pas touché."
fi

# Créer le dossier uploads
mkdir -p static/uploads

# ── 7. Service systemd (Gunicorn) ──
echo "[7/8] Configuration du service Gunicorn..."
cat > /etc/systemd/system/studiosowa.service << 'EOF'
[Unit]
Description=StudioSowa Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/studiosowa
Environment="PATH=/var/www/studiosowa/venv/bin"
EnvironmentFile=/var/www/studiosowa/.env
ExecStart=/var/www/studiosowa/venv/bin/gunicorn --workers 2 --bind unix:/var/www/studiosowa/studiosowa.sock --timeout 120 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Permissions
chown -R www-data:www-data /var/www/studiosowa

# Démarrer le service
systemctl daemon-reload
systemctl enable studiosowa
systemctl restart studiosowa
echo "  → Gunicorn démarré."

# ── 8. Configuration Nginx ──
echo "[8/8] Configuration Nginx..."
cat > /etc/nginx/sites-available/studiosowa << 'EOF'
server {
    listen 80;
    server_name studiosowa.com www.studiosowa.com;

    # Rediriger www vers non-www
    if ($host = www.studiosowa.com) {
        return 301 https://studiosowa.com$request_uri;
    }

    location / {
        proxy_pass http://unix:/var/www/studiosowa/studiosowa.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Fichiers statiques — servis directement par Nginx (rapide)
    location /static/ {
        alias /var/www/studiosowa/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Taille max upload images
    client_max_body_size 20M;
}
EOF

# Activer le site
ln -sf /etc/nginx/sites-available/studiosowa /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Tester et redémarrer Nginx
nginx -t && systemctl restart nginx

echo ""
echo "══════════════════════════════════════════"
echo "  DÉPLOIEMENT TERMINÉ !"
echo "══════════════════════════════════════════"
echo ""
echo "  Le site tourne sur http://168.231.81.133"
echo ""
echo "  PROCHAINES ÉTAPES :"
echo "  1. Changer le DNS : A record @ → 168.231.81.133"
echo "  2. Puis lancer le SSL :"
echo "     certbot --nginx -d studiosowa.com -d www.studiosowa.com"
echo "  3. Modifier SECRET_KEY dans /var/www/studiosowa/.env"
echo ""
