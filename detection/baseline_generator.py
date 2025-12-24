"""
Baseline Data Generator

Generates synthetic baseline data for LLM metrics to enable anomaly
detection from the start without requiring historical production data.
"""

import json
import os
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np


class BaselineGenerator:
    """
    Generates synthetic baseline data for LLM observability metrics.
    
    Creates realistic distributions based on expected Gemini Pro behavior:
    - Latency: ~200-300ms typical, occasional spikes
    - Tokens: ~200-800 per request depending on complexity
    - Cost: Proportional to token usage
    - Quality: Mostly good responses with occasional refusals
    """
    
    # Metric configurations: (mean, std, min_val, max_val)
    METRIC_CONFIGS = {
        "llm.tokens.total": (500, 150, 50, 2000),
        "llm.tokens.prompt": (200, 80, 20, 1000),
        "llm.tokens.response": (300, 100, 20, 1500),
        "llm.tokens.ratio": (0.8, 0.3, 0.1, 3.0),
        
        "llm.cost.per_request": (0.0004, 0.00015, 0.00005, 0.002),
        "llm.cost.input": (0.00005, 0.00002, 0.000005, 0.00025),
        "llm.cost.output": (0.00015, 0.00005, 0.00001, 0.00075),
        
        "llm.latency.ms": (250, 80, 100, 2000),
        "llm.throughput.tokens_per_sec": (2000, 500, 500, 5000),
        
        "llm.prompt.length": (800, 300, 50, 5000),
        "llm.prompt.complexity_score": (15, 5, 5, 40),
        "llm.prompt.question_count": (1.5, 1.0, 0, 5),
        "llm.prompt.context_utilization": (3, 2, 0.1, 15),
        
        "llm.response.length": (1200, 500, 50, 8000),
        "llm.response.is_refusal": (0.02, 0.02, 0, 1),  # ~2% refusal rate
        "llm.response.has_code": (0.15, 0.1, 0, 1),  # ~15% contain code
        "llm.response.is_truncated": (0.01, 0.01, 0, 1),  # ~1% truncated
    }
    
    def __init__(self, num_points: int = 1000, anomaly_rate: float = 0.05):
        """
        Initialize the baseline generator.
        
        Args:
            num_points: Number of data points to generate per metric
            anomaly_rate: Fraction of natural anomalies to include (default 5%)
        """
        self.num_points = num_points
        self.anomaly_rate = anomaly_rate
    
    def generate(self) -> Dict:
        """
        Generate complete baseline dataset.
        
        Returns:
            Dictionary with 'baseline' and 'history' keys
        """
        history = {}
        baseline = {}
        
        for metric_name, (mean, std, min_val, max_val) in self.METRIC_CONFIGS.items():
            # Generate normal distribution
            values = self._generate_metric_values(mean, std, min_val, max_val)
            
            # Add to history
            history[metric_name] = values
            
            # Calculate baseline statistics
            baseline[metric_name] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "p50": float(np.percentile(values, 50)),
                "p95": float(np.percentile(values, 95)),
                "p99": float(np.percentile(values, 99))
            }
        
        return {
            "baseline": baseline,
            "history": history,
            "generated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "num_points": self.num_points,
                "anomaly_rate": self.anomaly_rate,
                "version": "1.0"
            }
        }
    
    def _generate_metric_values(
        self,
        mean: float,
        std: float,
        min_val: float,
        max_val: float
    ) -> List[float]:
        """
        Generate metric values with realistic distribution.
        
        Args:
            mean: Expected mean value
            std: Standard deviation
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            List of generated values
        """
        # Generate base normal distribution
        values = np.random.normal(mean, std, self.num_points)
        
        # Clip to valid range
        values = np.clip(values, min_val, max_val)
        
        # Add natural anomalies (outliers)
        num_anomalies = int(self.num_points * self.anomaly_rate)
        anomaly_indices = random.sample(range(self.num_points), num_anomalies)
        
        for idx in anomaly_indices:
            # Generate anomaly: either high or low
            if random.random() > 0.5:
                # High anomaly (3-5 sigma above mean)
                anomaly_multiplier = random.uniform(3, 5)
                values[idx] = min(mean + anomaly_multiplier * std, max_val)
            else:
                # Low anomaly (3-5 sigma below mean)
                anomaly_multiplier = random.uniform(3, 5)
                values[idx] = max(mean - anomaly_multiplier * std, min_val)
        
        return values.tolist()
    
    def save(self, filepath: str = "data/baseline_metrics.json") -> None:
        """
        Generate and save baseline data to file.
        
        Args:
            filepath: Path to save the JSON file
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Generate data
        data = self.generate()
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Generated baseline data for {len(data['baseline'])} metrics")
        print(f"Saved to: {filepath}")
        print(f"Total data points: {self.num_points} per metric")
        print(f"Anomaly rate: {self.anomaly_rate * 100}%")


def generate_realistic_sequence(
    base_mean: float,
    base_std: float,
    num_points: int = 100,
    trend: float = 0.0,
    seasonality_amplitude: float = 0.0,
    seasonality_period: int = 24
) -> List[float]:
    """
    Generate a realistic time-series sequence with optional trend and seasonality.
    
    Args:
        base_mean: Base mean value
        base_std: Base standard deviation
        num_points: Number of points to generate
        trend: Linear trend (positive or negative)
        seasonality_amplitude: Amplitude of seasonal variation
        seasonality_period: Period of seasonal variation
        
    Returns:
        List of generated values
    """
    values = []
    
    for i in range(num_points):
        # Base value from normal distribution
        base = np.random.normal(base_mean, base_std)
        
        # Add trend
        if trend != 0:
            base += trend * i
        
        # Add seasonality
        if seasonality_amplitude > 0:
            seasonal = seasonality_amplitude * np.sin(2 * np.pi * i / seasonality_period)
            base += seasonal
        
        values.append(base)
    
    return values


if __name__ == "__main__":
    # Generate baseline data when run directly
    generator = BaselineGenerator(num_points=1000, anomaly_rate=0.05)
    generator.save()
