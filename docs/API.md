# API Reference

Base URL: `http://localhost:8000` (or your deployed URL)

---

## POST /chat

Process an LLM request with full observability.

### Request

```json
{
  "prompt": "Your prompt here",
  "temperature": 0.7,
  "max_tokens": 1024
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `prompt` | string | Yes | - | Prompt to send (1-32000 chars) |
| `temperature` | float | No | 0.7 | Generation temperature (0.0-2.0) |
| `max_tokens` | int | No | 1024 | Max response tokens (1-8192) |

### Response

```json
{
  "response": "The LLM response text",
  "metrics": {
    "llm.tokens.total": 150,
    "llm.tokens.prompt": 50,
    "llm.tokens.response": 100,
    "llm.tokens.ratio": 0.5,
    "llm.cost.per_request": 0.000375,
    "llm.latency.ms": 245.5,
    "llm.throughput.tokens_per_sec": 611.0,
    "llm.prompt.complexity_score": 12.5,
    "llm.response.is_refusal": 0,
    "llm.response.has_code": 0
  },
  "anomalies_detected": [],
  "incident_created": null,
  "processing_time_ms": 312.4
}
```

### With Anomalies

```json
{
  "response": "...",
  "metrics": {...},
  "anomalies_detected": [
    {
      "metric_name": "llm.latency.ms",
      "value": 5000.0,
      "z_score": 4.5,
      "deviation_percent": 400.0,
      "severity": "SEV-2",
      "direction": "high",
      "baseline_mean": 250.0,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "incident_created": {
    "id": "abc123",
    "url": "https://app.datadoghq.eu/incidents/abc123",
    "title": "[Sentinel] High Token Latency Spike",
    "severity": "SEV-2"
  },
  "processing_time_ms": 5312.4
}
```

### Errors

| Code | Description |
|------|-------------|
| 400 | Invalid request (prompt too long, invalid parameters) |
| 502 | LLM API error |
| 503 | LLM service unavailable |
| 500 | Internal server error |

### Example

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain quantum computing in simple terms"}'
```

---

## GET /health

Check health status of all components.

### Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "metrics_collected": 1234,
  "anomalies_detected": 15,
  "components": {
    "telemetry": {
      "stats": {
        "metrics_sent": 12340,
        "metrics_failed": 2
      }
    },
    "anomaly_detector": {
      "stats": {
        "total_datapoints": 50000,
        "anomalies_detected": 15,
        "metrics_tracked": 16
      }
    },
    "incident_creator": {
      "stats": {
        "incidents_created": 5
      }
    },
    "root_cause_analyzer": {
      "stats": {
        "analyses_performed": 15,
        "api_failures": 0
      }
    },
    "llm": {
      "model": "gemini-2.0-flash"
    }
  }
}
```

---

## GET /metrics/summary

Get aggregated metrics and recent anomalies.

### Response

```json
{
  "summary": {
    "total_requests": 1234,
    "uptime_seconds": 3600.5,
    "anomaly_detector": {
      "total_datapoints": 50000,
      "anomalies_detected": 15,
      "recent_anomalies": 3
    }
  },
  "recent_anomalies": [
    {
      "metric_name": "llm.latency.ms",
      "value": 5000.0,
      "z_score": 4.5,
      "severity": "SEV-2",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "session_stats": {
    "session.total_requests": 1234,
    "session.total_tokens": 185100,
    "session.total_cost": 0.046275,
    "session.requests_per_minute": 20.6
  }
}
```

---

## GET /

Root endpoint with API information.

### Response

```json
{
  "name": "Sentinel - LLM Observability Platform",
  "version": "1.0.0",
  "description": "Monitor LLM applications, detect anomalies, and create intelligent incidents",
  "endpoints": {
    "chat": "POST /chat",
    "health": "GET /health",
    "metrics": "GET /metrics/summary"
  },
  "documentation": "/docs"
}
```

---

## Error Format

All errors return:

```json
{
  "detail": "Error message description"
}
```

| Code | Meaning |
|------|---------|
| 400 | Bad Request - Invalid input |
| 422 | Validation Error - Schema mismatch |
| 500 | Internal Server Error |
| 502 | Bad Gateway - External API error |
| 503 | Service Unavailable |

---

## Interactive Docs

FastAPI provides auto-generated documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
