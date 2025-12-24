#!/usr/bin/env python3
"""
Baseline Generator Script

Generates synthetic baseline data for LLM metrics to enable
anomaly detection from the start without historical production data.

Usage:
    python scripts/generate_baseline.py [--output data/baseline_metrics.json] [--points 1000]
"""

import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection.baseline_generator import BaselineGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic baseline data for LLM metrics"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/baseline_metrics.json",
        help="Output file path (default: data/baseline_metrics.json)"
    )
    parser.add_argument(
        "--points", "-p",
        type=int,
        default=1000,
        help="Number of data points per metric (default: 1000)"
    )
    parser.add_argument(
        "--anomaly-rate", "-a",
        type=float,
        default=0.05,
        help="Fraction of natural anomalies to include (default: 0.05)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("LLM Observability Platform - Baseline Generator")
    print("=" * 60)
    print()
    
    generator = BaselineGenerator(
        num_points=args.points,
        anomaly_rate=args.anomaly_rate
    )
    
    generator.save(args.output)
    
    print()
    print("=" * 60)
    print("Baseline generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
