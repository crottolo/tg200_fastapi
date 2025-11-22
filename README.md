# TG200 FastAPI Gateway

API REST per gestire SMS tramite gateway Yeastar TG200.

## Funzionalità

- ✅ Invio SMS tramite API REST
- ✅ Verifica stato connessione TG200
- ✅ Autenticazione con Bearer token
- ✅ Webhook per messaggi in entrata
- ✅ Documentazione API automatica (Swagger)

## Installazione

1. Clona il repository e crea l'ambiente virtuale:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

3. Configura le variabili d'ambiente:
```bash
cp .env.example .env
# Modifica .env con i tuoi parametri
```

## Configurazione

Modifica il file `.env`:

```bash
# Connessione TG200
TG200_HOST=37.117.57.200
TG200_PORT=5038
TG200_USERNAME=apiuser
TG200_PASSWORD=apipass
TG200_DEFAULT_SPAN=2

# API
API_BEARER_TOKEN=your-secret-token-here
WEBHOOK_URL=http://localhost:8000/webhook/incoming
```

## Avvio

### Modalità Development
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Modalità Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Deploy su Coolify

Questo progetto è configurato per il deployment automatico su Coolify.

### Opzione 1: Deploy Automatico con Nixpacks (Raccomandato)

1. **Pusha il codice su GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Configura su Coolify**
   - Vai alla dashboard di Coolify
   - Crea una nuova applicazione
   - Seleziona "GitHub" come source
   - Scegli il repository
   - Coolify rileverà automaticamente `nixpacks.toml`
   - Porta rilevata automaticamente: **3000**

3. **Configura le variabili d'ambiente**

   Nella sezione "Environment Variables" di Coolify, aggiungi:
   ```
   TG200_HOST=37.117.57.200
   TG200_PORT=5038
   TG200_USERNAME=apiuser
   TG200_PASSWORD=apipass
   TG200_DEFAULT_SPAN=2
   API_BEARER_TOKEN=your-production-token-here
   WEBHOOK_URL=https://your-domain.com/webhook/incoming
   ```

4. **Deploy**
   - Clicca "Deploy"
   - Coolify builderà e deployerà automaticamente
   - Deploy automatici ad ogni push su main

### Opzione 2: Deploy con Dockerfile

Se preferisci usare il Dockerfile:

1. Nella dashboard Coolify, seleziona "Dockerfile" come build pack
2. Il file `Dockerfile` verrà usato automaticamente
3. La porta 3000 è già configurata nel Dockerfile

### Opzione 3: Build Locale e Push Docker Image

```bash
# Build immagine
docker build -t tg200-fastapi:latest .

# Test locale
docker run -p 3000:3000 --env-file .env tg200-fastapi:latest

# Push su registry e deploy da Coolify
```

### Verifica Deploy

Dopo il deployment, verifica che l'app funzioni:

```bash
# Health check
curl https://your-domain.com/

# Verifica stato (con token)
curl -H "Authorization: Bearer your-token" https://your-domain.com/status
```

### Note Importanti per Coolify

- ✅ Porta configurata: **3000** (default Coolify)
- ✅ Health check configurato nel Dockerfile
- ✅ Auto-deploy da GitHub abilitato
- ✅ **Proxy headers**: Configurato per Nginx/Reverse Proxy
- ✅ **CORS**: Abilitato per tutte le origini
- ✅ **Forwarded IPs**: Accetta connessioni da qualsiasi proxy
- ⚠️ Assicurati che il TG200 (37.117.57.200:5038) sia accessibile dal server Coolify
- 🔒 Usa sempre HTTPS in produzione
- 🔑 Cambia `API_BEARER_TOKEN` con un valore sicuro

## Utilizzo API

### 1. Health Check
```bash
curl http://localhost:8000/
```

### 2. Verifica Stato TG200
```bash
curl -H "Authorization: Bearer your-secret-token-here" \
  http://localhost:8000/status
```

### 3. Invio SMS

**Invio semplice** (SMS ID auto-generato):
```bash
curl -X POST http://localhost:8000/sms/send \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+393935873723",
    "message": "Test message",
    "span": "2"
  }'
```

**Invio con SMS ID personalizzato** (utile per tracking):
```bash
curl -X POST http://localhost:8000/sms/send \
  -H "Authorization: Bearer your-secret-token-here" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+393935873723",
    "message": "Order confirmation #12345",
    "span": "2",
    "sms_id": "order-12345"
  }'
```

Response:
```json
{
  "success": true,
  "message": "SMS sent successfully to +393935873723",
  "sms_id": "order-12345"
}
```

### 4. Test Webhook
```bash
curl -X POST http://localhost:8000/webhook/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+393935873723",
    "message": "Incoming SMS",
    "timestamp": "2025-11-22T17:30:00",
    "span": "2"
  }'
```

## Documentazione Interattiva

Una volta avviato il server, la documentazione interattiva è disponibile:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Esempi

Nella cartella `examples/` trovi:
- `send_sms.json` - Esempio payload per invio SMS (sms_id auto-generato)
- `send_sms_with_id.json` - Esempio payload con SMS ID personalizzato
- `incoming_webhook.json` - Esempio payload webhook in entrata
- `test_requests.sh` - Script per testare tutti gli endpoint

## Script Legacy

Il file `tg200_sms_sender.py` è lo script originale standalone per testare la connessione TCP al TG200:

```bash
# Modalità interattiva
python tg200_sms_sender.py

# Invio rapido
python tg200_sms_sender.py "+393935873723" "Test message" 2
```

## Note Tecniche

### Protocollo AMI
Il TG200 utilizza il protocollo AMI (Asterisk Manager Interface) su porta 5038.

Formato comando SMS:
```
Action: smscommand
command: gsm send sms {span} {phone} "{message}" {id}
```

### Span Disponibili
Sul TG200 configurato sono disponibili solo gli span 2 e 3 (nessun span 1).

### SMS ID Personalizzato
Il campo opzionale `sms_id` permette di tracciare l'origine del messaggio:

**Casi d'uso:**
- **E-commerce**: Collegare SMS a ordini specifici (`order-12345`)
- **Notifiche**: Identificare il tipo di alert (`payment-notification-789`)
- **Tracking**: Correlazione con sistemi esterni (`crm-lead-456`)
- **Debugging**: Facilitare il troubleshooting

**Comportamento:**
- Se non fornito → auto-generato (UUID a 8 caratteri)
- Se fornito → usato direttamente (max 50 caratteri)
- Sempre restituito nella response per conferma

## Struttura Progetto

```
tg200_fastapi/
├── app/
│   ├── api/
│   │   └── auth.py          # Autenticazione Bearer
│   ├── models/
│   │   └── schemas.py       # Modelli Pydantic
│   ├── services/
│   │   └── tg200_service.py # Comunicazione TCP/AMI
│   └── config.py            # Configurazione
├── examples/                # File di esempio
├── main.py                  # FastAPI application
├── tg200_sms_sender.py     # Script legacy standalone
├── requirements.txt         # Dipendenze Python
└── .env                     # Configurazione (non committare!)
```

## Sviluppo

Per lo sviluppo locale:
1. Modifica il codice
2. Il server si riavvierà automaticamente (modalità `--reload`)
3. Testa con gli script in `examples/`

## Licenza

Questo progetto è per uso interno.
