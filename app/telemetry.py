"""
Datadog Telemetry Module

Handles sending metrics to Datadog using the datadog-api-client v2 library.
Provides both individual and batch metric submission.

REQUIRES: DD_API_KEY environment variable.
"""

import os
import time
import logging
from typing import Dict, List

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.metrics_api import MetricsApi
from datadog_api_client.v2.model.metric_intake_type import MetricIntakeType
from datadog_api_client.v2.model.metric_payload import MetricPayload
from datadog_api_client.v2.model.metric_point import MetricPoint
from datadog_api_client.v2.model.metric_resource import MetricResource
from datadog_api_client.v2.model.metric_series import MetricSeries

logger = logging.getLogger(__name__)


class DatadogConfigurationError(Exception):
    """Raised when Datadog API key is not configured."""
    pass


class DatadogTelemetry:
    """
    Handles metric submission to Datadog using the v2 API.
    
    Uses datadog-api-client v2 for proper API interactions.
    Supports both individual metric submission and batch operations.
    
    REQUIRES DD_API_KEY to be configured.
    """
    
    def __init__(
        self,
        api_key: str = None,
        app_key: str = None,
        site: str = None,
        default_tags: List[str] = None
    ):
        """
        Initialize the Datadog telemetry client.
        
        Args:
            api_key: Datadog API key (defaults to DD_API_KEY env var)
            app_key: Datadog Application key (defaults to DD_APP_KEY env var)
            site: Datadog site (defaults to DD_SITE env var or datadoghq.com)
            default_tags: Default tags to apply to all metrics
            
        Raises:
            DatadogConfigurationError: If API key is not configured
        """
        self.api_key = api_key or os.getenv("DD_API_KEY")
        self.app_key = app_key or os.getenv("DD_APP_KEY")
        self.site = site or os.getenv("DD_SITE", "datadoghq.com")
        
        # Validate configuration - FAIL if not configured
        if not self.api_key:
            raise DatadogConfigurationError(
                "DD_API_KEY is required. Set it in your environment or .env file."
            )
        
        # Default tags for all metrics
        self.default_tags = default_tags or [
            "service:llm-observability",
            "model:gemini-pro",
            "env:production"
        ]
        
        # Configure the API client
        self.configuration = Configuration()
        self.configuration.api_key["apiKeyAuth"] = self.api_key
        if self.app_key:
            self.configuration.api_key["appKeyAuth"] = self.app_key
        
        # Set the server URL based on site
        self.configuration.server_variables["site"] = self.site
        
        # Track metrics sent
        self.metrics_sent = 0
        self.metrics_failed = 0
        
        logger.info(f"Datadog Telemetry initialized for site: {self.site}")
    
    def send_metric(
        self,
        metric_name: str,
        value: float,
        tags: List[str] = None,
        metric_type: MetricIntakeType = MetricIntakeType.GAUGE
    ) -> bool:
        """
        Send a single metric to Datadog.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional additional tags
            metric_type: Type of metric (GAUGE, COUNT, RATE)
            
        Returns:
            True if metric was sent successfully
            
        Raises:
            Exception: If metric submission fails
        """
        # Combine default tags with provided tags
        all_tags = self.default_tags.copy()
        if tags:
            all_tags.extend(tags)
        
        # Create metric series
        series = MetricSeries(
            metric=metric_name,
            type=metric_type,
            points=[
                MetricPoint(
                    timestamp=int(time.time()),
                    value=value
                )
            ],
            tags=all_tags,
            resources=[
                MetricResource(
                    name="llm-observability-host",
                    type="host"
                )
            ]
        )
        
        payload = MetricPayload(series=[series])
        
        # Send metric
        with ApiClient(self.configuration) as api_client:
            api_instance = MetricsApi(api_client)
            api_instance.submit_metrics(body=payload)
            
        self.metrics_sent += 1
        logger.debug(f"Sent metric: {metric_name}={value}")
        return True
    
    def send_batch_metrics(
        self,
        metrics: Dict[str, float],
        tags: List[str] = None,
        metric_type: MetricIntakeType = MetricIntakeType.GAUGE
    ) -> bool:
        """
        Send multiple metrics to Datadog in a single API call.
        
        Args:
            metrics: Dictionary of metric_name -> value
            tags: Optional additional tags for all metrics
            metric_type: Type of metrics (GAUGE, COUNT, RATE)
            
        Returns:
            True if all metrics were sent successfully
            
        Raises:
            Exception: If metric submission fails
        """
        if not metrics:
            return True
        
        # Combine default tags with provided tags
        all_tags = self.default_tags.copy()
        if tags:
            all_tags.extend(tags)
        
        current_timestamp = int(time.time())
        
        # Build series list
        series_list = []
        for metric_name, value in metrics.items():
            series = MetricSeries(
                metric=metric_name,
                type=metric_type,
                points=[
                    MetricPoint(
                        timestamp=current_timestamp,
                        value=value
                    )
                ],
                tags=all_tags,
                resources=[
                    MetricResource(
                        name="llm-observability-host",
                        type="host"
                    )
                ]
            )
            series_list.append(series)
        
        payload = MetricPayload(series=series_list)
        
        # Send batch
        with ApiClient(self.configuration) as api_client:
            api_instance = MetricsApi(api_client)
            api_instance.submit_metrics(body=payload)
        
        self.metrics_sent += len(metrics)
        logger.info(f"Sent {len(metrics)} metrics to Datadog")
        return True
    
    def send_count_metric(
        self,
        metric_name: str,
        value: float,
        tags: List[str] = None
    ) -> bool:
        """
        Send a count metric to Datadog.
        
        Args:
            metric_name: Name of the metric
            value: Count value
            tags: Optional additional tags
            
        Returns:
            True if metric was sent successfully
        """
        return self.send_metric(
            metric_name=metric_name,
            value=value,
            tags=tags,
            metric_type=MetricIntakeType.COUNT
        )
    
    def send_rate_metric(
        self,
        metric_name: str,
        value: float,
        tags: List[str] = None
    ) -> bool:
        """
        Send a rate metric to Datadog.
        
        Args:
            metric_name: Name of the metric
            value: Rate value
            tags: Optional additional tags
            
        Returns:
            True if metric was sent successfully
        """
        return self.send_metric(
            metric_name=metric_name,
            value=value,
            tags=tags,
            metric_type=MetricIntakeType.RATE
        )
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get telemetry statistics.
        
        Returns:
            Dictionary with metrics_sent and metrics_failed counts
        """
        return {
            "metrics_sent": self.metrics_sent,
            "metrics_failed": self.metrics_failed
        }
    
    def reset_stats(self) -> None:
        """Reset telemetry statistics."""
        self.metrics_sent = 0
        self.metrics_failed = 0
