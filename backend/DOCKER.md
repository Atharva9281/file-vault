# Docker Setup Guide - File Vault Backend

This guide covers Docker setup for local development and Cloud Run deployment.

---

## Quick Start

### Prerequisites
- Docker installed and running
- GCP service account key (`service-account-key.json`)
- `.env` file with required environment variables

### Local Development with Docker Compose

```bash
# Start the backend (with hot-reload)
docker-compose up

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the backend
docker-compose down

# Rebuild after dependency changes
docker-compose up --build
```

The backend will be available at: `http://localhost:8000`

---

## Docker Files Overview

### 1. `Dockerfile` - Production Build
- Base image: `python:3.11-slim`
- Optimized for Cloud Run deployment
- Minimal attack surface (slim base, no dev tools)
- Multi-layer caching for faster builds

### 2. `.dockerignore` - Exclusions
Excludes from Docker build:
- Virtual environments (`venv/`)
- Cache files (`__pycache__/`)
- Local environment files (`.env`)
- Documentation and test files
- Service account keys (for security)

### 3. `docker-compose.yml` - Local Development
- Hot-reload enabled (volume mapping)
- Exposes port 8000
- Loads environment from `.env`
- Health checks configured

---

## Building the Docker Image

### Local Build (for testing)
```bash
# Build the image
docker build -t filevault-backend .

# Run the container
docker run -p 8000:8000 --env-file .env filevault-backend

# Run with service account key
docker run -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/service-account-key.json:/app/service-account-key.json:ro \
  filevault-backend
```

### Production Build (for Cloud Run)
```bash
# Set your GCP project ID
export PROJECT_ID=file-vault-assessment-484617
export REGION=us-central1

# Build and tag for Google Container Registry
docker build -t gcr.io/$PROJECT_ID/filevault-backend:latest .

# Push to GCR
docker push gcr.io/$PROJECT_ID/filevault-backend:latest
```

Alternatively, use Cloud Build (recommended):
```bash
# Build on GCP (no local Docker needed)
gcloud builds submit --tag gcr.io/$PROJECT_ID/filevault-backend:latest .
```

---

## Deployment to Cloud Run

### Option 1: Deploy from Container Registry
```bash
# After building and pushing to GCR
gcloud run deploy filevault-backend \
  --image gcr.io/$PROJECT_ID/filevault-backend:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID \
  --set-env-vars STAGING_BUCKET=file-vault-assessment-484617-staging \
  --set-env-vars VAULT_BUCKET=file-vault-assessment-484617-vault \
  --set-env-vars DB_SECRET_NAME=file-vault-db-credentials \
  --set-env-vars REGION=$REGION \
  --max-instances 10 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300s
```

### Option 2: Deploy from Source (easier)
```bash
# Cloud Run builds the Docker image for you
gcloud run deploy filevault-backend \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID \
  --set-env-vars STAGING_BUCKET=file-vault-assessment-484617-staging \
  --set-env-vars VAULT_BUCKET=file-vault-assessment-484617-vault \
  --set-env-vars DB_SECRET_NAME=file-vault-db-credentials \
  --set-env-vars REGION=$REGION \
  --max-instances 10 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300s
```

---

## Environment Variables

### Required for Docker
Create a `.env` file with:

```env
# GCP Configuration
PROJECT_ID=file-vault-assessment-484617
REGION=us-central1
STAGING_BUCKET=file-vault-assessment-484617-staging
VAULT_BUCKET=file-vault-assessment-484617-vault

# Database
DB_SECRET_NAME=file-vault-db-credentials
DB_INSTANCE_NAME=file-vault-assessment-484617:us-central1:filevault-db
DB_NAME=filevault
DB_USER=filevault-user

# Document AI
DOCUMENT_AI_PROCESSOR_ID=your-processor-id
DOCUMENT_AI_LOCATION=us

# Vertex AI
VERTEX_AI_LOCATION=us-central1

# Authentication
NEXTAUTH_SECRET=your-nextauth-secret-here

# Service Account (for local development)
GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json
```

### Cloud Run Environment Variables
Set via `--set-env-vars` flag or Cloud Console:
- Same as above, but **DO NOT** include `GOOGLE_APPLICATION_CREDENTIALS`
- Cloud Run uses attached service account instead

---

## Docker Commands Reference

### Development
```bash
# Start with logs
docker-compose up

# Rebuild and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v
```

