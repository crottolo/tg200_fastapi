# Deployment Guide

## Configurazione Proxy e Reverse Proxy

L'applicazione è configurata per funzionare correttamente dietro proxy inversi (Nginx, Caddy, Coolify, etc).

### Middleware Configurati

1. **CORS Middleware** - Permette richieste da qualsiasi origine
2. **ProxyHeadersMiddleware** - Gestisce header X-Forwarded-*
3. **Uvicorn Proxy Headers** - Trust headers da qualsiasi IP

### Header Supportati

```
X-Forwarded-For: IP originale del client
X-Forwarded-Proto: http/https
X-Forwarded-Host: hostname originale
```

### Configurazione Nginx (Esempio)

```nginx
location / {
    proxy_pass http://localhost:8000;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header Host $host;
}
```

### Coolify

Coolify configura automaticamente il reverse proxy. L'app è pronta all'uso.

## Deploy su Coolify con Nixpacks

Coolify usa **Nixpacks** per buildare automaticamente l'app FastAPI. Nixpacks rileva il progetto Python e costruisce il container automaticamente.

### 1. Crea Nuova Application

1. In Coolify → **Projects** → seleziona il tuo progetto
2. Click **+ New Resource**
3. Seleziona **Application** (NON Docker Compose)
4. Scegli **Git Repository**
5. Inserisci: `https://github.com/crottolo/tg200_fastapi`
6. Branch: `main`

### 2. Configura Build Pack

Coolify rileva automaticamente **Nixpacks** grazie al file `nixpacks.toml`.

- ✅ **Build Pack**: Nixpacks (auto-detected)
- ✅ **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 8000` (da nixpacks.toml)

### 3. Configura Porta (IMPORTANTE!)

**In Coolify UI → Network Section:**
- **Ports Exposes**: `8000` (⚠️ IMPORTANTE: FastAPI default port)

Se non configuri la porta corretta, l'app non sarà raggiungibile!

### 4. Configura Environment Variables

Vai alla tab **Environment Variables** e aggiungi **TUTTE** le variabili:

```bash
# TG200 Gateway Configuration (OBBLIGATORIE)
TG200_HOST=37.117.57.200
TG200_PORT=5038
TG200_USERNAME=apiuser
TG200_PASSWORD=apipass
TG200_DEFAULT_SPAN=2

# API Security (⚠️ CAMBIA QUESTO!)
API_BEARER_TOKEN=your-secret-token-here

# Webhook Configuration
WEBHOOK_URL=https://your-webhook-endpoint.com/webhook
WEBHOOK_ENABLED=true

# Webhook Advanced (OPZIONALI)
WEBHOOK_TIMEOUT=5.0
WEBHOOK_RETRY=0
WEBHOOK_SEND_ALL_EVENTS=true
WEBHOOK_SEND_KEEPALIVE=false
```

### 5. Deploy

Click **Deploy** - Coolify:
1. Clona il repository da GitHub
2. Nixpacks builda automaticamente l'immagine
3. Avvia il container sulla porta 8000
4. Configura il reverse proxy automaticamente
5. L'app è live!

### 6. Verifica Deploy

Dopo il deploy, controlla i **Logs** in Coolify:
```
AMI LISTENER STARTED - Logging all events from TG200
AMI KEEPALIVE ENABLED - Ping every 25 seconds
```

Testa l'endpoint:
```bash
curl https://your-domain.com/
# Output: {"status":"ok","message":"TG200 FastAPI Gateway"}
```

### Troubleshooting Deploy

**Build fallisce**:
- Verifica che `requirements.txt` sia committato
- Controlla i logs di build in Coolify

**Container non parte**:
- Verifica le variabili d'ambiente obbligatorie
- Controlla connectivity verso TG200_HOST:TG200_PORT

**AMI non si connette**:
- Verifica TG200_HOST, TG200_USERNAME, TG200_PASSWORD
- Controlla firewall tra Coolify server e TG200

## AMI Event Listener

L'applicazione include un listener AMI persistente che:
- Si connette automaticamente al TG200 all'avvio
- Rimane in ascolto per eventi (ReceivedSMS, etc)
- Logga tutti gli eventi ricevuti
- Invia webhook quando riceve SMS
- Si riconnette automaticamente in caso di disconnessione

### Eventi Supportati

**ReceivedSMS** - SMS in arrivo
```json
{
  "event": "ReceivedSMS",
  "gsmspan": "2",
  "sender": "+393935873723",
  "recvtime": "2025-11-22 18:00:00",
  "content": "Testo SMS",
  "index": "0",
  "total": "1"
}
```

### Webhook Notification

Quando riceve un SMS, invia POST al webhook configurato:

```json
{
  "phone": "+393935873723",
  "message": "Testo SMS",
  "timestamp": "2025-11-22T18:00:00",
  "span": "2",
  "smsc": "+393500000000",
  "multipart": {
    "index": "0",
    "total": "1",
    "id": ""
  }
}
```

## Test API in Produzione

```bash
# Health check
curl https://your-domain.com/

# Status (richiede auth)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-domain.com/status

# Invia SMS
curl -X POST https://your-domain.com/sms/send \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+393935873723",
    "message": "Test",
    "span": "2"
  }'
```
