"""
Root Cause Analyzer

Uses Google AI (Gemini) to generate intelligent root cause analysis
for detected anomalies with actionable recommendations.

REQUIRES: GOOGLE_API_KEY environment variable.
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GoogleAIConfigurationError(Exception):
    """Raised when Google AI is not properly configured."""
    pass


class RootCauseAnalyzer:
    """
    Generates intelligent root cause analysis using Google AI (Gemini).
    
    Features:
    - Structured JSON output with specific schema
    - Low temperature for consistent analysis
    
    REQUIRES GOOGLE_API_KEY to be configured.
    """
    
    # Analysis prompt template
    ANALYSIS_PROMPT_TEMPLATE = """You are an expert LLM operations analyst. Analyze the following anomalies detected in an LLM observability system and provide a structured root cause analysis.

## Detected Anomalies:
{anomalies_text}

## Recent Metrics Summary:
{metrics_summary}

## Task:
Provide a detailed root cause analysis for these anomalies. Consider:
1. What is the most likely root cause?
2. How are the anomalies correlated?
3. What is the impact on users/system?
4. What specific actions should be taken?

## Output Format:
Respond with a valid JSON object (no markdown, no code blocks) with this exact structure:
{{
  "root_cause": "Single sentence describing the most likely root cause",
  "evidence": ["Specific metric correlation 1", "Specific metric correlation 2"],
  "impact": "Description of user/system impact",
  "suggested_actions": ["Action 1", "Action 2", "Action 3"],
  "confidence": "high|medium|low",
  "similar_patterns": "Description of any historical patterns this matches"
}}

Respond ONLY with the JSON object, no other text."""

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        api_key: str = None,
        temperature: float = 0.1,
        max_tokens: int = 1024
    ):
        """
        Initialize the root cause analyzer.
        
        Args:
            model_name: Google AI model to use
            api_key: Google AI API key (defaults to GOOGLE_API_KEY env var)
            temperature: Generation temperature (low for consistency)
            max_tokens: Maximum response tokens
            
        Raises:
            GoogleAIConfigurationError: If API key is not configured
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Validate configuration
        if not self.api_key:
            raise GoogleAIConfigurationError(
                "GOOGLE_API_KEY is required. Get one from https://aistudio.google.com/apikey"
            )
        
        # Initialize Google AI
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        logger.info(f"Initialized Google AI with model: {self.model_name}")
        
        # Track analyses
        self.analyses_performed = 0
    
    def analyze(
        self,
        anomalies: List[Dict],
        recent_metrics: Dict
    ) -> Dict:
        """
        Generate root cause analysis for detected anomalies.
        
        Args:
            anomalies: List of detected anomaly dictionaries
            recent_metrics: Summary of recent metric values
            
        Returns:
            Structured root cause analysis dictionary
        """
        self.analyses_performed += 1
        
        if not anomalies:
            return {
                "root_cause": "No anomalies to analyze",
                "evidence": [],
                "impact": "None",
                "suggested_actions": [],
                "confidence": "high",
                "similar_patterns": "N/A",
                "source": "empty"
            }
        
        # Build prompt
        prompt = self._build_analysis_prompt(anomalies, recent_metrics)
        
        # Generate analysis
        response = self.model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens
            )
        )
        
        # Parse response
        response_text = response.text.strip()
        
        # Try to extract JSON
        analysis = self._parse_json_response(response_text)
        
        if analysis:
            analysis = self._validate_analysis(analysis)
            analysis["source"] = "ai"
            analysis["model"] = self.model_name
            return analysis
        
        # If JSON parsing fails, create structured response from text
        return self._text_to_analysis(response_text, anomalies)
    
    def _build_analysis_prompt(
        self,
        anomalies: List[Dict],
        recent_metrics: Dict
    ) -> str:
        """Build the analysis prompt for Gemini."""
        anomalies_lines = []
        for a in anomalies:
            line = (
                f"- {a.get('metric_name', 'unknown')}: "
                f"value={a.get('value', 'N/A')}, "
                f"z-score={a.get('z_score', 'N/A')}, "
                f"deviation={a.get('deviation_percent', 'N/A')}%, "
                f"direction={a.get('direction', 'N/A')}, "
                f"severity={a.get('severity', 'N/A')}"
            )
            anomalies_lines.append(line)
        
        anomalies_text = "\n".join(anomalies_lines)
        
        metrics_lines = []
        for name, value in list(recent_metrics.items())[:10]:
            metrics_lines.append(f"- {name}: {value}")
        
        metrics_summary = "\n".join(metrics_lines) if metrics_lines else "No recent metrics available"
        
        return self.ANALYSIS_PROMPT_TEMPLATE.format(
            anomalies_text=anomalies_text,
            metrics_summary=metrics_summary
        )
    
    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """Parse JSON from response text."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _validate_analysis(self, analysis: Dict) -> Dict:
        """Ensure analysis has all required fields."""
        defaults = {
            "root_cause": "Unable to determine root cause",
            "evidence": [],
            "impact": "Impact assessment unavailable",
            "suggested_actions": ["Review anomaly details", "Check recent changes", "Monitor for recurrence"],
            "confidence": "low",
            "similar_patterns": "No similar patterns identified"
        }
        
        for key, default in defaults.items():
            if key not in analysis or not analysis[key]:
                analysis[key] = default
        
        return analysis
    
    def _text_to_analysis(self, text: str, anomalies: List[Dict]) -> Dict:
        """Convert free-form text to structured analysis."""
        return {
            "root_cause": text[:200] if text else "Analysis unavailable",
            "evidence": [a.get("metric_name", "unknown") for a in anomalies],
            "impact": "See AI analysis text for details",
            "suggested_actions": [
                "Review the full AI analysis",
                "Check metric trends in Datadog",
                "Consider adjusting thresholds if false positive"
            ],
            "confidence": "medium",
            "similar_patterns": "Check historical data for comparison",
            "raw_analysis": text,
            "source": "ai_text"
        }
    
    def get_stats(self) -> Dict:
        """Get analyzer statistics."""
        return {
            "analyses_performed": self.analyses_performed,
            "model": self.model_name
        }
