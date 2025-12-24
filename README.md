# Sentinel - LLM Observability Platform

Real-time monitoring and intelligent incident management for LLM applications.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green)
![Datadog](https://img.shields.io/badge/Datadog-Integrated-purple)
![Google AI](https://img.shields.io/badge/Google%20AI-Gemini-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Demo Video

[![Sentinel Demo](https://img.youtube.com/vi/PLACEHOLDER/maxresdefault.jpg)](https://www.youtube.com/watch?v=PLACEHOLDER)

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

- Python 3.11+
- Datadog account ([free trial](https://www.datadoghq.com/))
- Google AI API key ([get one here](https://aistudio.google.com/apikey))

### Installation

```bash
git clone https://github.com/dbisina/sentinel-llm-observability.git
cd sentinel-llm-observability

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
DD_API_KEY=your_datadog_api_key
DD_APP_KEY=your_datadog_app_key
GOOGLE_API_KEY=your_google_ai_api_key
DD_SITE=datadoghq.eu
```

### Run

```bash
python main.py
```

Visit `http://localhost:8000/docs` for the API documentation.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                         Sentinel                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Your App ──▶ /chat ──▶ Gemini API ──▶ Response                 │
│                  │                         │                     │
│                  ▼                         ▼                     │
│           ┌───────────┐            ┌─────────────┐              │
│           │  Metrics  │            │   Anomaly   │              │
│           │ Collector │───────────▶│  Detector   │              │
│           └───────────┘            └──────┬──────┘              │
│                  │                        │                      │
│                  ▼                        ▼                      │
│           ┌───────────┐            ┌─────────────┐              │
│           │  Datadog  │            │  Root Cause │              │
│           │ Telemetry │            │  Analyzer   │              │
│           └───────────┘            └──────┬──────┘              │
│                                           │                      │
│                                           ▼                      │
│                                    ┌─────────────┐              │
│                                    │  Incident   │              │
│                                    │  Creator    │              │
│                                    └─────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Flow

1. **Request comes in** - Your app sends a prompt to `/chat`
2. **LLM processes** - Sentinel calls Gemini and captures the response
3. **Metrics collected** - Token counts, latency, costs, quality indicators
4. **Telemetry sent** - All metrics stream to Datadog in real-time
5. **Anomaly detection** - Z-score analysis against rolling baselines
6. **Incident creation** - If anomalies detected, Gemini analyzes root cause and Datadog incident is created

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat` | POST | Send a prompt, get response with full metrics |
| `/health` | GET | Component health status |
| `/metrics/summary` | GET | Aggregated metrics and recent anomalies |
| `/docs` | GET | Interactive API documentation |

### Example: Send a Chat Request

```bash
# Local
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain machine learning in simple terms"}'

# Live deployment
curl -X POST https://sentinel-pas233odta-uc.a.run.app/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain machine learning in simple terms"}'

Response includes the LLM output plus:
- 16 metrics (tokens, costs, latency, etc.)
- Any detected anomalies
- Incident details if one was created

---

## Metrics Tracked

| Category | Metric | Description |
|----------|--------|-------------|
| **Tokens** | `llm.tokens.total` | Total tokens used |
| | `llm.tokens.prompt` | Input token count |
| | `llm.tokens.response` | Output token count |
| | `llm.tokens.ratio` | Input/output ratio |
| **Cost** | `llm.cost.per_request` | Cost per request ($) |
| | `llm.cost.input` | Input token cost |
| | `llm.cost.output` | Output token cost |
| **Performance** | `llm.latency.ms` | End-to-end latency |
| | `llm.throughput.tokens_per_sec` | Processing speed |
| **Quality** | `llm.response.is_refusal` | Detected refusal (0/1) |
| | `llm.response.has_code` | Contains code (0/1) |
| | `llm.response.is_truncated` | Truncated response (0/1) |
| **Prompt** | `llm.prompt.complexity_score` | Prompt complexity |
| | `llm.prompt.question_count` | Questions in prompt |
| | `llm.prompt.context_utilization` | Context window usage % |

---

## Anomaly Detection

Sentinel uses **Z-score based detection** with:

- **Rolling window**: Last 100 datapoints
- **Threshold**: 3 standard deviations (configurable)
- **EWMA baseline**: Smoothed baseline updates
- **Pattern correlation**: Identifies related anomalies

### Detected Patterns

- `high_token_latency_spike` - High tokens causing latency
- `cost_anomaly` - Unexpected cost increase
- `quality_degradation` - Increased refusals or short responses
- `throughput_drop` - Processing speed decrease
- `context_exhaustion` - Context window over-utilization

---

## Incident Management

When anomalies are detected, Sentinel:

1. **Correlates** multiple anomalies into patterns
2. **Analyzes** root cause using Gemini AI
3. **Creates** Datadog incident with:
   - Severity level (SEV-1 to SEV-3) based on Z-score
   - AI-generated root cause explanation
   - Evidence and correlations
   - Actionable recommendations

---

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment instructions.

### Quick Deploy to Cloud Run

```bash
gcloud run deploy sentinel \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

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
