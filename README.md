# Pangolin Installation - Glue-IT

## Überblick

Identity-aware VPN und Reverse Proxy auf Basis von WireGuard. Alternative zu Cloudflare Tunnels mit selbstgehosteter Kontrolle.

**Video-Referenz:** [Better Than Cloudflare Tunnels? - Pangolin Guide](https://www.youtube.com/watch?v=8VdwOL7nYkY) von Jim's Garage

---

## Architektur

```
┌─────────────────────────────────────────┐
│           INTERNET (Public)             │
│         46.62.129.50 (blockiert)        │
│              durch UFW                  │
└─────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────┐
│           TAILSCALE NETWORK             │
│         100.108.41.111 (erlaubt)        │
│                                         │
│   ┌─────────┐    ┌─────────┐           │
│   │ Dashboard│    │  Apps   │           │
│   │ :443    │    │ :443    │           │
│   │ (Admin) │    │ (Public)│           │
│   └─────────┘    └─────────┘           │
│        │              │                 │
│   ┌─────────────────────────────────┐   │
│   │      Pangolin + Traefik         │   │
│   │      (100.108.41.111:443)       │   │
│   └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Sicherheitsmodell: Zero Trust

| Komponente | Zugriff | Begründung |
|------------|---------|------------|
| **Dashboard** | Tailscale only | Admin-Interface nur über VPN |
| **Apps** | Tailscale / Public* | Selektiv öffentlich machbar |
| **WireGuard** | Tailscale only | VPN-Tunnel geschützt |

*Apps können später über separate Public-IP oder Cloudflare Tunnel exponiert werden, ohne das Dashboard zu gefährden.

---

## Installation

### Voraussetzungen

- Linux Server mit root-Zugriff
- Docker & Docker Compose
- Domain (hier: `apps.glue-it.de`)
- Cloudflare Account mit API Token
- Tailscale auf dem Server

### DNS-Konfiguration (Cloudflare)

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| A | `dashboard.apps` | `100.108.41.111` | 🚫 DNS only (grau) |
| A | `*.apps` | `100.108.41.111` | 🚫 DNS only (grau) |

**Wichtig:** Proxy muss ausgeschaltet sein für DNS-01 Challenge!

### Cloudflare API Token

1. https://dash.cloudflare.com/profile/api-tokens
2. "Create Token" → "Custom token"
3. Berechtigungen:
   - Zone:Read
   - DNS:Edit
4. Zone Resources: Include - Specific zone - `glue-it.de`

Token in `.env` eintragen:
```bash
CF_DNS_API_TOKEN=cfat_...
```

---

## Konfiguration

### Dateien

| Datei | Zweck |
|-------|-------|
| `docker-compose.yml` | Tailscale-only Betrieb |
| `docker-compose.public.yml` | Public Access (optional) |
| `config/config.yml` | Pangolin Konfiguration |
| `config/traefik/traefik_config.yml` | Traefik + Let's Encrypt |
| `config/traefik/dynamic_config.yml` | TLS-Optionen |
| `.env` | Cloudflare Credentials |

### Let's Encrypt DNS-01 Challenge

Traefik ist für Cloudflare DNS-01 konfiguriert:

```yaml
certificatesResolvers:
  letsencrypt:
    acme:
      dnsChallenge:
        provider: cloudflare
      email: "info@thielebein.net"
      storage: "/letsencrypt/acme.json"
```

---

## Betrieb

### Start (Tailscale-only)

```bash
cd /opt/pangolin
docker compose up -d
```

### Logs

```bash
docker compose logs -f traefik   # Traefik
docker compose logs -f pangolin  # Pangolin
docker compose logs -f gerbil    # WireGuard
```

### Status

```bash
docker compose ps
```

---

## Erste Einrichtung

1. **Dashboard öffnen:** `https://dashboard.apps.glue-it.de`
2. **Setup Token eingeben** (aus Logs: `docker compose logs pangolin | grep "Token:"`)
3. **Admin-Account erstellen**
4. **Organisation einrichten**
5. **Sites und Resources hinzufügen**

---

## Public Access (später)

Wenn Apps für Entwickler öffentlich erreichbar sein sollen:

### Option 1: Public IP

```bash
# Firewall öffnen
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp

# Public Compose verwenden
docker compose -f docker-compose.public.yml up -d
```

DNS auf Public IP umstellen:
| Type | Name | Target |
|------|------|--------|
| A | `dashboard.apps` | `46.62.129.50` |
| A | `*.apps` | `46.62.129.50` |

### Option 2: Cloudflare Tunnel

Dashboard bleibt auf Tailscale, einzelne Apps über Cloudflare Tunnel.

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
docker compose logs traefik | grep -i "acme\|certificate"

# acme.json prüfen
cat config/letsencrypt/acme.json | jq
```

### DNS-01 Challenge fehlschlägt

- Cloudflare API Token prüfen
- DNS-Propagation abwarten (`delayBeforeCheck: 10`)
- Resolvers: `1.1.1.1:53`, `1.0.0.1:53`

---

## Sicherheit

| Maßnahme | Status |
|----------|--------|
| Dashboard nur Tailscale | ✅ |
| Let's Encrypt TLS | ✅ |
| DNS-01 Challenge (kein Port 80 nötig) | ✅ |
| UFW Firewall aktiv | ✅ |
| Cloudflare DNS | ✅ |
| SSO/OIDC möglich | ⬜ (optional) |
| CrowdSec | ⬜ (optional) |

---

## Ressourcen

- **Dokumentation:** https://docs.pangolin.net
- **GitHub:** https://github.com/fosrl/pangolin
- **Community:** https://discord.gg/pangolin

---

## Tailscale IP

- Server: `100.108.41.111`
- Exit Node: `100.89.128.1/24:51820`
