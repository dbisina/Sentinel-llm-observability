"""
LLM Observability Platform - FastAPI Server

Main API server providing:
- /chat endpoint for LLM interactions with full telemetry
- /health endpoint for health checks
- /metrics/summary endpoint for metrics aggregation

REQUIRES: DD_API_KEY, DD_APP_KEY, GOOGLE_API_KEY
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import our modules
from app.metrics_collector import LLMMetricsCollector
from app.telemetry import DatadogTelemetry
from detection.anomaly_detector import SimpleAnomalyDetector
from incidents.incident_creator import DatadogIncidentCreator
from incidents.root_cause import RootCauseAnalyzer

# Import Google AI
import google.generativeai as genai


# ============================================================================
# Pydantic Models
# ============================================================================

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    prompt: str = Field(..., min_length=1, max_length=32000, description="The prompt to send to the LLM")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int = Field(default=1024, ge=1, le=8192, description="Maximum response tokens")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    metrics: Dict
    anomalies_detected: List[Dict]
    incident_created: Optional[Dict] = None
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Response model for health endpoint."""
    status: str
    timestamp: str
    metrics_collected: int
    anomalies_detected: int
    components: Dict


class MetricsSummaryResponse(BaseModel):
    """Response model for metrics summary endpoint."""
    summary: Dict
    recent_anomalies: List[Dict]
    session_stats: Dict


# ============================================================================
# Global State
# ============================================================================

class AppState:
    """Application state container."""
    def __init__(self):
        self.metrics_collector: Optional[LLMMetricsCollector] = None
        self.telemetry: Optional[DatadogTelemetry] = None
        self.anomaly_detector: Optional[SimpleAnomalyDetector] = None
        self.incident_creator: Optional[DatadogIncidentCreator] = None
        self.root_cause_analyzer: Optional[RootCauseAnalyzer] = None
        self.gemini_model = None
        self.request_count: int = 0
        self.start_time: datetime = datetime.utcnow()


