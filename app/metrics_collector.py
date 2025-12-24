"""
LLM Metrics Collector

Collects comprehensive metrics from LLM request/response cycles including:
- Token economics (counts, ratios, costs)
- Performance metrics (latency, throughput)
- Prompt patterns (complexity, questions)
- Quality indicators (refusals, code detection)
"""

import re
from typing import Dict, Optional
from datetime import datetime


class LLMMetricsCollector:
    """
    Collects and calculates comprehensive metrics from LLM interactions.
    
    Tracks 12+ metrics essential for LLM observability including token usage,
    cost estimation, latency, and quality indicators.
    """
    
    # Common refusal patterns in LLM responses
    REFUSAL_PATTERNS = [
        r"i can't",
        r"i cannot",
        r"i'm unable to",
        r"i am unable to",
        r"i'm not able to",
        r"i won't",
        r"i will not",
        r"as an ai",
        r"as a language model",
        r"i don't have the ability",
        r"i'm sorry, but i can't",
        r"i apologize, but i cannot",
        r"it would be inappropriate",
        r"i must decline",
        r"against my guidelines",
        r"violates my",
        r"not something i can help with",
    ]
    
    # Patterns that indicate code in response
    CODE_PATTERNS = [
        r"```[\s\S]*?```",  # Markdown code blocks
        r"`[^`]+`",  # Inline code
        r"def\s+\w+\s*\(",  # Python function
        r"function\s+\w+\s*\(",  # JavaScript function
        r"class\s+\w+",  # Class definition
        r"import\s+\w+",  # Import statement
        r"from\s+\w+\s+import",  # Python from import
    ]
    
    def __init__(
        self,
        cost_per_1k_input_tokens: float = 0.00025,
        cost_per_1k_output_tokens: float = 0.0005,
        model_context_window: int = 32000
    ):
        """
        Initialize the metrics collector.
        
        Args:
            cost_per_1k_input_tokens: Cost per 1000 input tokens (Gemini Pro pricing)
            cost_per_1k_output_tokens: Cost per 1000 output tokens
            model_context_window: Maximum context window size for the model
        """
        self.cost_per_1k_input_tokens = cost_per_1k_input_tokens
        self.cost_per_1k_output_tokens = cost_per_1k_output_tokens
        self.model_context_window = model_context_window
        
        # Compile regex patterns for efficiency
        self._refusal_patterns = [re.compile(p, re.IGNORECASE) for p in self.REFUSAL_PATTERNS]
        self._code_patterns = [re.compile(p, re.IGNORECASE) for p in self.CODE_PATTERNS]
        
        # Request tracking
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.start_time = datetime.utcnow()
    
    def collect_metrics(
        self,
        prompt: str,
        response: str,
        prompt_tokens: int,
        response_tokens: int,
        latency_ms: float
    ) -> Dict[str, float]:
        """
        Collect all metrics from a single LLM request/response cycle.
        
        Args:
            prompt: The input prompt text
            response: The LLM response text
            prompt_tokens: Number of tokens in the prompt
            response_tokens: Number of tokens in the response
            latency_ms: Total latency in milliseconds
            
        Returns:
            Dictionary containing all calculated metrics with flat keys
            suitable for Datadog submission
        """
        # Update tracking
        self.total_requests += 1
        total_tokens = prompt_tokens + response_tokens
        self.total_tokens += total_tokens
        
        # Calculate cost
        input_cost = (prompt_tokens / 1000) * self.cost_per_1k_input_tokens
        output_cost = (response_tokens / 1000) * self.cost_per_1k_output_tokens
        request_cost = input_cost + output_cost
        self.total_cost += request_cost
        
        # Token ratio (protect against division by zero)
        token_ratio = prompt_tokens / response_tokens if response_tokens > 0 else 0.0
        
        # Throughput calculations
        latency_seconds = latency_ms / 1000 if latency_ms > 0 else 0.001
        tokens_per_second = total_tokens / latency_seconds if latency_seconds > 0 else 0.0
        
        # Quality indicators
        is_refusal = self._is_refusal(response)
        has_code = self._has_code(response)
        is_truncated = self._is_truncated(response)
        
        # Prompt analysis
        complexity_score = self._calculate_complexity(prompt)
        question_count = self._count_questions(prompt)
        context_utilization = (prompt_tokens / self.model_context_window) * 100
        
        # Response analysis
        response_length = len(response)
        
        # Build metrics dictionary with flat keys for Datadog
        metrics = {
            # Token Economics
            "llm.tokens.total": float(total_tokens),
            "llm.tokens.prompt": float(prompt_tokens),
            "llm.tokens.response": float(response_tokens),
            "llm.tokens.ratio": round(token_ratio, 4),
            
            # Cost Metrics
            "llm.cost.per_request": round(request_cost, 8),
            "llm.cost.input": round(input_cost, 8),
            "llm.cost.output": round(output_cost, 8),
            
            # Performance Metrics
            "llm.latency.ms": round(latency_ms, 2),
            "llm.throughput.tokens_per_sec": round(tokens_per_second, 2),
            
            # Prompt Patterns
            "llm.prompt.length": float(len(prompt)),
            "llm.prompt.complexity_score": round(complexity_score, 4),
            "llm.prompt.question_count": float(question_count),
            "llm.prompt.context_utilization": round(context_utilization, 2),
            
            # Quality Indicators
            "llm.response.length": float(response_length),
            "llm.response.is_refusal": 1.0 if is_refusal else 0.0,
            "llm.response.has_code": 1.0 if has_code else 0.0,
            "llm.response.is_truncated": 1.0 if is_truncated else 0.0,
        }
        
        return metrics
    
    def _calculate_complexity(self, text: str) -> float:
        """
        Calculate text complexity score based on words per sentence ratio.
        Higher values indicate more complex text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Complexity score (words per sentence)
        """
        if not text:
            return 0.0
        
        # Count words (simple split by whitespace)
        words = text.split()
        word_count = len(words)
        
        if word_count == 0:
            return 0.0
        
        # Count sentences (split by sentence-ending punctuation)
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        if sentence_count == 0:
            return float(word_count)  # Single sentence
        
        return word_count / sentence_count
    
    def _count_questions(self, text: str) -> int:
        """
        Count the number of questions in the text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Number of question marks found
        """
        return text.count('?')
    
    def _is_refusal(self, response: str) -> bool:
        """
        Detect if the response is a refusal to answer.
        
        Args:
            response: LLM response text
            
        Returns:
            True if the response appears to be a refusal
        """
        if not response:
            return False
        
        response_lower = response.lower()
        
        # Check each refusal pattern
        for pattern in self._refusal_patterns:
            if pattern.search(response_lower):
                return True
        
        return False
    
    def _has_code(self, response: str) -> bool:
        """
        Detect if the response contains code.
        
        Args:
            response: LLM response text
            
        Returns:
            True if the response contains code patterns
        """
        if not response:
            return False
        
        for pattern in self._code_patterns:
            if pattern.search(response):
                return True
        
        return False
    
    def _is_truncated(self, response: str) -> bool:
        """
        Detect if the response appears to be truncated.
        
        Args:
            response: LLM response text
            
        Returns:
            True if the response appears truncated
        """
        if not response:
            return False
        
        # Common truncation indicators
        truncation_patterns = [
            response.endswith('...'),
            response.endswith('…'),
            response.endswith('etc'),
            # Ends mid-sentence (no period, question mark, exclamation)
            not response.rstrip().endswith(('.', '!', '?', '"', "'", '`', ')', ']', '}')),
        ]
        
        return any(truncation_patterns)
    
    def get_session_summary(self) -> Dict[str, float]:
        """
        Get summary metrics for the current session.
        
        Returns:
            Dictionary with session-level metrics
        """
        elapsed_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "session.total_requests": float(self.total_requests),
            "session.total_tokens": float(self.total_tokens),
            "session.total_cost": round(self.total_cost, 6),
            "session.elapsed_seconds": round(elapsed_seconds, 2),
            "session.requests_per_minute": round((self.total_requests / elapsed_seconds) * 60, 2) if elapsed_seconds > 0 else 0.0,
            "session.avg_tokens_per_request": round(self.total_tokens / self.total_requests, 2) if self.total_requests > 0 else 0.0,
            "session.avg_cost_per_request": round(self.total_cost / self.total_requests, 6) if self.total_requests > 0 else 0.0,
        }
    
    def reset_session(self) -> None:
        """Reset session statistics."""
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.start_time = datetime.utcnow()
