# Deployment Guide

Deploy Sentinel to Google Cloud Run for a public URL.

---

## Prerequisites

1. [Google Cloud account](https://cloud.google.com/) with billing enabled
2. [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed
3. Datadog API and App keys
4. Google AI API key ([get one](https://aistudio.google.com/apikey))

---

## Deploy to Cloud Run

### 1. Configure gcloud

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### 2. Store Secrets

```bash
echo -n "your_dd_api_key" | gcloud secrets create dd-api-key --data-file=-
echo -n "your_dd_app_key" | gcloud secrets create dd-app-key --data-file=-  
echo -n "your_google_api_key" | gcloud secrets create google-api-key --data-file=-
```

### 3. Deploy

```bash
gcloud run deploy sentinel \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets "DD_API_KEY=dd-api-key:latest,DD_APP_KEY=dd-app-key:latest,GOOGLE_API_KEY=google-api-key:latest" \
  --set-env-vars "DD_SITE=datadoghq.eu" \
  --memory 512Mi \
  --min-instances 0 \
  --max-instances 3
```

### 4. Get Your URL

After deployment:

```
Service URL: https://sentinel-pas233odta-uc.a.run.app
```

This is the public URL for hackathon submission.

---

## Quick Test

```bash
# Health check
curl https://sentinel-pas233odta-uc.a.run.app/health

# Send a chat request
curl -X POST https://sentinel-pas233odta-uc.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

---

## Alternative: Railway

For easier deployment:

1. Go to [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Add environment variables:
   - `DD_API_KEY`
   - `DD_APP_KEY`
   - `GOOGLE_API_KEY`
   - `DD_SITE=datadoghq.com`
4. Deploy

Railway auto-detects the Dockerfile and provides a public URL.

---

## Alternative: Render

1. Go to [render.com](https://render.com)
2. Create "Web Service" from GitHub
3. Settings:
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables
5. Deploy

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DD_API_KEY` | Yes | Datadog API key |
| `DD_APP_KEY` | Yes | Datadog App key |
| `GOOGLE_API_KEY` | Yes | Google AI API key |
| `DD_SITE` | No | Datadog site (default: datadoghq.com) |
| `ANOMALY_THRESHOLD` | No | Z-score threshold (default: 3.0) |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

---

## Troubleshooting

### View Logs

```bash
gcloud run logs read sentinel --region us-central1
```

### Service Status

```bash
gcloud run services describe sentinel --region us-central1
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Build fails | Check Dockerfile and requirements.txt |
| Runtime error | Check logs for missing env vars |
| Cold start slow | Set `--min-instances 1` |
| API errors | Verify secrets are correctly set |
