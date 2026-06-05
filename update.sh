#!/bin/bash
# ================================================================
# StudioSowa — Mise à jour rapide après un git push
# Usage : ssh root@168.231.81.133 'bash /var/www/studiosowa/update.sh'
# ================================================================

cd /var/www/studiosowa
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --quiet
chown -R www-data:www-data /var/www/studiosowa
systemctl restart studiosowa
echo "✓ StudioSowa mis à jour et redémarré."
