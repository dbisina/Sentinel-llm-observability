"""
Detection Utilities

Helper functions for statistical analysis and anomaly detection.
"""

import math
from typing import List, Tuple, Optional
import numpy as np


def calculate_z_score(value: float, mean: float, std: float) -> float:
    """
    Calculate Z-score for a value given mean and standard deviation.
    
    Args:
        value: The value to calculate Z-score for
        mean: Population/sample mean
        std: Population/sample standard deviation
        
    Returns:
        Z-score (number of standard deviations from mean)
    """
    if std == 0 or std < 0.0001:
        return 0.0
    return (value - mean) / std


def calculate_ewma(
    current_ewma: float,
    new_value: float,
    alpha: float = 0.1
) -> float:
    """
    Calculate Exponentially Weighted Moving Average.
    
    Args:
        current_ewma: Current EWMA value
        new_value: New observation
        alpha: Smoothing factor (0 < alpha <= 1)
        
    Returns:
        Updated EWMA value
    """
    return alpha * new_value + (1 - alpha) * current_ewma


def calculate_rolling_stats(
    values: List[float],
    window_size: int = 100
) -> Tuple[float, float]:
    """
    Calculate rolling mean and standard deviation.
    
    Args:
        values: List of values
        window_size: Number of recent values to use
        
    Returns:
        Tuple of (mean, std)
    """
    if not values:
        return 0.0, 0.0
    
    # Use only the most recent values
    window = values[-window_size:]
    arr = np.array(window)
    
    return float(np.mean(arr)), float(np.std(arr))


def calculate_percentile(values: List[float], percentile: float) -> float:
    """
    Calculate percentile value from a list.
    
    Args:
        values: List of values
        percentile: Percentile to calculate (0-100)
        
    Returns:
        Percentile value
    """
    if not values:
        return 0.0
    return float(np.percentile(values, percentile))


def detect_trend(values: List[float], window_size: int = 20) -> str:
    """
    Detect trend direction in a series of values.
    
    Args:
        values: List of values (time-ordered)
        window_size: Number of recent values to analyze
        
    Returns:
        'increasing', 'decreasing', or 'stable'
    """
    if len(values) < window_size:
        return "stable"
    
    recent = values[-window_size:]
    first_half = np.mean(recent[:window_size // 2])
    second_half = np.mean(recent[window_size // 2:])
    
    # Calculate percentage change
    if first_half == 0:
        return "stable"
    
    change_pct = ((second_half - first_half) / abs(first_half)) * 100
    
    if change_pct > 10:
        return "increasing"
    elif change_pct < -10:
        return "decreasing"
    else:
        return "stable"


def is_outlier_iqr(value: float, values: List[float], multiplier: float = 1.5) -> bool:
    """
    Check if a value is an outlier using the IQR method.
    
    Args:
        value: Value to check
        values: Reference values for IQR calculation
        multiplier: IQR multiplier (default 1.5 for mild outliers)
        
    Returns:
        True if value is an outlier
    """
    if len(values) < 4:
        return False
    
    q1 = np.percentile(values, 25)
    q3 = np.percentile(values, 75)
    iqr = q3 - q1
    
    lower_bound = q1 - (multiplier * iqr)
    upper_bound = q3 + (multiplier * iqr)
    
    return value < lower_bound or value > upper_bound


def calculate_correlation(x: List[float], y: List[float]) -> float:
    """
    Calculate Pearson correlation coefficient between two series.
    
    Args:
        x: First series
        y: Second series
        
    Returns:
        Correlation coefficient (-1 to 1)
    """
    if len(x) != len(y) or len(x) < 2:
        return 0.0
    
    # Use numpy for efficient calculation
    correlation_matrix = np.corrcoef(x, y)
    return float(correlation_matrix[0, 1])


def deviation_percentage(value: float, baseline: float) -> float:
    """
    Calculate percentage deviation from baseline.
    
    Args:
        value: Current value
        baseline: Baseline/expected value
        
    Returns:
        Percentage deviation (positive = above, negative = below)
    """
    if baseline == 0:
        return 0.0 if value == 0 else float('inf')
    return ((value - baseline) / abs(baseline)) * 100


def smooth_series(values: List[float], window_size: int = 5) -> List[float]:
    """
    Apply moving average smoothing to a series.
    
    Args:
        values: Input series
        window_size: Smoothing window size
        
    Returns:
        Smoothed series
    """
    if len(values) < window_size:
        return values
    
    smoothed = []
    for i in range(len(values)):
        start = max(0, i - window_size // 2)
        end = min(len(values), i + window_size // 2 + 1)
        smoothed.append(np.mean(values[start:end]))
    
    return smoothed


def normalize(values: List[float]) -> List[float]:
    """
    Normalize values to 0-1 range.
    
    Args:
        values: Input values
        
    Returns:
        Normalized values
    """
    if not values:
        return []
    
    min_val = min(values)
    max_val = max(values)
    
    if max_val == min_val:
        return [0.5] * len(values)
    
    return [(v - min_val) / (max_val - min_val) for v in values]


def standardize(values: List[float]) -> List[float]:
    """
    Standardize values to zero mean and unit variance.
    
    Args:
        values: Input values
        
    Returns:
        Standardized values (Z-scores)
    """
    if not values:
        return []
    
    mean = np.mean(values)
    std = np.std(values)
    
    if std == 0:
        return [0.0] * len(values)
    
    return [(v - mean) / std for v in values]
