"""
Datadog Incident Creator

Creates incidents in Datadog using the Incidents API (v2).
Falls back to Events API v2 if Incidents API is unavailable.
Properly structures incidents with severity, root cause analysis,
and actionable recommendations.

REQUIRES: DD_API_KEY and DD_APP_KEY environment variables.
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

from datadog_api_client import ApiClient, Configuration
from datadog_api_client.v2.api.incidents_api import IncidentsApi
from datadog_api_client.v2.model.incident_create_attributes import IncidentCreateAttributes
from datadog_api_client.v2.model.incident_create_data import IncidentCreateData
from datadog_api_client.v2.model.incident_create_request import IncidentCreateRequest
from datadog_api_client.v2.model.incident_field_attributes_single_value import IncidentFieldAttributesSingleValue
from datadog_api_client.v2.model.incident_field_attributes_single_value_type import IncidentFieldAttributesSingleValueType
from datadog_api_client.v2.model.incident_type import IncidentType

# Events API v1 for fallback (stable API)
from datadog_api_client.v1.api.events_api import EventsApi
from datadog_api_client.v1.model.event_create_request import EventCreateRequest
from datadog_api_client.v1.model.event_alert_type import EventAlertType

logger = logging.getLogger(__name__)


class DatadogConfigurationError(Exception):
    """Raised when Datadog API keys are not configured."""
    pass


class DatadogIncidentCreator:
    """
    Creates and manages incidents in Datadog using the Incidents API.
    
    Uses datadog-api-client v2 with IncidentsApi (NOT Events API).
    Properly structures incidents with severity, impact, and remediation steps.
    
    REQUIRES DD_API_KEY and DD_APP_KEY to be configured.
    """
    
    # Severity mapping
    SEVERITY_MAP = {
        "SEV-1": "SEV-1",
        "SEV-2": "SEV-2", 
        "SEV-3": "SEV-3",
        "SEV-4": "SEV-4",
        "SEV-5": "SEV-5"
    }
    
    def __init__(
        self,
        api_key: str = None,
        app_key: str = None,
        site: str = None
    ):
        """
        Initialize the Datadog incident creator.
        
        Args:
            api_key: Datadog API key (defaults to DD_API_KEY env var)
            app_key: Datadog Application key (defaults to DD_APP_KEY env var)
            site: Datadog site (defaults to DD_SITE env var)
            
        Raises:
            DatadogConfigurationError: If API keys are not configured
        """
        self.api_key = api_key or os.getenv("DD_API_KEY")
        self.app_key = app_key or os.getenv("DD_APP_KEY")
        self.site = site or os.getenv("DD_SITE", "datadoghq.com")
        
        # Validate configuration - FAIL if not configured
        if not self.api_key:
            raise DatadogConfigurationError(
                "DD_API_KEY is required. Set it in your environment or .env file."
            )
        if not self.app_key:
            raise DatadogConfigurationError(
                "DD_APP_KEY is required. Set it in your environment or .env file."
            )
        
        # Configure the API client
        self.configuration = Configuration()
        self.configuration.api_key["apiKeyAuth"] = self.api_key
        self.configuration.api_key["appKeyAuth"] = self.app_key
        self.configuration.server_variables["site"] = self.site
        
        # Enable unstable operations (Incidents API is marked as unstable)
        self.configuration.unstable_operations["create_incident"] = True
        
        self.incidents_created = 0
        self.events_sent = 0  # Track fallback events
        logger.info(f"Datadog Incident Creator initialized for site: {self.site}")
    
    def create_incident(
        self,
        anomalies: List[Dict],
        root_cause_analysis: Dict,
        correlation_info: Dict
    ) -> Dict:
        """
        Create an incident in Datadog from detected anomalies.
        
        Args:
            anomalies: List of detected anomaly dictionaries
            root_cause_analysis: AI-generated root cause analysis
            correlation_info: Correlation and pattern information
            
        Returns:
            Dictionary with incident details (id, url)
            
        Raises:
            Exception: If incident creation fails
        """
        # Build incident title
        title = self._build_title(anomalies, correlation_info)
        
        # Determine severity
        severity = correlation_info.get("total_severity", "SEV-3")
        
        # Build customer impact description
        impact = self._build_impact_description(anomalies, root_cause_analysis)
        
        # Build incident fields
        fields = self._build_incident_fields(
            anomalies, 
            root_cause_analysis, 
            correlation_info
        )
        
        # Create incident request
        incident_attributes = IncidentCreateAttributes(
            title=title,
            customer_impact_scope=impact,
            customer_impacted=True,
            fields=fields
        )
        
        incident_data = IncidentCreateData(
            type=IncidentType.INCIDENTS,
            attributes=incident_attributes
        )
        
        incident_request = IncidentCreateRequest(data=incident_data)
        
        # Try Incidents API first, fall back to Events API
        try:
            with ApiClient(self.configuration) as api_client:
                api_instance = IncidentsApi(api_client)
                response = api_instance.create_incident(body=incident_request)
            
            self.incidents_created += 1
            
            incident_id = response.data.id
            incident_url = f"https://app.{self.site}/incidents/{incident_id}"
            
            logger.info(f"Created Datadog incident: {incident_id}")
            logger.info(f"Incident URL: {incident_url}")
            
            return {
                "id": incident_id,
                "url": incident_url,
                "title": title,
                "severity": severity,
                "type": "incident",
                "created_at": datetime.utcnow().isoformat()
            }
            
        except Exception as incident_error:
            logger.warning(f"Incidents API failed: {incident_error}. Falling back to Events API.")
            
            # Fallback to Events API
            return self.send_event(
                title=title,
                text=impact,
                severity=severity,
                anomalies=anomalies,
                root_cause_analysis=root_cause_analysis
            )
    
    def send_event(
        self,
        title: str,
        text: str,
        severity: str,
        anomalies: List[Dict],
        root_cause_analysis: Dict
    ) -> Dict:
        """
        Send an event to Datadog using Events API v2 as fallback.
        
        This provides an actionable item even when Incidents API is unavailable.
        Events appear in the Event Stream and can trigger notifications.
        
        Args:
            title: Event title
            text: Event description/impact
            severity: Severity level (SEV-1 to SEV-5)
            anomalies: List of detected anomalies
            root_cause_analysis: AI analysis results
            
        Returns:
            Dictionary with event details
        """
        
        # Build detailed event text
        details = []
        details.append(f"**Severity:** {severity}")
        details.append(f"**Root Cause:** {root_cause_analysis.get('root_cause', 'Under investigation')}")
        details.append("")
        details.append("**Affected Metrics:**")
        for anomaly in anomalies[:5]:  # Limit to 5
            metric = anomaly.get("metric_name", "unknown")
            z_score = anomaly.get("z_score", 0)
            details.append(f"- {metric}: z-score={z_score:.2f}")
        details.append("")
        details.append("**Recommended Actions:**")
        for action in root_cause_analysis.get("suggested_actions", [])[:3]:
            details.append(f"- {action}")
        
        event_text = f"{text}\n\n" + "\n".join(details)
        
        # Build tags
        tags = [
            "service:llm-observability",
            "source:llm-observability",
            f"severity:{severity}",
            "hackathon:ai-partner-catalyst",
            "alert_type:anomaly"
        ]
        
        # Map severity to alert type
        alert_type_map = {
            "SEV-1": EventAlertType.ERROR,
            "SEV-2": EventAlertType.ERROR, 
            "SEV-3": EventAlertType.WARNING,
            "SEV-4": EventAlertType.WARNING,
            "SEV-5": EventAlertType.INFO
        }
        
        try:
            with ApiClient(self.configuration) as api_client:
                api_instance = EventsApi(api_client)
                
                # Create event using v1 API format
                body = EventCreateRequest(
                    title=title,
                    text=event_text,
                    tags=tags,
                    alert_type=alert_type_map.get(severity, EventAlertType.WARNING),
                    source_type_name="llm-observability",
                    priority="normal" if severity in ["SEV-1", "SEV-2"] else "low"
                )
                
                response = api_instance.create_event(body=body)
            
            self.events_sent += 1
            event_id = str(response.event.id) if response.event else str(datetime.utcnow().timestamp())
            
            logger.info(f"Sent Datadog event as fallback: {title}")
            
            return {
                "id": event_id,
                "url": f"https://app.{self.site}/event/explorer?query=source:llm-observability",
                "title": title,
                "severity": severity,
                "type": "event",
                "created_at": datetime.utcnow().isoformat(),
                "fallback": True
            }
            
        except Exception as event_error:
            logger.error(f"Events API also failed: {event_error}")
            
            # Return a local-only result to avoid breaking the flow
            return {
                "id": f"local-{datetime.utcnow().timestamp()}",
                "url": None,
                "title": title,
                "severity": severity,
                "type": "local",
                "created_at": datetime.utcnow().isoformat(),
                "error": str(event_error)
            }

    
    def _build_title(self, anomalies: List[Dict], correlation_info: Dict) -> str:
        """Build a descriptive incident title."""
        # Check for detected pattern
        primary_pattern = correlation_info.get("primary_pattern")
        
        if primary_pattern:
            pattern_name = primary_pattern.get("pattern", "Unknown Pattern")
            pattern_desc = primary_pattern.get("description", "")
            return f"[LLM Observability] {pattern_name.replace('_', ' ').title()}: {pattern_desc}"
        
        # Build from anomalies
        if len(anomalies) == 1:
            metric = anomalies[0].get("metric_name", "Unknown Metric")
            direction = anomalies[0].get("direction", "anomalous")
            return f"[LLM Observability] {metric} - {direction.title()} Value Detected"
        else:
            return f"[LLM Observability] Multiple Anomalies Detected ({len(anomalies)} metrics affected)"
    
    def _build_impact_description(
        self,
        anomalies: List[Dict],
        root_cause_analysis: Dict
    ) -> str:
        """Build customer impact description."""
        impact = root_cause_analysis.get("impact", "")
        
        if impact:
            return impact
        
        # Build from anomalies
        metric_names = [a.get("metric_name", "unknown") for a in anomalies]
        return f"LLM service experiencing anomalous behavior in: {', '.join(metric_names)}"
    
    def _build_incident_fields(
        self,
        anomalies: List[Dict],
        root_cause_analysis: Dict,
        correlation_info: Dict
    ) -> Dict:
        """Build incident custom fields."""
        fields = {}
        
        # Severity field
        severity = correlation_info.get("total_severity", "SEV-3")
        fields["severity"] = IncidentFieldAttributesSingleValue(
            type=IncidentFieldAttributesSingleValueType.DROPDOWN,
            value=severity
        )
        
        # Root cause (as summary text)
        root_cause = root_cause_analysis.get("root_cause", "Under investigation")
        fields["root_cause"] = IncidentFieldAttributesSingleValue(
            type=IncidentFieldAttributesSingleValueType.TEXTBOX,
            value=root_cause[:1000]  # Limit length
        )
        
        # Detected metrics
        metrics_list = ", ".join([a.get("metric_name", "?") for a in anomalies])
        fields["detected_metrics"] = IncidentFieldAttributesSingleValue(
            type=IncidentFieldAttributesSingleValueType.TEXTBOX,
            value=metrics_list[:500]
        )
        
        # Suggested actions
        actions = root_cause_analysis.get("suggested_actions", [])
        if actions:
            actions_text = "; ".join(actions[:5])
            fields["suggested_actions"] = IncidentFieldAttributesSingleValue(
                type=IncidentFieldAttributesSingleValueType.TEXTBOX,
                value=actions_text[:1000]
            )
        
        # AI Confidence
        confidence = root_cause_analysis.get("confidence", "medium")
        fields["ai_confidence"] = IncidentFieldAttributesSingleValue(
            type=IncidentFieldAttributesSingleValueType.TEXTBOX,
            value=confidence
        )
        
        return fields
    
    def get_stats(self) -> Dict:
        """Get incident creator statistics."""
        return {
            "incidents_created": self.incidents_created,
            "events_sent": self.events_sent,
            "total_actionable_items": self.incidents_created + self.events_sent,
            "site": self.site
        }
