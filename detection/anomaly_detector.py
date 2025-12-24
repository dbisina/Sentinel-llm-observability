"""
Anomaly Detection Engine

Uses Z-score based anomaly detection with rolling windows and EWMA baseline updates.
Supports correlation detection between multiple anomalies for pattern identification.
"""

import json
import os
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)


class SimpleAnomalyDetector:
    """
    Z-score based anomaly detector with rolling window statistics.
    
    Features:
    - Rolling window for recent data (configurable size)
    - EWMA for smooth baseline updates
    - Correlation detection between anomalies
    - Pattern identification (high_token_latency_spike, cost_anomaly, etc.)
    - Minimum data points requirement before detection
    """
    
    # Known anomaly patterns and their metric correlations
    ANOMALY_PATTERNS = {
        "high_token_latency_spike": {
            "metrics": ["llm.tokens.total", "llm.latency.ms"],
            "description": "High token count causing increased latency"
        },
        "cost_anomaly": {
            "metrics": ["llm.cost.per_request", "llm.tokens.total"],
            "description": "Unexpected cost increase"
        },
        "quality_degradation": {
            "metrics": ["llm.response.is_refusal", "llm.response.length"],
            "description": "Increase in refusals or short responses"
        },
        "throughput_drop": {
            "metrics": ["llm.throughput.tokens_per_sec", "llm.latency.ms"],
            "description": "Decrease in processing speed"
        },
        "context_exhaustion": {
            "metrics": ["llm.prompt.context_utilization", "llm.response.is_truncated"],
            "description": "Context window being over-utilized"
        }
    }
    
    def __init__(
        self,
        window_size: int = 100,
        threshold: float = 3.0,
        min_data_points: int = 30,
        baseline_file: Optional[str] = None,
        ewma_alpha: float = 0.1
    ):
        """
        Initialize the anomaly detector.
        
        Args:
            window_size: Size of the rolling window for statistics
            threshold: Z-score threshold for anomaly detection
            min_data_points: Minimum points needed before detection starts
            baseline_file: Path to baseline data JSON file
            ewma_alpha: Alpha parameter for EWMA baseline updates
        """
        self.window_size = window_size
        self.threshold = threshold
        self.min_data_points = min_data_points
        self.ewma_alpha = ewma_alpha
        self.baseline_file = baseline_file or "data/baseline_metrics.json"
        
        # Rolling windows per metric
        self._windows: Dict[str, deque] = {}
        
        # Baseline statistics (mean, std) per metric
        self._baseline: Dict[str, Dict[str, float]] = {}
        
        # Anomaly history for correlation detection
        self._recent_anomalies: deque = deque(maxlen=50)
        
        # Load baseline if exists
        self._load_baseline()
        
        # Stats tracking
        self.total_datapoints = 0
        self.anomalies_detected = 0
    
    def _load_baseline(self) -> None:
        """Load baseline statistics from file."""
        if os.path.exists(self.baseline_file):
            try:
                with open(self.baseline_file, 'r') as f:
                    data = json.load(f)
                    self._baseline = data.get("baseline", {})
                    
                    # Also populate windows from historical data if available
                    for metric_name, history in data.get("history", {}).items():
                        if metric_name not in self._windows:
                            self._windows[metric_name] = deque(maxlen=self.window_size)
                        for value in history[-self.window_size:]:
                            self._windows[metric_name].append(value)
                    
                logger.info(f"Loaded baseline for {len(self._baseline)} metrics from {self.baseline_file}")
            except Exception as e:
                logger.warning(f"Failed to load baseline: {e}")
                self._baseline = {}
        else:
            logger.info("No baseline file found - will build baseline from incoming data")
    
    def _save_baseline(self) -> None:
        """Save current baseline statistics to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
            
            # Collect window data for history
            history = {}
            for metric_name, window in self._windows.items():
                history[metric_name] = list(window)
            
            data = {
                "baseline": self._baseline,
                "history": history,
                "updated_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "window_size": self.window_size,
                    "threshold": self.threshold,
                    "ewma_alpha": self.ewma_alpha
                }
            }
            
            with open(self.baseline_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved baseline to {self.baseline_file}")
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
    
    def add_datapoint(self, metric_name: str, value: float) -> None:
        """
        Add a datapoint to the rolling window for a metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
        """
        if metric_name not in self._windows:
            self._windows[metric_name] = deque(maxlen=self.window_size)
        
        self._windows[metric_name].append(value)
        self.total_datapoints += 1
        
        # Update baseline using EWMA if we have enough data
        if len(self._windows[metric_name]) >= self.min_data_points:
            self.update_baseline(metric_name, value)
    
    def detect_anomaly(self, metric_name: str, value: float) -> Optional[Dict]:
        """
        Detect if a value is anomalous for a given metric.
        
        Args:
            metric_name: Name of the metric
            value: Current metric value
            
        Returns:
            Anomaly details dict if detected, None otherwise
            Contains: metric_name, value, z_score, deviation_percent, severity, direction
        """
        # Add to window first
        self.add_datapoint(metric_name, value)
        
        # Get window data
        window = self._windows.get(metric_name, deque())
        
        # Check minimum data requirement
        if len(window) < self.min_data_points:
            return None
        
        # Calculate statistics from window
        window_array = np.array(window)
        mean = np.mean(window_array)
        std = np.std(window_array)
        
        # Avoid division by zero
        if std < 0.0001:
            return None
        
        # Calculate Z-score
        z_score = (value - mean) / std
        
        # Check threshold
        if abs(z_score) < self.threshold:
            return None
        
        # Anomaly detected!
        self.anomalies_detected += 1
        
        # Calculate deviation percentage
        deviation_percent = ((value - mean) / mean) * 100 if mean != 0 else 0
        
        # Determine severity based on Z-score magnitude
        severity = self._calculate_severity(abs(z_score))
        
        # Determine direction
        direction = "high" if z_score > 0 else "low"
        
        anomaly = {
            "metric_name": metric_name,
            "value": round(value, 4),
            "z_score": round(z_score, 2),
            "deviation_percent": round(deviation_percent, 2),
            "severity": severity,
            "direction": direction,
            "baseline_mean": round(mean, 4),
            "baseline_std": round(std, 4),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Track for correlation detection
        self._recent_anomalies.append(anomaly)
        
        logger.warning(
            f"Anomaly detected: {metric_name}={value} "
            f"(z={z_score:.2f}, {deviation_percent:+.1f}%, severity={severity})"
        )
        
        return anomaly
    
    def detect_batch_anomalies(self, metrics: Dict[str, float]) -> List[Dict]:
        """
        Detect anomalies in a batch of metrics.
        
        Args:
            metrics: Dictionary of metric_name -> value
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        for metric_name, value in metrics.items():
            anomaly = self.detect_anomaly(metric_name, value)
            if anomaly:
                anomalies.append(anomaly)
        
        return anomalies
    
    def detect_correlations(self, anomalies: List[Dict]) -> Dict:
        """
        Detect correlations between multiple anomalies to identify patterns.
        
        Args:
            anomalies: List of detected anomalies
            
        Returns:
            Dictionary with pattern information
        """
        if not anomalies:
            return {"pattern": None, "correlated_anomalies": []}
        
        anomaly_metrics = {a["metric_name"] for a in anomalies}
        
        # Check for known patterns
        detected_patterns = []
        
        for pattern_name, pattern_info in self.ANOMALY_PATTERNS.items():
            pattern_metrics = set(pattern_info["metrics"])
            overlap = anomaly_metrics & pattern_metrics
            
            # If both pattern metrics are present, it's likely this pattern
            if len(overlap) == len(pattern_metrics):
                detected_patterns.append({
                    "pattern": pattern_name,
                    "description": pattern_info["description"],
                    "matching_metrics": list(overlap),
                    "confidence": "high"
                })
            elif len(overlap) > 0:
                detected_patterns.append({
                    "pattern": pattern_name,
                    "description": pattern_info["description"],
                    "matching_metrics": list(overlap),
                    "confidence": "medium"
                })
        
        # Sort by confidence and number of matching metrics
        detected_patterns.sort(
            key=lambda x: (x["confidence"] == "high", len(x["matching_metrics"])),
            reverse=True
        )
        
        result = {
            "patterns_detected": len(detected_patterns),
            "primary_pattern": detected_patterns[0] if detected_patterns else None,
            "all_patterns": detected_patterns,
            "correlated_anomalies": [
                {"metric": a["metric_name"], "z_score": a["z_score"]}
                for a in anomalies
            ],
            "total_severity": self._aggregate_severity(anomalies)
        }
        
        return result
    
    def update_baseline(self, metric_name: str, value: float, alpha: Optional[float] = None) -> None:
        """
        Update baseline statistics using EWMA (Exponentially Weighted Moving Average).
        
        Args:
            metric_name: Name of the metric
            value: New metric value
            alpha: EWMA alpha parameter (defaults to self.ewma_alpha)
        """
        alpha = alpha or self.ewma_alpha
        
        if metric_name not in self._baseline:
            # Initialize baseline from window statistics
            window = self._windows.get(metric_name, deque())
            if len(window) >= self.min_data_points:
                window_array = np.array(window)
                self._baseline[metric_name] = {
                    "mean": float(np.mean(window_array)),
                    "std": float(np.std(window_array))
                }
            return
        
        # EWMA update
        current = self._baseline[metric_name]
        current["mean"] = alpha * value + (1 - alpha) * current["mean"]
        
        # Update variance/std using Welford's method approximation
        diff = value - current["mean"]
        current["std"] = np.sqrt(
            alpha * diff * diff + (1 - alpha) * current["std"] ** 2
        )
    
    def _calculate_severity(self, abs_z_score: float) -> str:
        """
        Calculate severity level based on Z-score magnitude.
        
        Args:
            abs_z_score: Absolute value of Z-score
            
        Returns:
            Severity string: 'SEV-1', 'SEV-2', or 'SEV-3'
        """
        if abs_z_score >= 5.0:
            return "SEV-1"  # Critical
        elif abs_z_score >= 4.0:
            return "SEV-2"  # High
        else:
            return "SEV-3"  # Medium
    
    def _aggregate_severity(self, anomalies: List[Dict]) -> str:
        """
        Aggregate severity from multiple anomalies.
        
        Args:
            anomalies: List of anomaly dictionaries
            
        Returns:
            Highest severity level
        """
        if not anomalies:
            return "SEV-3"
        
        severities = [a.get("severity", "SEV-3") for a in anomalies]
        
        if "SEV-1" in severities:
            return "SEV-1"
        elif "SEV-2" in severities:
            return "SEV-2"
        else:
            return "SEV-3"
    
    def get_stats(self) -> Dict:
        """
        Get detector statistics.
        
        Returns:
            Dictionary with detector stats
        """
        return {
            "total_datapoints": self.total_datapoints,
            "anomalies_detected": self.anomalies_detected,
            "metrics_tracked": len(self._windows),
            "baseline_metrics": len(self._baseline),
            "window_size": self.window_size,
            "threshold": self.threshold,
            "recent_anomalies": len(self._recent_anomalies)
        }
    
    def get_recent_anomalies(self, limit: int = 10) -> List[Dict]:
        """
        Get recent anomalies.
        
        Args:
            limit: Maximum number of anomalies to return
            
        Returns:
            List of recent anomaly dictionaries
        """
        return list(self._recent_anomalies)[-limit:]
    
    def save_state(self) -> None:
        """Save detector state (baseline) to file."""
        self._save_baseline()
    
    def reset(self) -> None:
        """Reset detector state."""
        self._windows.clear()
        self._baseline.clear()
        self._recent_anomalies.clear()
        self.total_datapoints = 0
        self.anomalies_detected = 0
