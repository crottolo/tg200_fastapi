"""
Uvicorn configuration for production deployment
Use with: uvicorn main:app --config uvicorn_config.py
"""

# Bind to all interfaces
bind = "0.0.0.0:3000"

# Workers (adjust based on CPU cores)
workers = 1

# Trust proxy headers from any IP (for Coolify/Nginx/etc)
proxy_headers = True
forwarded_allow_ips = "*"

# Logging
log_level = "info"
access_log = True

# Timeouts
timeout_keep_alive = 75
