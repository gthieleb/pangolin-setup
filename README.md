# Pangolin Setup - Tailscale + Cloudflare DNS-01

Identity-aware VPN und Reverse Proxy auf Basis von WireGuard. Alternative zu Cloudflare Tunnels mit selbstgehosteter Kontrolle.

**Video-Referenz:** [Better Than Cloudflare Tunnels? - Pangolin Guide](https://www.youtube.com/watch?v=8VdwOL7nYkY) von Jim's Garage

---

## Architektur

```
┌─────────────────────────────────────────┐
│           INTERNET (Public)             │
│                                         │
│  Traefik-Public: PUBLIC_IP:443          │
│  (Services für Entwickler)              │
│  - Holt Config von Pangolin API         │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         TAILSCALE (Privat)              │
│                                         │
│  Traefik-Tailscale: TS_IP:443           │
│  (Dashboard nur für Admins)             │
│  - Statische Route zu Pangolin          │
│  - KEIN API-Zugriff                     │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│         DOCKER INTERNAL                 │
│                                         │
│  Pangolin:3000-3002                     │
│  - Dashboard API (3000)                 │
│  - Internal API (3001)                  │
│  - Web UI (3002)                        │
│  - KEINE Ports exposed                  │
│                                         │
│  Gerbil:3004                            │
│  - WireGuard VPN                        │
└─────────────────────────────────────────┘
```

### Sicherheitsmodell: Zero Trust

| Komponente | Zugriff | Begründung |
|------------|---------|------------|
| **Dashboard** | Tailscale only | Admin-Interface nur über VPN |
| **Services** | Public / Tailscale | Selektiv öffentlich machbar |
| **WireGuard** | Tailscale / Public | VPN-Tunnel |

---

## Schnellstart

### 1. Repository klonen

```bash
git clone https://github.com/gthieleb/pangolin-setup.git
cd pangolin-setup
```

### 2. Konfiguration anpassen

```bash
# .env erstellen
cp .env.example .env
# .env editieren und Cloudflare Token eintragen

# docker-compose.yml erstellen
cp docker-compose.yml.example docker-compose.yml
# IPs anpassen (Tailscale + Public)
```

### 3. Pangolin Config erstellen

```bash
# config/config.yml erstellen
mkdir -p config/letsencrypt config/traefik-tailscale/logs config/traefik-public/logs

# Server Secret generieren
openssl rand -hex 32
# In config/config.yml eintragen
```

### 4. Starten

```bash
docker compose up -d
```

---

## Konfiguration

### Dateien

| Datei | Zweck | Quelle |
|-------|-------|--------|
| `docker-compose.yml` | Services | Aus `.example` kopieren |
| `.env` | Secrets | Aus `.example` kopieren |
| `config/config.yml` | Pangolin | Siehe Dokumentation |
| `config/traefik-tailscale/` | Traefik Dashboard | Statische Routes |
| `config/traefik-public/` | Traefik Services | Mit Pangolin API |
| `config/letsencrypt/` | Zertifikate | Auto-generiert |

### Wichtige Variablen

In `docker-compose.yml`:

```yaml
# Tailscale IP (Dashboard)
ports:
  - DEINE_TAILSCALE_IP:443:443
  - DEINE_TAILSCALE_IP:80:80

# Public IP (Services) - optional
ports:
  - DEINE_PUBLIC_IP:443:443
  - DEINE_PUBLIC_IP:80:80
```

In `config/config.yml`:

```yaml
server:
  base_endpoint: "dashboard.apps.deine-domain.de"
  
app:
  dashboard_url: "https://dashboard.apps.deine-domain.de"
  base_domain: "apps.deine-domain.de"
```

---

## DNS-Konfiguration (Cloudflare)

### Tailscale-only (Initial)

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| A | `dashboard.apps` | `DEINE_TAILSCALE_IP` | 🚫 DNS only |
| A | `*.apps` | `DEINE_TAILSCALE_IP` | 🚫 DNS only |

### Public Services (optional)

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| A | `service1.apps` | `DEINE_PUBLIC_IP` | 🚫 DNS only |
| A | `service2.apps` | `DEINE_PUBLIC_IP` | 🚫 DNS only |

**Wichtig:** Proxy muss ausgeschaltet sein für DNS-01 Challenge!

---

## Cloudflare API Token

1. https://dash.cloudflare.com/profile/api-tokens
2. "Create Token" → "Custom token"
3. Berechtigungen:
   - Zone:Read
   - DNS:Edit
4. Zone Resources: Include - Specific zone - `deine-domain.de`

In `.env` eintragen:
```bash
CF_DNS_API_TOKEN=cfat_...
```

---

## Betrieb

### Start

```bash
docker compose up -d
```

### Logs

```bash
docker compose logs -f traefik-tailscale  # Dashboard
docker compose logs -f traefik-public     # Services
docker compose logs -f pangolin           # Pangolin
```

### Status

```bash
docker compose ps
```

---

## Erste Einrichtung

1. **Dashboard öffnen:** `https://dashboard.apps.deine-domain.de`
2. **Setup Token eingeben** (aus Logs: `docker compose logs pangolin | grep "Token:"`)
3. **Admin-Account erstellen**
4. **Organisation einrichten**
5. **Sites und Resources hinzufügen**

---

## Troubleshooting

### Port 443 belegt (Tailscale)

```bash
# Tailscale serve stoppen
sudo tailscale serve --https=443 off
```

### Zertifikat nicht erstellt

```bash
# Traefik Logs prüfen
docker compose logs traefik-tailscale | grep -i "acme\|certificate"

# acme.json prüfen
sudo cat config/letsencrypt/acme.json | python3 -m json.tool
```

### DNS-01 Challenge fehlschlägt

- Cloudflare API Token prüfen
- DNS-Propagation abwarten
- Resolvers: `1.1.1.1:53`, `1.0.0.1:53`

---

## Sicherheit

| Maßnahme | Status |
|----------|--------|
| Dashboard nur Tailscale | ✅ |
| Let's Encrypt TLS | ✅ |
| DNS-01 Challenge (kein Port 80 nötig) | ✅ |
| Pangolin keine exposed Ports | ✅ |
| UFW Firewall aktiv | ✅ |
| Cloudflare DNS | ✅ |
| SSO/OIDC möglich | ⬜ (optional) |
| CrowdSec | ⬜ (optional) |

## Integration API (OpenAPI MCP)

Pangolin bietet eine REST API zur Automatisierung. Diese kann als MCP Server für Hermes/Claude genutzt werden.

### Aktivierung

In `config/config.yml`:
```yaml
flags:
  enable_integration_api: true
```

### OpenAPI Spec

Die API Spec wird automatisch generiert und ist verfügbar unter:
- JSON: `http://pangolin:3003/v1/openapi.json`
- YAML: `http://pangolin:3003/v1/openapi.yaml`
- Swagger UI: `http://pangolin:3003/v1/docs`

### MCP Proxy

Ein MCP Proxy konvertiert die OpenAPI Spec in MCP Tools:

```bash
# MCP Proxy starten
docker compose -f docker-compose.mcp.yml up -d
```

### Hermes Agent Konfiguration

In `~/.hermes/config.yaml`:
```yaml
mcp_servers:
  pangolin:
    command: docker
    args:
      - exec
      - -i
      - pangolin-mcp
      - python
      - /app/mcp-proxy.py
    env:
      PANGOLIN_API_KEY: dein-api-key
```

### API Key erstellen

1. Dashboard öffnen: `https://dashboard.apps.deine-domain.de`
2. Organisation → API Keys
3. Neuer Key mit gewünschten Berechtigungen

---

- **Dokumentation:** https://docs.pangolin.net
- **GitHub:** https://github.com/fosrl/pangolin
- **Community:** https://discord.gg/pangolin
