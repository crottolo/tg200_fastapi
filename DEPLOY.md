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
    proxy_pass http://localhost:3000;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header Host $host;
}
```

### Coolify

Coolify configura automaticamente il reverse proxy. L'app è pronta all'uso.

## Deploy su Coolify - Step by Step

### Metodo Consigliato: Docker Compose

Il progetto include un `docker-compose.yml` che Coolify rileva automaticamente. Questo è il metodo **più semplice** perché:
- ✅ Coolify rileva automaticamente tutte le variabili d'ambiente
- ✅ Valori di default già configurati
- ✅ Variabili obbligatorie marcate con `:?`
- ✅ Devi modificare solo `API_BEARER_TOKEN` e `WEBHOOK_URL`

### 1. Crea Nuova Resource

1. In Coolify, vai su **Projects** → seleziona il tuo progetto
2. Click su **+ New Resource**
3. Seleziona **Docker Compose** (NON "Docker")
4. Scegli **Git Repository**
5. Inserisci URL del repository
6. Seleziona branch (main/master)

### 2. Coolify Rileva le Variabili Automaticamente

Dopo aver selezionato il repository, Coolify:
1. Legge il `docker-compose.yml`
2. Rileva tutte le variabili `${VARIABLE_NAME}`
3. Le mostra nella tab **Environment Variables**

### 3. Configura Solo le Variabili Obbligatorie

Coolify ti chiederà di impostare solo le variabili **OBBLIGATORIE** (quelle con `:?`):

**⚠️ DA CONFIGURARE:**
```bash
TG200_HOST=37.117.57.200          # IP del tuo TG200
TG200_USERNAME=apiuser             # Username AMI
TG200_PASSWORD=apipass             # Password AMI
API_BEARER_TOKEN=YOUR-SECRET-TOKEN # ⚠️ CAMBIA QUESTO!
WEBHOOK_URL=https://your-webhook.com/endpoint  # URL webhook destinazione
```

**✅ GIÀ CONFIGURATE (default nel compose file):**
```bash
TG200_PORT=5038                    # Porta AMI (default)
TG200_DEFAULT_SPAN=2               # Span GSM di default
WEBHOOK_ENABLED=true               # Webhook abilitato
WEBHOOK_TIMEOUT=5.0                # Timeout 5 secondi
WEBHOOK_RETRY=0                    # Nessun retry
WEBHOOK_SEND_ALL_EVENTS=true      # Invia tutti gli eventi
WEBHOOK_SEND_KEEPALIVE=false      # NON inviare Ping/Pong (consigliato)
```

**💡 Tip**: Se vuoi cambiare i valori di default, puoi modificarli nell'UI di Coolify.

### 4. Deploy

Click **Deploy** - Coolify:
1. Clona il repository
2. Builda l'immagine Docker
3. Avvia il container
4. Configura il reverse proxy automaticamente

### 5. Verifica

Dopo il deploy:
1. Controlla i **Logs** in Coolify
2. Cerca `AMI LISTENER STARTED - Logging all events from TG200`
3. Ogni 25 secondi: `Keepalive ping sent`
4. Testa l'endpoint: `curl https://your-domain.com/`

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

## Variabili d'Ambiente per Coolify

### Come Configurare in Coolify

1. Vai alla tua **Resource** (Application) in Coolify
2. Click su tab **"Environment Variables"**
3. Click **"Add Variable"** per ogni variabile
4. Copia/incolla le variabili qui sotto
5. **⚠️ IMPORTANTE: Modifica `API_BEARER_TOKEN` con un token sicuro!**

### Variabili OBBLIGATORIE

```bash
# TG200 Gateway Configuration
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
```

### Variabili OPZIONALI (Configurazione Avanzata Webhook)

```bash
# Webhook Timeout & Retry
WEBHOOK_TIMEOUT=5.0              # Timeout in secondi (default: 5.0)
WEBHOOK_RETRY=0                  # Numero di retry su errore (default: 0, max: 3)

# Webhook Event Filtering
WEBHOOK_SEND_ALL_EVENTS=true    # Invia TUTTI gli eventi AMI al webhook (default: true)
WEBHOOK_SEND_KEEPALIVE=false    # Invia eventi Ping/Pong keepalive (default: true, consigliato: false)
```

### Note sulle Variabili

- **WEBHOOK_SEND_KEEPALIVE**: Imposta `false` per evitare spam di Ping/Pong ogni 25 secondi
- **WEBHOOK_RETRY**: Utile se il tuo webhook è instabile (0 = nessun retry)
- **WEBHOOK_TIMEOUT**: Evita che webhook lenti blocchino l'app
- Le variabili in Coolify sono sicure e non vengono salvate nel repository Git

## Test in Produzione

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
