# Setting up HTTPS for FastAPI on OCI Instance

## Status: COMPLETED (2025-07-24)
- Domain: `rag-api.outside5sigma.com`
- SSL Certificate: Valid until 2025-10-22
- HTTPS Proxy: Nginx reverse proxy configured

## Problem
Your RAG chat widget is experiencing a Mixed Content Error because:
- GitHub Pages serves your site over HTTPS
- Your FastAPI API only supports HTTP
- Browsers block HTTP requests from HTTPS sites for security

## Solution: Enable HTTPS on your OCI Instance

### Architecture
```
Internet → your-domain.com:443 (HTTPS) → Nginx → localhost:8000 (FastAPI HTTP)
```

## Step-by-Step Setup

### 1. Install Nginx on your OCI Instance
```bash
# SSH into your OCI instance
ssh your-username@146.235.193.141

# Install Nginx
sudo apt update
sudo apt install nginx  # Ubuntu/Debian
# OR
sudo yum install nginx  # CentOS/RHEL
```

### 2. Configure Nginx
Create a new configuration file:
```bash
sudo nano /etc/nginx/sites-available/your-domain.com
```

Add this configuration (replace `your-domain.com` with your actual domain):
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com www.your-domain.com;

    # SSL certificates (will be added by certbot)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Proxy all requests to your FastAPI app
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # DO NOT add CORS headers here - let FastAPI handle CORS
    }
}
```

### 3. Enable the Site
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/your-domain.com /etc/nginx/sites-enabled/

# Test the configuration
sudo nginx -t

# Start/restart Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 4. Update OCI Security Rules
In OCI Console → Compute → Instances → Your Instance → Subnet → Security Lists:

Add ingress rules:
- **Port 80** (HTTP) - Source: 0.0.0.0/0
- **Port 443** (HTTPS) - Source: 0.0.0.0/0

### 5. Get Free SSL Certificate with Let's Encrypt
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace with your actual domain)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

**This single command will:**
- ✅ Get a free SSL certificate from Let's Encrypt
- ✅ Automatically configure Nginx to use it
- ✅ Set up automatic renewal (every 90 days)
- ✅ Redirect HTTP to HTTPS

### 6. Keep FastAPI Running
Your FastAPI continues running on port 8000 (HTTP internally):
```bash
# Your FastAPI command stays the same
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 7. Update Jekyll Configuration
After HTTPS is working, update `_layouts/default.html`:
```javascript
// Chat widget configuration
// HTTPS enabled - no more Mixed Content Error!
window.CHAT_CONFIG = {
  apiUrl: 'https://your-domain.com'
};
```

## Prerequisites
- Domain name pointing to your OCI instance IP (146.235.193.141)
- Ports 80 and 443 open in OCI security rules
- FastAPI running on port 8000

## Why This Works
- **Nginx** acts as a reverse proxy handling HTTPS termination
- **Let's Encrypt** provides free, trusted SSL certificates
- **Automatic renewal** keeps certificates current
- **CORS headers** allow your GitHub Pages site to access the API

## Testing
1. Visit `https://your-domain.com/rag/generate-test` - should work over HTTPS
2. Test the chat widget on your GitHub Pages site - no more Mixed Content Error
3. Check certificate: `openssl s_client -connect your-domain.com:443`

## Troubleshooting
- **Domain not pointing to server**: Update DNS A record to 146.235.193.141
- **Ports blocked**: Check OCI security lists and instance firewall
- **Nginx errors**: Check logs with `sudo journalctl -u nginx`
- **Certificate issues**: Run `sudo certbot renew --dry-run`

## Next Steps
Once HTTPS is working:
1. Update the API URL in your Jekyll site
2. Test the chat widget functionality
3. Set up automatic certificate renewal monitoring

## Development & Debug Process

### 1. Initial Setup (Using IP Address)
We initially configured nginx with the bare IP address:
```nginx
server {
    listen 80;
    server_name 146.235.193.141;
    location / {
        proxy_pass http://127.0.0.1:8000;
        # proxy headers...
    }
}
```

**Key Learning**: Let's Encrypt cannot issue SSL certificates for IP addresses - you must have a domain name.

### 2. Domain Configuration
After setting up `rag-api.outside5sigma.com` to point to the server:
```bash
# Updated nginx config with domain
sudo sed -i 's/146.235.193.141/rag-api.outside5sigma.com/g' /etc/nginx/sites-available/chatbot-api
sudo nginx -t && sudo systemctl reload nginx
```

### 3. Common Issues Encountered

#### Issue 1: Let's Encrypt Timeout
```
Domain: rag-api.outside5sigma.com
Type:   connection
Detail: Timeout during connect (likely firewall problem)
```

**Solution**: Add port 80 to OCI Security List ingress rules. Let's Encrypt needs HTTP access to verify domain ownership.

#### Issue 2: CORS Multiple Headers Error
```
Access-Control-Allow-Origin header contains multiple values 
'http://localhost:4000, https://jwt625.github.io', but only one is allowed
```

**Root Cause**: Both nginx and FastAPI were adding CORS headers, creating duplicates.

**Solution**: Remove CORS headers from nginx config and let FastAPI handle all CORS:
```bash
# Remove CORS headers from nginx
sudo sed -i '11,14d' /etc/nginx/sites-available/chatbot-api
sudo nginx -t && sudo systemctl reload nginx
```

### 4. Final Working Configuration

#### Nginx (handles HTTPS/SSL only):
```nginx
server {
    server_name rag-api.outside5sigma.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/rag-api.outside5sigma.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/rag-api.outside5sigma.com/privkey.pem;
}
```

#### FastAPI (handles CORS):
```python
# In app/config.py
CORS_ORIGINS: list[str] = [
    "http://localhost:4000",
    "http://127.0.0.1:4000",
    "https://jwt625.github.io",
    "https://outside5sigma.com"
]

# In app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5. Testing Commands

```bash
# Test HTTPS is working
curl https://rag-api.outside5sigma.com/

# Test CORS preflight
curl -I -X OPTIONS https://rag-api.outside5sigma.com/rag/generate-test \
  -H "Origin: http://localhost:4000" \
  -H "Access-Control-Request-Method: POST"

# Check SSL certificate
openssl s_client -connect rag-api.outside5sigma.com:443 -servername rag-api.outside5sigma.com
```

### 6. Key Takeaways

1. **OCI Security Lists**: Always ensure ports 80 and 443 are open for web traffic
2. **Domain Requirement**: SSL certificates require a domain name, not IP addresses
3. **CORS Handling**: Let only one layer (FastAPI) handle CORS to avoid conflicts
4. **Nginx Role**: Use nginx purely as an HTTPS reverse proxy, not for application logic
5. **Certificate Renewal**: Certbot automatically sets up renewal via systemd timer