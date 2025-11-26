# Nicole V7 - DigitalOcean Deployment

## Prerequisites
- Ubuntu 24 droplet (8GB RAM / 4 vCPU)
- Domain pointing `api.nicole.alphawavetech.com` to droplet IP (A record)
- SSH access as root or sudo user

## One-time Setup
```bash
# Copy repo to server (example using scp)
scp -r /local/path/Nicole_Assistant root@<DROPLET_IP>:/root/Nicole_Assistant

ssh root@<DROPLET_IP>
cd /root/Nicole_Assistant
chmod +x deploy/install.sh
sudo bash deploy/install.sh \
  --app-dir /opt/nicole \
  --domain api.nicole.alphawavetech.com \
  --email you@example.com
```

## Environment Variables
- Create `/opt/nicole/.env` from `.env.template` and normalize names:
  - `ELEVENLABS_VOICE_ID` → `NICOLE_VOICE_ID`
  - `REPLICATE_API_KEY` → `REPLICATE_API_TOKEN`
  - `AZURE_COMPUTER_VISION_ENDPOINT/KEY` → `AZURE_VISION_ENDPOINT/AZURE_VISION_KEY`
  - `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT/KEY` → `AZURE_DOCUMENT_ENDPOINT/AZURE_DOCUMENT_KEY`
  - Add: `REDIS_URL=redis://localhost:6379`, `QDRANT_URL=http://localhost:6333`
- Remove any leading spaces after `=`

Restart services after updating env:
```bash
supervisorctl restart nicole-api nicole-worker
```

## Services
- Redis & Qdrant are brought up with Docker Compose by the install script.
- Verify containers:
```bash
docker ps
```

## Verify
```bash
curl -sS https://api.nicole.alphawavetech.com/healthz
curl -sS https://api.nicole.alphawavetech.com/health/check
```

## Updating Code
```bash
ssh root@<DROPLET_IP>
cd /opt/nicole
rsync -a --delete --exclude='.venv' --exclude='node_modules' /root/Nicole_Assistant/ .
pip install -r backend/requirements.txt
supervisorctl restart nicole-api
```
