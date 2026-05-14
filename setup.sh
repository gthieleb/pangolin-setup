#!/bin/bash
set -e

echo "=== Pangolin Setup ==="
echo ""

# Prüfe ob .env existiert
if [ ! -f .env ]; then
    echo "Erstelle .env aus Template..."
    cp .env.example .env
    echo "⚠️  Bitte .env editieren und Cloudflare Token eintragen!"
    exit 1
fi

# Prüfe ob docker-compose.yml existiert
if [ ! -f docker-compose.yml ]; then
    echo "Erstelle docker-compose.yml aus Template..."
    cp docker-compose.yml.example docker-compose.yml
    echo "⚠️  Bitte docker-compose.yml editieren und IPs anpassen!"
    exit 1
fi

# Erstelle Verzeichnisse
mkdir -p config/letsencrypt
mkdir -p config/traefik-tailscale/logs
mkdir -p config/traefik-public/logs

# Kopiere Beispiel-Configs wenn nicht vorhanden
if [ ! -f config/config.yml ]; then
    echo "Erstelle config/config.yml aus Template..."
    cp examples/config.yml.example config/config.yml
    echo "⚠️  Bitte config/config.yml editieren:"
    echo "   - Server Secret generieren: openssl rand -hex 32"
    echo "   - Domain anpassen"
    exit 1
fi

# Prüfe acme.json Berechtigungen
if [ -f config/letsencrypt/acme.json ]; then
    chmod 600 config/letsencrypt/acme.json
fi

echo "✅ Setup complete!"
echo ""
echo "Starte mit: docker compose up -d"
