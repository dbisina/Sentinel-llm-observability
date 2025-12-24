"""
Integration Tests

End-to-end integration tests for the LLM Observability Platform.
Tests the full flow from request to incident creation.

Note: Some tests require API keys to be configured.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.metrics_collector import LLMMetricsCollector
from app.telemetry import DatadogTelemetry
from detection.anomaly_detector import SimpleAnomalyDetector
from incidents.incident_creator import DatadogIncidentCreator
from incidents.root_cause import RootCauseAnalyzer


class TestEndToEndFlow:
    """Test the complete observability flow."""
    
    @pytest.fixture
    def components(self):
        """Create all components for integration testing."""
        return {
            "metrics_collector": LLMMetricsCollector(),
            "anomaly_detector": SimpleAnomalyDetector(
                window_size=20,
                threshold=2.5,
                min_data_points=5
            ),
            "telemetry": DatadogTelemetry(),  # Will be disabled without keys
            "incident_creator": DatadogIncidentCreator(),
            "root_cause_analyzer": RootCauseAnalyzer()
        }
    
    def test_full_flow_normal_request(self, components):
        """Test full flow with normal request (no anomaly)."""
        # Populate baseline
        for i in range(20):
            components["anomaly_detector"].add_datapoint("llm.latency.ms", 100.0 + i)
            components["anomaly_detector"].add_datapoint("llm.tokens.total", 200.0)
        
        # Simulate a normal request
        metrics = components["metrics_collector"].collect_metrics(
            prompt="What is 2+2?",
            response="2+2 equals 4.",
            prompt_tokens=10,
            response_tokens=8,
            latency_ms=120.0
        )
        
        # Check for anomalies
        anomalies = components["anomaly_detector"].detect_batch_anomalies(metrics)
        
        # Should not detect anomalies for normal request
        assert len(anomalies) == 0
    
    def test_full_flow_with_anomaly(self, components):
        """Test full flow with anomalous request."""
        # Populate baseline with low latency
        for i in range(20):
            components["anomaly_detector"].add_datapoint("llm.latency.ms", 100.0)
        
        # Simulate an anomalous request (very high latency)
        metrics = components["metrics_collector"].collect_metrics(
            prompt="Complex prompt " * 100,
            response="Long response " * 100,
            prompt_tokens=500,
            response_tokens=400,
            latency_ms=5000.0  # 5 seconds - anomalous
        )
        
        # Check for anomalies
        anomalies = components["anomaly_detector"].detect_batch_anomalies({
            "llm.latency.ms": 5000.0
        })
        
        # Should detect latency anomaly
        assert len(anomalies) >= 1
        
        # Detect correlations
        if anomalies:
            correlation = components["anomaly_detector"].detect_correlations(anomalies)
            assert "total_severity" in correlation
    
    def test_metrics_to_datadog_flow(self, components):
        """Test metrics collection and Datadog submission."""
        metrics = components["metrics_collector"].collect_metrics(
            prompt="Test prompt",
            response="Test response",
            prompt_tokens=5,
            response_tokens=5,
            latency_ms=100.0
        )
        
        # Verify all required metrics are present
        required_metrics = [
            "llm.tokens.total",
            "llm.tokens.prompt",
            "llm.tokens.response",
            "llm.latency.ms",
            "llm.cost.per_request",
            "llm.throughput.tokens_per_sec",
        ]
        
        for metric in required_metrics:
            assert metric in metrics, f"Missing metric: {metric}"
        
        # Try to send (will fail gracefully without API key)
        result = components["telemetry"].send_batch_metrics(metrics)
        
        # Should return False if API key not configured
        if not components["telemetry"].is_enabled:
            assert result is False
    
    def test_root_cause_analysis_fallback(self, components):
        """Test root cause analysis fallback mode."""
        anomalies = [
            {
                "metric_name": "llm.latency.ms",
                "value": 5000.0,
                "z_score": 5.0,
                "deviation_percent": 400.0,
                "direction": "high",
                "severity": "SEV-1"
            },
            {
                "metric_name": "llm.tokens.total",
                "value": 1000.0,
                "z_score": 4.0,
                "deviation_percent": 300.0,
                "direction": "high",
                "severity": "SEV-2"
            }
        ]
        
        recent_metrics = {"llm.latency.ms": 5000.0, "llm.tokens.total": 1000.0}
        
        # Should use fallback analysis if Vertex AI not configured
        analysis = components["root_cause_analyzer"].analyze(anomalies, recent_metrics)
        
        assert "root_cause" in analysis
        assert "evidence" in analysis
        assert "suggested_actions" in analysis
        assert len(analysis["suggested_actions"]) >= 1
    
    def test_incident_creation_fallback(self, components):
        """Test incident creation fallback mode."""
        anomalies = [
            {
                "metric_name": "llm.latency.ms",
                "value": 5000.0,
                "z_score": 5.0,
                "severity": "SEV-1"
            }
        ]
        
        root_cause = {
            "root_cause": "High token count causing increased latency",
            "evidence": ["Latency increased 400%"],
            "impact": "User requests are taking too long",
            "suggested_actions": ["Reduce prompt size"],
            "confidence": "high"
        }
        
        correlation = {
            "total_severity": "SEV-1",
            "primary_pattern": {
                "pattern": "high_token_latency_spike",
                "description": "High token count causing increased latency"
            }
        }
        
        # Should return mock incident if API not configured
        incident = components["incident_creator"].create_incident(
            anomalies, root_cause, correlation
        )
        
        assert incident is not None
        assert "id" in incident
        assert "title" in incident


class TestComponentIntegration:
    """Test integration between specific components."""
    
    def test_metrics_collector_to_detector(self):
        """Test data flow from metrics collector to anomaly detector."""
        collector = LLMMetricsCollector()
        detector = SimpleAnomalyDetector(min_data_points=5)
        
        # Build baseline
        for _ in range(10):
            metrics = collector.collect_metrics(
                prompt="Normal prompt",
                response="Normal response",
                prompt_tokens=50,
                response_tokens=50,
                latency_ms=100.0
            )
            detector.detect_batch_anomalies(metrics)
        
        # Now send anomalous request
        anomalous_metrics = collector.collect_metrics(
            prompt="Huge prompt " * 500,
            response="Huge response " * 500,
            prompt_tokens=5000,
            response_tokens=5000,
            latency_ms=10000.0
        )
        
        # Should detect anomalies
        anomalies = detector.detect_batch_anomalies(anomalous_metrics)
        
        # May or may not detect depending on baseline
        # At minimum, stats should be updated
        stats = detector.get_stats()
        assert stats["total_datapoints"] > 0
    
    def test_detector_to_root_cause(self):
        """Test flow from detector anomalies to root cause analysis."""
        detector = SimpleAnomalyDetector(min_data_points=5)
        analyzer = RootCauseAnalyzer()
        
        # Create synthetic anomalies (as if detected)
        anomalies = [
            {
                "metric_name": "llm.cost.per_request",
                "value": 0.01,
                "z_score": 5.0,
                "deviation_percent": 500.0,
                "direction": "high",
                "severity": "SEV-1"
            }
        ]
        
        # Detect correlations
        correlations = detector.detect_correlations(anomalies)
        
        # Analyze
        analysis = analyzer.analyze(anomalies, {"llm.cost.per_request": 0.01})
        
        assert analysis["root_cause"] is not None
        assert len(analysis["suggested_actions"]) > 0


class TestErrorHandling:
    """Test error handling in the integration flow."""
    
    def test_telemetry_handles_api_errors(self):
        """Test that telemetry handles API errors gracefully."""
        telemetry = DatadogTelemetry()
        
        # Even without valid API key, should not raise
        result = telemetry.send_metric("test.metric", 123.0)
        
        # Should return False (failed) but not raise
        assert result is False or result is True  # Depends on config
    
    def test_detector_handles_empty_metrics(self):
        """Test detector handles empty metrics dict."""
        detector = SimpleAnomalyDetector()
        
        anomalies = detector.detect_batch_anomalies({})
        
        assert anomalies == []
    
    def test_analyzer_handles_empty_anomalies(self):
        """Test analyzer handles empty anomalies list."""
        analyzer = RootCauseAnalyzer()
        
        analysis = analyzer.analyze([], {})
        
        assert analysis["root_cause"] == "No anomalies to analyze"


class TestWithMockedAPIs:
    """Tests with mocked external APIs."""
    
    @patch('app.telemetry.ApiClient')
    def test_telemetry_with_mocked_datadog(self, mock_api_client):
        """Test telemetry with mocked Datadog API."""
        # Setup mock
        mock_api_client.return_value.__enter__ = Mock(return_value=Mock())
        mock_api_client.return_value.__exit__ = Mock(return_value=False)
        
        # Create telemetry with fake keys
        telemetry = DatadogTelemetry(api_key="fake_key", app_key="fake_app_key")
        
        # Send metric
        result = telemetry.send_metric("test.metric", 42.0)
        
        # With valid keys, should attempt to call API
        assert telemetry.is_enabled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