app_state = AppState()


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logger.info("Starting LLM Observability Platform...")
    
    # Initialize metrics collector
    app_state.metrics_collector = LLMMetricsCollector(
        cost_per_1k_input_tokens=float(os.getenv("COST_PER_1K_INPUT_TOKENS", "0.00025")),
        cost_per_1k_output_tokens=float(os.getenv("COST_PER_1K_OUTPUT_TOKENS", "0.0005"))
    )
    logger.info("✓ Metrics collector initialized")
    
    # Initialize Datadog telemetry
    app_state.telemetry = DatadogTelemetry()
    logger.info("✓ Datadog telemetry initialized")
    
    # Initialize anomaly detector
    app_state.anomaly_detector = SimpleAnomalyDetector(
        window_size=int(os.getenv("METRICS_WINDOW_SIZE", "100")),
        threshold=float(os.getenv("ANOMALY_THRESHOLD", "3.0")),
        baseline_file="data/baseline_metrics.json"
    )
    logger.info("✓ Anomaly detector initialized")
    
    # Initialize incident creator
    app_state.incident_creator = DatadogIncidentCreator()
    logger.info("✓ Incident creator initialized")
    
    # Initialize root cause analyzer (uses Google AI)
    app_state.root_cause_analyzer = RootCauseAnalyzer()
    logger.info("✓ Root cause analyzer initialized")
    
    # Initialize Google AI for LLM chat
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY is required. Get one from https://aistudio.google.com/apikey")
    
    genai.configure(api_key=api_key)
    app_state.gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    logger.info("✓ Gemini model initialized")
    
    logger.info("🚀 LLM Observability Platform ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LLM Observability Platform...")
    
    # Save detector state
    if app_state.anomaly_detector:
        app_state.anomaly_detector.save_state()
        logger.info("Saved anomaly detector state")
    
    logger.info("Shutdown complete")


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="LLM Observability Platform",
    description="Monitor LLM applications, detect anomalies, and create intelligent incidents",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests."""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    logger.debug(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}ms"
    )
    
    return response


# ============================================================================
# Endpoints
# ============================================================================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a chat request through the LLM with full observability.
    
    Flow:
    1. Validate input
    2. Start timer
    3. Call Gemini model
    4. Collect metrics
    5. Send to Datadog
    6. Check for anomalies
    7. Create incident if needed
    8. Return response
    """
    app_state.request_count += 1
    start_time = time.time()
    
    # Call Gemini
    generation_response = app_state.gemini_model.generate_content(
        request.prompt,
        generation_config=genai.GenerationConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens
        )
    )
    response_text = generation_response.text
    
    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000
    
    # Count tokens (approximation: ~4 chars per token)
    prompt_tokens = len(request.prompt) // 4
    response_tokens = len(response_text) // 4
    
    # Collect metrics
    metrics = app_state.metrics_collector.collect_metrics(
        prompt=request.prompt,
        response=response_text,
        prompt_tokens=prompt_tokens,
        response_tokens=response_tokens,
        latency_ms=latency_ms
    )
    
    # Send metrics to Datadog
    app_state.telemetry.send_batch_metrics(
        metrics=metrics,
        tags=[f"request_id:{app_state.request_count}"]
    )
    
    # Check for anomalies
    anomalies = app_state.anomaly_detector.detect_batch_anomalies(metrics)
    
    # Handle anomalies
    incident_created = None
    if anomalies:
        logger.warning(f"Detected {len(anomalies)} anomalies")
        
        # Detect correlations
        correlation_info = app_state.anomaly_detector.detect_correlations(anomalies)
        
        # Perform root cause analysis
        recent_metrics = {
            k: v for k, v in metrics.items()
            if k.startswith("llm.")
        }
        root_cause = app_state.root_cause_analyzer.analyze(
            anomalies=anomalies,
            recent_metrics=recent_metrics
        )
        
        # Create incident (non-blocking - log errors but don't fail the request)
        try:
            incident_created = app_state.incident_creator.create_incident(
                anomalies=anomalies,
                root_cause_analysis=root_cause,
                correlation_info=correlation_info
            )
        except Exception as e:
            logger.error(f"Failed to create incident: {e}")
            incident_created = {"error": str(e)}
    
    total_time = (time.time() - start_time) * 1000
    
    return ChatResponse(
        response=response_text,
        metrics=metrics,
        anomalies_detected=anomalies,
        incident_created=incident_created,
        processing_time_ms=round(total_time, 2)
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        metrics_collected=app_state.request_count,
        anomalies_detected=app_state.anomaly_detector.anomalies_detected if app_state.anomaly_detector else 0,
        components={
            "telemetry": {
                "stats": app_state.telemetry.get_stats() if app_state.telemetry else {}
            },
            "anomaly_detector": {
                "stats": app_state.anomaly_detector.get_stats() if app_state.anomaly_detector else {}
            },
            "incident_creator": {
                "stats": app_state.incident_creator.get_stats() if app_state.incident_creator else {}
            },
            "root_cause_analyzer": {
                "stats": app_state.root_cause_analyzer.get_stats() if app_state.root_cause_analyzer else {}
            },
            "llm": {
                "model": "gemini-1.5-flash"
            }
        }
    )


@app.get("/metrics/summary", response_model=MetricsSummaryResponse)
async def metrics_summary():
    """Get summary of recent metrics."""
    session_stats = {}
    if app_state.metrics_collector:
        session_stats = app_state.metrics_collector.get_session_summary()
    
    recent_anomalies = []
    detector_stats = {}
    if app_state.anomaly_detector:
        recent_anomalies = app_state.anomaly_detector.get_recent_anomalies(limit=10)
        detector_stats = app_state.anomaly_detector.get_stats()
    
    return MetricsSummaryResponse(
        summary={
            "total_requests": app_state.request_count,
            "uptime_seconds": (datetime.utcnow() - app_state.start_time).total_seconds(),
            "anomaly_detector": detector_stats
        },
        recent_anomalies=recent_anomalies,
        session_stats=session_stats
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "LLM Observability Platform",
        "version": "1.0.0",
        "description": "Monitor LLM applications, detect anomalies, and create intelligent incidents",
        "endpoints": {
            "chat": "POST /chat - Send prompts and receive responses with full observability",
            "health": "GET /health - Health check and component status",
            "metrics": "GET /metrics/summary - Recent metrics and anomalies"
        },
        "documentation": "/docs"
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# ============================================================================
# Run server (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run(
        "app.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
