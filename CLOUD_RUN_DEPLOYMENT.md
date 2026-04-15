# Google Cloud Run Deployment Guide for HR Application

This guide provides step-by-step instructions to deploy the Flask HR Application to Google Cloud Run.

## Prerequisites

- Google Cloud account with billing enabled
- Google Cloud SDK (gcloud CLI) installed locally
- Docker installed (optional, for local testing)
- OpenAI API key (for LLM features)

## Deployment Steps

### Option 1: Deploy via gcloud CLI (Recommended)

#### Step 1: Install Google Cloud SDK

```bash
# macOS
brew install --cask google-cloud-sdk

# Windows
# Download from https://cloud.google.com/sdk/docs/install

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

#### Step 2: Initialize and Login

```bash
# Login to Google Cloud
gcloud auth login

# Set your project (replace with your project ID)
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

#### Step 3: Deploy to Cloud Run

```bash
# Deploy directly from source (Cloud Build will create the container)
gcloud run deploy hr-application \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "FLASK_SECRET_KEY=$(openssl rand -hex 32)" \
  --set-env-vars "DATABASE_URL=sqlite:///hr.db" \
  --set-env-vars "UPLOAD_FOLDER=/app/uploads" \
  --set-env-vars "CHROMA_DB_PATH=/app/data/chromadb" \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0
```

#### Step 4: Set OpenAI API Key

```bash
# Update the service with your OpenAI API key
gcloud run services update hr-application \
  --region us-central1 \
  --update-env-vars "OPENAI_API_KEY=your-actual-openai-api-key"
```

---

### Option 2: Deploy via Google Cloud Console

#### Step 1: Prepare Your Code

1. Ensure all files are committed to your Git repository
2. Push to GitHub, GitLab, or Bitbucket

#### Step 2: Deploy from Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **Cloud Run**
3. Click **"CREATE SERVICE"**
4. Choose **"Continuously deploy from a repository"**
5. Connect your repository and select the branch
6. Configure the service:
   - **Service name**: hr-application
   - **Region**: us-central1 (or your preferred region)
   - **Authentication**: Allow unauthenticated invocations
   - **Container port**: 8080
   - **Memory**: 2 GiB
   - **CPU**: 2
   - **Request timeout**: 300 seconds
   - **Maximum instances**: 10
   - **Minimum instances**: 0

#### Step 3: Add Environment Variables

In the **Variables & Secrets** section, add:
```
FLASK_SECRET_KEY=<generate-a-secure-random-key>
OPENAI_API_KEY=<your-openai-api-key>
DATABASE_URL=sqlite:///hr.db
UPLOAD_FOLDER=/app/uploads
CHROMA_DB_PATH=/app/data/chromadb
```

7. Click **"CREATE"**

---

### Option 3: Deploy with Docker (Manual Build)

#### Step 1: Build Docker Image

```bash
# Build the image
docker build -t gcr.io/YOUR_PROJECT_ID/hr-application:latest .

# Test locally (optional)
docker run -p 8080:8080 \
  -e FLASK_SECRET_KEY="test-secret-key" \
  -e OPENAI_API_KEY="your-api-key" \
  gcr.io/YOUR_PROJECT_ID/hr-application:latest
```

#### Step 2: Push to Google Container Registry

```bash
# Configure Docker to use gcloud credentials
gcloud auth configure-docker

# Push the image
docker push gcr.io/YOUR_PROJECT_ID/hr-application:latest
```

#### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy hr-application \
  --image gcr.io/YOUR_PROJECT_ID/hr-application:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "FLASK_SECRET_KEY=$(openssl rand -hex 32)" \
  --set-env-vars "OPENAI_API_KEY=your-openai-api-key" \
  --set-env-vars "DATABASE_URL=sqlite:///hr.db" \
  --set-env-vars "UPLOAD_FOLDER=/app/uploads" \
  --set-env-vars "CHROMA_DB_PATH=/app/data/chromadb" \
  --memory 2Gi \
  --cpu 2
```

---

## Post-Deployment Configuration

### 1. Get Your Service URL

```bash
gcloud run services describe hr-application \
  --region us-central1 \
  --format 'value(status.url)'
```

### 2. View Logs

```bash
# Stream logs
gcloud run services logs tail hr-application --region us-central1

# Or view in Console: Cloud Run → hr-application → Logs
```

### 3. Update Environment Variables

```bash
gcloud run services update hr-application \
  --region us-central1 \
  --update-env-vars "KEY=VALUE"
```

### 4. Enable Custom Domain (Optional)

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service hr-application \
  --domain your-domain.com \
  --region us-central1
```

---

## Storage Considerations

### Current Setup (Container File System)
- **Warning**: Files stored in the container are ephemeral and will be lost on redeployment
- SQLite database and uploaded files are not persistent

### Production Recommendation: Google Cloud Storage

#### Step 1: Create Storage Bucket

