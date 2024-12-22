bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
accesslog = "/var/log/mirror-is/access.log"
errorlog = "/var/log/mirror-is/error.log"
loglevel = "info"

# Process naming
proc_name = "mirror-is"

# SSL (uncomment if using SSL directly with gunicorn)
# keyfile = "/etc/letsencrypt/live/mirror.is/privkey.pem"
# certfile = "/etc/letsencrypt/live/mirror.is/fullchain.pem"
