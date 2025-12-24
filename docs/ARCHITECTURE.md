# Architecture Overview

Sentinel is built as a modular observability platform with clear separation of concerns.

## System Design

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                  Sentinel                                     │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                            API Layer (FastAPI)                           │ │
│  │  ┌─────────┐  ┌─────────────┐  ┌──────────────────┐                    │ │
│  │  │ /chat   │  │   /health   │  │ /metrics/summary │                    │ │
│  │  └────┬────┘  └─────────────┘  └──────────────────┘                    │ │
│  └───────┼──────────────────────────────────────────────────────────────────┘ │
│          │                                                                    │
│          ▼                                                                    │
│  ┌───────────────────────────────────────────────────────────────────────────┐│
│  │                         Processing Pipeline                               ││
│  │                                                                           ││
│  │  ┌───────────┐    ┌────────────────┐    ┌─────────────────┐              ││
│  │  │  Gemini   │───▶│    Metrics     │───▶│    Datadog      │              ││
│  │  │   API     │    │   Collector    │    │   Telemetry     │              ││
│  │  └───────────┘    └───────┬────────┘    └─────────────────┘              ││
│  │                           │                                               ││
│  │                           ▼                                               ││
│  │                   ┌───────────────┐                                       ││
│  │                   │   Anomaly     │                                       ││
│  │                   │   Detector    │                                       ││
│  │                   └───────┬───────┘                                       ││
│  │                           │                                               ││
│  │           ┌───────────────┴───────────────┐                              ││
│  │           ▼                               ▼                              ││
│  │   ┌───────────────┐            ┌─────────────────┐                       ││
│  │   │  Root Cause   │            │    Incident     │                       ││
│  │   │   Analyzer    │───────────▶│    Creator      │                       ││
│  │   │   (Gemini)    │            │   (Datadog)     │                       ││
│  │   └───────────────┘            └─────────────────┘                       ││
│  └───────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

## Components

### API Layer (`app/server.py`)

FastAPI application handling all HTTP requests. Uses async request handling with CORS support.

**Endpoints:**
- `POST /chat` - Process LLM requests with full observability
- `GET /health` - Component health checks
- `GET /metrics/summary` - Aggregated metrics

**Key design decisions:**
- Lifespan context manager for clean startup/shutdown
- Global exception handler for consistent error responses
- Request logging middleware for debugging

### Metrics Collector (`app/metrics_collector.py`)

Extracts 16+ metrics from every LLM interaction:

**Token Economics:**
- Total, prompt, response token counts
- Token ratio (prompt/response)
- Cost calculations using model pricing

**Performance:**
- Latency in milliseconds
- Throughput (tokens/second)

**Quality Indicators:**
- Refusal detection via regex patterns
- Code detection (markdown blocks, function definitions)
- Truncation detection

### Datadog Telemetry (`app/telemetry.py`)

Handles metric submission to Datadog using the v2 API:

- Uses official `datadog-api-client` (not deprecated `datadog` package)
- Batch metric submission for efficiency
- Configurable tags and metadata

### Anomaly Detector (`detection/anomaly_detector.py`)

Z-score based anomaly detection:

```
Z-score = (value - mean) / std
Anomaly if |Z-score| > threshold (default 3.0)
```

**Features:**
- Rolling window statistics (100 datapoints)
- EWMA baseline updates (α = 0.1)
- Pattern correlation for related anomalies
- Severity mapping (SEV-1 to SEV-3)

**Known Patterns:**
- `high_token_latency_spike`
- `cost_anomaly`
- `quality_degradation`
- `throughput_drop`
- `context_exhaustion`

### Root Cause Analyzer (`incidents/root_cause.py`)

Uses Gemini to generate intelligent root cause analysis:

1. Builds structured prompt with anomaly context
2. Calls Gemini with low temperature (0.1) for consistency
3. Parses JSON response
4. Falls back to rule-based analysis if API fails

**Output Schema:**
```json
{
  "root_cause": "string",
  "evidence": ["string"],
  "impact": "string",
  "suggested_actions": ["string"],
  "confidence": "high|medium|low",
  "similar_patterns": "string"
}
```

### Incident Creator (`incidents/incident_creator.py`)

Creates incidents in Datadog via Incidents API:

- Uses `IncidentsApi` (not Events API)
- Sets severity based on Z-score magnitude
- Includes AI-generated root cause
- Adds actionable recommendations
- Falls back to Events API if Incidents API unavailable

## Data Flow

### Request Processing

```
1. Request received at /chat
2. Validate input (length, content)
3. Start latency timer
4. Call Gemini API
5. Calculate all metrics
6. Send batch to Datadog
7. Check each metric for anomalies
8. If anomalies found:
   a. Detect correlations/patterns
   b. Generate AI root cause analysis
   c. Create Datadog incident
9. Return response with metadata
```

### Anomaly Detection Flow

```
1. New metric value arrives
2. Add to rolling window
3. Calculate window statistics
4. If window size >= min_points:
   a. Calculate Z-score
   b. If |Z| > threshold:
      - Create anomaly record
      - Determine severity
      - Track for correlation
5. Update EWMA baseline
```

## Scaling

### Horizontal Scaling

- FastAPI is async-first, handles concurrent requests efficiently
- Stateless design allows multiple instances
- Baseline data can be stored in shared storage (Redis, GCS)

### Performance Optimization

- Batch metric submission (single API call per request)
- Efficient rolling window with `deque`
- Compiled regex patterns for text analysis

### High Availability

- Health check endpoint for load balancers
- Graceful degradation without external APIs
- Fallback analysis when Gemini unavailable

## Security

- API keys stored in environment variables only
- No credentials in code or logs
- CORS configured for production origins
- Input validation on all endpoints