```bash
# Create bucket for file uploads
gsutil mb -l us-central1 gs://YOUR_PROJECT_ID-hr-uploads

# Set bucket permissions
gsutil iam ch allUsers:objectViewer gs://YOUR_PROJECT_ID-hr-uploads
```

#### Step 2: Update Application Code

Add to `requirements.txt`:
```
google-cloud-storage==2.10.0
```

Update `config.py` to use Cloud Storage for uploads.

#### Step 3: Use Cloud SQL for Database (Recommended)

```bash
# Create Cloud SQL instance
gcloud sql instances create hr-postgres \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create hrdb --instance=hr-postgres

# Create user
gcloud sql users create hruser \
  --instance=hr-postgres \
  --password=SECURE_PASSWORD

# Connect Cloud Run to Cloud SQL
gcloud run services update hr-application \
  --region us-central1 \
  --add-cloudsql-instances YOUR_PROJECT_ID:us-central1:hr-postgres \
  --update-env-vars "DATABASE_URL=postgresql://hruser:SECURE_PASSWORD@/hrdb?host=/cloudsql/YOUR_PROJECT_ID:us-central1:hr-postgres"
```

---

## Scaling and Performance

### Auto-scaling Configuration

```bash
gcloud run services update hr-application \
  --region us-central1 \
  --min-instances 0 \
  --max-instances 10 \
  --concurrency 80 \
  --cpu-throttling \
  --memory 2Gi \
  --cpu 2
```

### Performance Tips

1. **Use Cloud CDN** for static assets
2. **Enable HTTP/2** (enabled by default)
3. **Optimize cold starts**: Keep min-instances at 1 for production
4. **Use Cloud Memorystore** for caching (Redis)

---

## Security Best Practices

### 1. Use Secret Manager for Sensitive Data

```bash
# Create secret
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-

# Grant Cloud Run access
gcloud secrets add-iam-policy-binding openai-api-key \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Update Cloud Run to use secret
gcloud run services update hr-application \
  --region us-central1 \
  --update-secrets "OPENAI_API_KEY=openai-api-key:latest"
```

### 2. Enable Identity-Aware Proxy (IAP)

```bash
# Require authentication
gcloud run services update hr-application \
  --region us-central1 \
  --no-allow-unauthenticated
```

### 3. Configure VPC Connector (Optional)

For private network access to Cloud SQL, Redis, etc.

---

## Monitoring and Logging

### Enable Cloud Monitoring

```bash
# View metrics in Cloud Console
# Navigate to: Cloud Run → hr-application → Metrics

# Set up alerts
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="HR App High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05
```

### Structured Logging

Update your Flask app to use structured logging:
```python
import google.cloud.logging
client = google.cloud.logging.Client()
client.setup_logging()
```

---

## Cost Optimization

### Pricing Breakdown
- **Free tier**: 2 million requests/month
- **CPU**: $0.00002400/vCPU-second
- **Memory**: $0.00000250/GiB-second
- **Requests**: $0.40/million requests

### Cost-Saving Tips
1. Set `--min-instances 0` for development
2. Use `--cpu-throttling` to reduce costs when idle
3. Optimize container size (use slim base images)
4. Set appropriate `--timeout` values
5. Use Cloud Storage lifecycle policies

---

## Troubleshooting

### Common Issues

1. **Container fails to start**
   - Check logs: `gcloud run services logs tail hr-application`
   - Verify PORT environment variable is set to 8080
   - Ensure all dependencies are in requirements.txt

2. **Database connection errors**
   - Verify DATABASE_URL is correct
   - Check Cloud SQL connection if using Cloud SQL
   - Ensure database is created

3. **File upload errors**
   - Container filesystem is ephemeral
   - Use Cloud Storage for persistent file storage

4. **OpenAI API errors**
   - Verify OPENAI_API_KEY is set correctly
   - Check API quota and billing
   - Review API usage in OpenAI dashboard

### Useful Commands

```bash
# Get service details
gcloud run services describe hr-application --region us-central1

# List all services
gcloud run services list

# Delete service
gcloud run services delete hr-application --region us-central1

# View revisions
gcloud run revisions list --service hr-application --region us-central1

# Rollback to previous revision
gcloud run services update-traffic hr-application \
  --region us-central1 \
  --to-revisions REVISION_NAME=100
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - id: auth
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v1
        with:
          service: hr-application
          region: us-central1
          source: .
```

---

## Support and Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Python on Cloud Run](https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Best Practices](https://cloud.google.com/run/docs/best-practices)

---

## Quick Reference

### Important Files
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies
- `.gcloudignore` - Files to exclude from deployment
- `.dockerignore` - Files to exclude from Docker build

### Environment Variables Required
- `FLASK_SECRET_KEY` - Flask session secret
- `OPENAI_API_KEY` - OpenAI API key
- `DATABASE_URL` - Database connection string
- `UPLOAD_FOLDER` - Upload directory path
- `CHROMA_DB_PATH` - Vector database path
- `PORT` - Port to run on (default: 8080)