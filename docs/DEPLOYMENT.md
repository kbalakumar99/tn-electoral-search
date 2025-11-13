# Deployment Guide

## Local Development

### Prerequisites
- Python 3.8+
- SQLite 3.35+ (for FTS5 support)

### Setup
```bash
# Clone and setup
git clone https://github.com/[username]/tn-electoral-search.git
cd tn-electoral-search

# Install dependencies
make install

# Initialize database
make init-db

# Run development server
make dev
```

## Docker Deployment

### Build and Run
```bash
# Build image
make docker-build

# Run with Docker Compose
make docker-run

# View logs
docker-compose logs -f

# Stop
make docker-stop
```

### Environment Variables
- `PYTHONPATH`: Set to `/app` (handled automatically)

## Production Deployment

### Systemd Service
Create `/etc/systemd/system/tn-electoral-search.service`:

```ini
[Unit]
Description=TN Electoral Search
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/tn-electoral-search
Environment=PYTHONPATH=/opt/tn-electoral-search
ExecStart=/opt/tn-electoral-search/venv/bin/python scripts/run_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable tn-electoral-search
sudo systemctl start tn-electoral-search
```

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Performance Considerations

### Database
- SQLite with WAL mode (enabled by default)
- Regular VACUUM operations for large datasets
- Consider PostgreSQL for high-traffic deployments

### Caching
- Built-in LRU and TTL caching for search results
- Redis can be added for distributed caching

### Scaling
- Run multiple instances behind a load balancer
- Database can be shared between instances
- Consider read replicas for heavy read workloads

## Monitoring

### Health Checks
```bash
curl http://localhost:8000/api/health
```

### Logs
- Application logs to stdout/stderr
- Rotate logs with logrotate in production
- Consider centralized logging (ELK stack, etc.)

### Metrics
- Basic database statistics available at `/api/stats`
- Consider adding Prometheus metrics for production

## Backup

### Database Backup
```bash
# Simple backup
cp database/electoral_data.db backup/electoral_data_$(date +%Y%m%d).db

# With vacuum (smaller file)
sqlite3 database/electoral_data.db "VACUUM INTO 'backup/electoral_data_$(date +%Y%m%d).db'"
```

### Automated Backups
```bash
# Add to crontab
0 2 * * * cd /opt/tn-electoral-search && sqlite3 database/electoral_data.db "VACUUM INTO 'backup/electoral_data_$(date +\%Y\%m\%d).db'"
```