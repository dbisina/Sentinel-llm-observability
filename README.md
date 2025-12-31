# Sentinel - LLM Observability Platform

Real-time monitoring and intelligent incident management for LLM applications.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![Datadog](https://img.shields.io/badge/Datadog-Integrated-purple)
![Google AI](https://img.shields.io/badge/Google%20AI-Gemini-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Demo Video

[![Sentinel Demo](https://img.youtube.com/vi/5i0pCwsFZ_g/maxresdefault.jpg)](https://youtu.be/5i0pCwsFZ_g)

> **Watch the 3-minute demo** showing real-time anomaly detection and automated incident creation.

---

## What is Sentinel?

Sentinel is an observability platform designed specifically for LLM applications. It captures metrics from every LLM interaction, detects anomalies using statistical analysis, and automatically creates actionable incidents in Datadog with AI-powered root cause analysis.

### The Problem

LLM applications are black boxes. Without proper observability, you can't answer:
- Why did costs spike 300% yesterday?
- Which prompts are causing latency issues?
- When did response quality start degrading?
- How do I know when something's wrong before users complain?

### The Solution

Sentinel wraps your LLM interactions and provides:
- **16+ metrics** per request (tokens, costs, latency, quality indicators)
- **Z-score anomaly detection** with rolling baselines
- **Auto-generated incidents** in Datadog with severity levels
- **AI root cause analysis** explaining what went wrong and how to fix it

---

## Live Demo

**🚀 Try it now:** [https://sentinel-pas233odta-uc.a.run.app](https://sentinel-pas233odta-uc.a.run.app)

```bash
curl -X POST https://sentinel-pas233odta-uc.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is machine learning?"}'
```

---

## Quick Start

### Prerequisites

Before you begin, make sure you have:

- **Python 3.11+** - [Download here](https://www.python.org/downloads/)
- **Git** - [Download here](https://git-scm.com/downloads)
- **Datadog Account** - [Free trial](https://www.datadoghq.com/) (need API Key + App Key)
- **Google AI API Key** - [Get one here](https://aistudio.google.com/apikey)

For Cloud Run deployment, also install:
- **Google Cloud SDK** - [Install here](https://cloud.google.com/sdk/docs/install)

---

## 🧪 Local Testing (Step-by-Step)

### Step 1: Clone the Repository

```bash
git clone https://github.com/dbisina/sentinel-llm-observability.git
cd sentinel-llm-observability
```

### Step 2: Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Get Your API Keys

1. **Datadog API Key:**
   - Go to [Datadog > Organization Settings > API Keys](https://app.datadoghq.eu/organization-settings/api-keys)
   - Click "New Key" and copy it

2. **Datadog App Key:**
   - Go to [Datadog > Organization Settings > Application Keys](https://app.datadoghq.eu/organization-settings/application-keys)
   - Click "New Key" and copy it

3. **Google AI API Key:**
   - Go to [Google AI Studio](https://aistudio.google.com/apikey)
   - Click "Create API Key" and copy it

### Step 5: Create Environment File

Create a file named `.env` in the project root:

```env
# Datadog Credentials (REQUIRED)
DD_API_KEY=your_datadog_api_key_here
DD_APP_KEY=your_datadog_app_key_here
DD_SITE=datadoghq.eu

# Google AI Credentials (REQUIRED)
GOOGLE_API_KEY=your_google_ai_api_key_here

# Optional Configuration
ANOMALY_THRESHOLD=3.0
METRICS_WINDOW_SIZE=100
```

> ⚠️ **Important:** Replace the placeholder values with your actual API keys!

### Step 6: Run the Application

```bash
python main.py
```

You should see output like:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     ✓ Metrics collector initialized
INFO:     ✓ Datadog telemetry initialized
INFO:     ✓ Anomaly detector initialized
INFO:     ✓ Incident creator initialized
INFO:     ✓ Root cause analyzer initialized
INFO:     ✓ Gemini model initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 7: Test the Application

**Open the Dashboard:**
- Go to: http://localhost:8000

**Test the API:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, what is machine learning?"}'
```

**Check Health:**
```bash
curl http://localhost:8000/health
```

---

## ☁️ Deploy to Google Cloud Run (Step-by-Step)

### Step 1: Install Google Cloud SDK

**Windows:**
- Download from: https://cloud.google.com/sdk/docs/install
- Run the installer
- Open a new terminal after installation

**Mac:**
```bash
brew install google-cloud-sdk
```

**Linux:**
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### Step 2: Authenticate with Google Cloud

```bash
gcloud auth login
```

This opens a browser window. Sign in with your Google account.

### Step 3: Set Your Project

```bash
# List your projects
gcloud projects list

# Set your project (replace with your project ID)
gcloud config set project YOUR_PROJECT_ID
```

### Step 4: Enable Required APIs

```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### Step 5: Deploy to Cloud Run

Run this command (replace the API keys with your actual values):

```bash
gcloud run deploy sentinel \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 300 \
  --set-env-vars "DD_API_KEY=your_datadog_api_key,DD_APP_KEY=your_datadog_app_key,DD_SITE=datadoghq.eu,GOOGLE_API_KEY=your_google_ai_key"
```

> ⚠️ **Replace the placeholder API keys with your actual keys!**

### Step 6: Wait for Deployment

The deployment takes 2-5 minutes. You'll see progress like:
```
Building using Dockerfile and target ...
Uploading sources...
Building Container... Logs available at [...]
Creating Revision...
Routing traffic...
Done.
Service URL: https://sentinel-xxxxxx-uc.a.run.app
```

### Step 7: Verify Deployment

Copy your Service URL and test it:

```bash
# Test the dashboard (open in browser)
https://sentinel-xxxxxx-uc.a.run.app

# Test the API
curl -X POST https://sentinel-xxxxxx-uc.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'

# Check health
curl https://sentinel-xxxxxx-uc.a.run.app/health
```

---

## 🔧 Troubleshooting

### "GOOGLE_API_KEY is required"
- Make sure you set the environment variable correctly
- Check that your `.env` file is in the project root

### "Datadog API key not configured"
- Verify your DD_API_KEY is correct
- Make sure you're using the right Datadog site (datadoghq.eu vs datadoghq.com)

### Cloud Run deployment fails
- Check that billing is enabled on your Google Cloud project
- Ensure you have the required APIs enabled (Step 4 above)
- Check the Cloud Build logs for specific errors

### Incidents not appearing in Datadog
- Verify your DD_APP_KEY has the right permissions
- Check that the Incidents API is enabled for your Datadog account

---

## Project Structure

```
sentinel-llm-observability/
├── app/
│   ├── server.py           # FastAPI application
│   ├── metrics_collector.py # Metrics collection
│   └── telemetry.py        # Datadog integration
├── detection/
│   ├── anomaly_detector.py # Z-score anomaly detection
│   └── baseline_generator.py
├── incidents/
│   ├── incident_creator.py # Datadog incidents
│   └── root_cause.py       # AI root cause analysis
├── dashboards/
│   ├── datadog_dashboard.json
│   └── datadog_monitors.json
├── docs/
├── tests/
├── main.py
├── requirements.txt
└── Dockerfile
```

---

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DD_API_KEY` | Yes | - | Datadog API key |
| `DD_APP_KEY` | Yes | - | Datadog App key |
| `GOOGLE_API_KEY` | Yes | - | Google AI API key |
| `DD_SITE` | No | datadoghq.eu | Datadog site |
| `ANOMALY_THRESHOLD` | No | 3.0 | Z-score threshold |
| `METRICS_WINDOW_SIZE` | No | 100 | Rolling window size |

---

## Built With

- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[Datadog](https://www.datadoghq.eu/)** - Monitoring and incident management
- **[Google AI (Gemini)](https://ai.google.dev/)** - LLM for chat and root cause analysis
- **[datadog-api-client](https://github.com/DataDog/datadog-api-client-python)** - Official Datadog Python client

---

## Hackathon Submission

This project was built for the **AI Partner Catalyst: Accelerate Innovation** hackathon.

**Challenge**: Datadog Challenge - End-to-end observability monitoring for LLM applications

**Requirements Met**:
- ✅ Integrates Google Cloud AI (Gemini)
- ✅ Integrates Datadog for observability
- ✅ Streams telemetry to Datadog
- ✅ Defines detection rules
- ✅ Creates actionable incidents
- ✅ Dashboard surfacing application health

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Author

Built by [dbisina](https://github.com/dbisina) for AI Partner Catalyst 2025.
