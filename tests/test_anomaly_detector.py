"""
Unit Tests for Anomaly Detector

Tests the SimpleAnomalyDetector class including:
- Z-score calculation
- Rolling window behavior
- Correlation detection
- Baseline updates (EWMA)
- Synthetic anomaly detection
"""

import pytest
import sys
import os
import json
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection.anomaly_detector import SimpleAnomalyDetector
import numpy as np


class TestSimpleAnomalyDetector:
    """Test suite for SimpleAnomalyDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create a fresh detector instance for each test."""
        # Use temp file for baseline
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        return SimpleAnomalyDetector(
            window_size=50,
            threshold=3.0,
            min_data_points=10,
            baseline_file=temp_path
        )
    
    @pytest.fixture
    def populated_detector(self, detector):
        """Create a detector with populated baseline data."""
        # Add normal data points
        np.random.seed(42)
        normal_values = np.random.normal(100, 10, 50)
        
        for value in normal_values:
            detector.add_datapoint("test_metric", value)
        
        return detector
    
    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.window_size == 50
        assert detector.threshold == 3.0
        assert detector.min_data_points == 10
        assert detector.total_datapoints == 0
        assert detector.anomalies_detected == 0
    
    def test_add_datapoint(self, detector):
        """Test adding data points."""
        detector.add_datapoint("metric1", 100.0)
        detector.add_datapoint("metric1", 105.0)
        detector.add_datapoint("metric2", 50.0)
        
        assert detector.total_datapoints == 3
        assert len(detector._windows["metric1"]) == 2
        assert len(detector._windows["metric2"]) == 1
    
    def test_no_anomaly_with_insufficient_data(self, detector):
        """Test that no anomalies are detected with insufficient data."""
        # Add fewer than min_data_points
        for i in range(5):
            result = detector.detect_anomaly("metric", float(i))
            assert result is None
    
    def test_detect_high_anomaly(self, populated_detector):
        """Test detection of high value anomaly."""
        # Add a value that's definitely an outlier (mean=100, std=10)
        # Value of 150 is 5 standard deviations above mean
        anomaly = populated_detector.detect_anomaly("test_metric", 150.0)
        
        assert anomaly is not None
        assert anomaly["metric_name"] == "test_metric"
        assert anomaly["value"] == 150.0
        assert anomaly["direction"] == "high"
        assert anomaly["z_score"] > 3.0
    
    def test_detect_low_anomaly(self, populated_detector):
        """Test detection of low value anomaly."""
        # Value of 50 is 5 standard deviations below mean (100)
        anomaly = populated_detector.detect_anomaly("test_metric", 50.0)
        
        assert anomaly is not None
        assert anomaly["direction"] == "low"
        assert anomaly["z_score"] < -3.0
    
    def test_no_anomaly_for_normal_value(self, populated_detector):
        """Test that normal values don't trigger anomalies."""
        # Value close to mean (100) should not be anomaly
        anomaly = populated_detector.detect_anomaly("test_metric", 102.0)
        
        assert anomaly is None
    
    def test_severity_calculation(self, populated_detector):
        """Test severity level calculation."""
        # SEV-3: 3-4 sigma
        anomaly_sev3 = populated_detector.detect_anomaly("test_metric", 135.0)  # ~3.5 sigma
        assert anomaly_sev3["severity"] == "SEV-3"
        
        # Add more points to re-stabilize
        for _ in range(10):
            populated_detector.add_datapoint("test_metric2", 100.0)
        
        # SEV-2: 4-5 sigma  
        anomaly_sev2 = populated_detector.detect_anomaly("test_metric2", 145.0)  # ~4.5 sigma
        if anomaly_sev2:
            assert anomaly_sev2["severity"] in ["SEV-1", "SEV-2"]
    
    def test_rolling_window_size(self, detector):
        """Test that rolling window doesn't exceed max size."""
        # Add more points than window size
        for i in range(100):
            detector.add_datapoint("metric", float(i))
        
        assert len(detector._windows["metric"]) == 50  # window_size
    
    def test_detect_batch_anomalies(self, populated_detector):
        """Test batch anomaly detection."""
        metrics = {
            "test_metric": 150.0,  # Anomaly
            "normal_metric": 100.0  # Normal (new metric, needs baseline)
        }
        
        # First add baseline for normal_metric
        for _ in range(20):
            populated_detector.add_datapoint("normal_metric", 100.0)
        
        anomalies = populated_detector.detect_batch_anomalies(metrics)
        
        # Should detect the test_metric anomaly
        assert len(anomalies) >= 1
        assert any(a["metric_name"] == "test_metric" for a in anomalies)
    
    def test_correlation_detection(self, detector):
        """Test correlation detection between anomalies."""
        # Create anomalies matching a known pattern
        anomalies = [
            {"metric_name": "llm.tokens.total", "z_score": 4.0},
            {"metric_name": "llm.latency.ms", "z_score": 3.5},
        ]
        
        correlation = detector.detect_correlations(anomalies)
        
        assert correlation["patterns_detected"] >= 1
        assert correlation["primary_pattern"] is not None
        assert correlation["primary_pattern"]["pattern"] == "high_token_latency_spike"
    
    def test_ewma_baseline_update(self, detector):
        """Test EWMA baseline update."""
        # First, populate with enough data
        for _ in range(20):
            detector.add_datapoint("metric", 100.0)
        
        # Force baseline creation
        old_mean = detector._baseline.get("metric", {}).get("mean", 100.0)
        
        # Update with new value
        detector.update_baseline("metric", 120.0, alpha=0.5)
        
        new_mean = detector._baseline["metric"]["mean"]
        
        # New mean should be between old mean and new value
        assert new_mean > old_mean
        assert new_mean < 120.0
    
    def test_save_and_load_baseline(self, detector):
        """Test saving and loading baseline."""
        # Populate with data
        for i in range(30):
            detector.add_datapoint("metric1", 100.0 + i * 0.1)
        
        # Save state
        detector.save_state()
        
        # Create new detector with same file
        new_detector = SimpleAnomalyDetector(
            window_size=50,
            threshold=3.0,
            baseline_file=detector.baseline_file
        )
        
        # Should have loaded the baseline
        assert len(new_detector._baseline) > 0 or len(new_detector._windows) > 0
    
    def test_get_stats(self, populated_detector):
        """Test statistics retrieval."""
        # Trigger some anomalies
        populated_detector.detect_anomaly("test_metric", 150.0)
        populated_detector.detect_anomaly("test_metric", 160.0)
        
        stats = populated_detector.get_stats()
        
        assert "total_datapoints" in stats
        assert "anomalies_detected" in stats
        assert "metrics_tracked" in stats
        assert stats["anomalies_detected"] >= 2
    
    def test_get_recent_anomalies(self, populated_detector):
        """Test retrieving recent anomalies."""
        # Trigger anomalies
        populated_detector.detect_anomaly("test_metric", 150.0)
        populated_detector.detect_anomaly("test_metric", 160.0)
        populated_detector.detect_anomaly("test_metric", 155.0)
        
        recent = populated_detector.get_recent_anomalies(limit=2)
        
        assert len(recent) == 2
        # Should be ordered by recency (last in list is most recent)
    
    def test_reset(self, populated_detector):
        """Test detector reset."""
        populated_detector.reset()
        
        assert populated_detector.total_datapoints == 0
        assert populated_detector.anomalies_detected == 0
        assert len(populated_detector._windows) == 0
    
    def test_deviation_percentage(self, populated_detector):
        """Test deviation percentage calculation."""
        # Mean is approximately 100
        anomaly = populated_detector.detect_anomaly("test_metric", 150.0)
        
        assert anomaly is not None
        # 150 is 50% above 100
        assert anomaly["deviation_percent"] == pytest.approx(50.0, rel=0.2)
    
    def test_pattern_matching_cost_anomaly(self, detector):
        """Test cost anomaly pattern detection."""
        anomalies = [
            {"metric_name": "llm.cost.per_request", "z_score": 4.0},
            {"metric_name": "llm.tokens.total", "z_score": 3.5},
        ]
        
        correlation = detector.detect_correlations(anomalies)
        
        patterns = [p["pattern"] for p in correlation.get("all_patterns", [])]
        assert "cost_anomaly" in patterns
    
    def test_pattern_matching_quality_degradation(self, detector):
        """Test quality degradation pattern detection."""
        anomalies = [
            {"metric_name": "llm.response.is_refusal", "z_score": 4.0},
            {"metric_name": "llm.response.length", "z_score": -3.5},
        ]
        
        correlation = detector.detect_correlations(anomalies)
        
        patterns = [p["pattern"] for p in correlation.get("all_patterns", [])]
        assert "quality_degradation" in patterns
    
    def test_empty_correlation(self, detector):
        """Test correlation with no anomalies."""
        correlation = detector.detect_correlations([])
        
        assert correlation["pattern"] is None
        assert correlation["correlated_anomalies"] == []


class TestAnomalyPatterns:
    """Test specific anomaly patterns."""
    
    def test_sustained_anomaly(self):
        """Test detection of sustained anomalies."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        detector = SimpleAnomalyDetector(
            window_size=20,
            threshold=2.5,
            min_data_points=10,
            baseline_file=temp_path
        )
        
        # Build normal baseline
        for _ in range(20):
            detector.add_datapoint("metric", 100.0)
        
        # Now add sustained high values
        anomaly_count = 0
        for _ in range(5):
            result = detector.detect_anomaly("metric", 130.0)
            if result:
                anomaly_count += 1
        
        # Should detect initial anomalies (later ones may not trigger as baseline updates)
        assert anomaly_count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