### Image Management
```bash
# List images
docker images | grep filevault

# Remove old images
docker image prune

# Remove specific image
docker rmi filevault-backend:test

# Tag image
docker tag filevault-backend:latest gcr.io/$PROJECT_ID/filevault-backend:v1.0.0
```

### Container Management
```bash
# List running containers
docker ps

# Stop container
docker stop filevault-backend

# Remove container
docker rm filevault-backend

# Access container shell
docker exec -it filevault-backend /bin/bash

# View container logs
docker logs -f filevault-backend
```

---

## Dockerfile Breakdown

```dockerfile
# 1. Base image (Python 3.11 slim for minimal size)
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Install system dependencies (for PyMuPDF, psycopg2, etc.)
RUN apt-get update && apt-get install -y \
    gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy and install Python dependencies (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy application code
COPY ./app ./app

# 6. Expose port 8000
EXPOSE 8000

# 7. Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 8. Run uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Why these choices?**
- `python:3.11-slim`: Small base image (~50MB vs 1GB for full Python)
- Layer caching: Dependencies installed before app code (faster rebuilds)
- `--no-cache-dir`: Reduces image size by not storing pip cache
- System packages: Required for PyMuPDF (PDF processing) and pg8000 (PostgreSQL)
- `PYTHONUNBUFFERED`: Ensures logs appear in real-time
- `EXPOSE 8000`: Documents the port (Cloud Run uses $PORT)

---

## Troubleshooting

### Docker daemon not running
```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker

# Check status
docker info
```

### Permission denied
```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

### Build fails on dependencies
```bash
# Clear Docker cache
docker builder prune

# Rebuild without cache
docker build --no-cache -t filevault-backend .
```

### Can't connect to GCP services
- Verify `service-account-key.json` is mounted correctly
- Check `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Ensure service account has required IAM roles

### Hot-reload not working (docker-compose)
- Verify volume mapping in `docker-compose.yml`
- Check that `--reload` flag is in the command
- Restart: `docker-compose restart backend`

---

## Health Checks

### Local Testing
```bash
# Health check endpoint
curl http://localhost:8000/

# Config endpoint (non-sensitive)
curl http://localhost:8000/config

# API docs (FastAPI auto-generated)
open http://localhost:8000/docs
```

### Cloud Run Health Checks
Cloud Run automatically performs health checks on `/`:
- Startup probe: Initial container startup (40s grace period)
- Liveness probe: Container is healthy (every 30s)
- If health check fails 3 times, container is restarted

---

## Security Best Practices

### DO ✅
- Use `.dockerignore` to exclude sensitive files
- Mount service account key as read-only (`:ro`)
- Use environment variables for secrets (never hardcode)
- Keep base image updated (`python:3.11-slim`)
- Run as non-root user in production (Cloud Run does this)

### DON'T ❌
- Include `.env` or `service-account-key.json` in image
- Expose debug endpoints in production
- Use `latest` tag for production (use versioned tags)
- Run as root user
- Include unnecessary packages

---

## Production Checklist

Before deploying to Cloud Run:

- [ ] `.env` file configured with production values
- [ ] Service account has required IAM roles:
  - Storage Admin (GCS buckets)
  - Cloud SQL Client (database)
  - Document AI User (OCR)
  - DLP User (PII detection)
  - Vertex AI User (Gemini)
  - Secret Manager Accessor (database credentials)
- [ ] Docker build succeeds locally
- [ ] Health check endpoint returns 200 OK
- [ ] API docs accessible at `/docs`
- [ ] Cloud SQL instance is running
- [ ] GCS buckets exist and are accessible
- [ ] Document AI processor is created
- [ ] Secret Manager secret contains DB credentials
- [ ] Cloud Run service account attached
- [ ] Environment variables set in Cloud Run
- [ ] CORS configured on GCS buckets (if needed)

---

## Next Steps

1. **Local Development**: Use `docker-compose up` for development
2. **Testing**: Verify all endpoints work with Postman/curl
3. **Build**: Create production image with `gcloud builds submit`
4. **Deploy**: Deploy to Cloud Run with environment variables
5. **Monitor**: Check Cloud Run logs and metrics

For detailed deployment steps, see `/docs/DEPLOYMENT_GUIDE.md`.

---

## Resources

- [Docker Documentation](https://docs.docker.com/)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [FastAPI Docker Guide](https://fastapi.tiangolo.com/deployment/docker/)
- [Google Container Registry](https://cloud.google.com/container-registry/docs)
