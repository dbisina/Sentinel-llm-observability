"""
Unit Tests for Metrics Collector

Tests the LLMMetricsCollector class including:
- Basic metric calculation
- Edge cases (empty response, zero tokens)
- Complexity calculation accuracy
- Refusal detection
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.metrics_collector import LLMMetricsCollector


class TestLLMMetricsCollector:
    """Test suite for LLMMetricsCollector."""
    
    @pytest.fixture
    def collector(self):
        """Create a fresh collector instance for each test."""
        return LLMMetricsCollector(
            cost_per_1k_input_tokens=0.00025,
            cost_per_1k_output_tokens=0.0005
        )
    
    def test_basic_metric_calculation(self, collector):
        """Test basic metric collection with normal inputs."""
        prompt = "What is the capital of France?"
        response = "The capital of France is Paris. Paris is known for the Eiffel Tower."
        
        metrics = collector.collect_metrics(
            prompt=prompt,
            response=response,
            prompt_tokens=10,
            response_tokens=20,
            latency_ms=250.0
        )
        
        # Check token metrics
        assert metrics["llm.tokens.total"] == 30.0
        assert metrics["llm.tokens.prompt"] == 10.0
        assert metrics["llm.tokens.response"] == 20.0
        assert metrics["llm.tokens.ratio"] == 0.5  # 10/20
        
        # Check latency
        assert metrics["llm.latency.ms"] == 250.0
        
        # Check throughput
        expected_throughput = 30 / 0.25  # tokens / seconds
        assert metrics["llm.throughput.tokens_per_sec"] == expected_throughput
        
        # Check cost
        expected_cost = (10 / 1000 * 0.00025) + (20 / 1000 * 0.0005)
        assert metrics["llm.cost.per_request"] == pytest.approx(expected_cost, rel=1e-6)
        
        # Check quality indicators
        assert metrics["llm.response.is_refusal"] == 0.0
        assert metrics["llm.response.has_code"] == 0.0
    
    def test_empty_response(self, collector):
        """Test handling of empty response."""
        metrics = collector.collect_metrics(
            prompt="Hello?",
            response="",
            prompt_tokens=5,
            response_tokens=0,
            latency_ms=100.0
        )
        
        # Should handle zero response tokens
        assert metrics["llm.tokens.response"] == 0.0
        assert metrics["llm.tokens.ratio"] == 0.0  # Division by zero handled
        assert metrics["llm.response.length"] == 0.0
    
    def test_zero_tokens(self, collector):
        """Test handling of zero tokens."""
        metrics = collector.collect_metrics(
            prompt="",
            response="",
            prompt_tokens=0,
            response_tokens=0,
            latency_ms=50.0
        )
        
        assert metrics["llm.tokens.total"] == 0.0
        assert metrics["llm.cost.per_request"] == 0.0
    
    def test_complexity_calculation(self, collector):
        """Test prompt complexity calculation."""
        # Simple prompt - few words per sentence
        simple_prompt = "Hi. How are you?"
        
        # Complex prompt - many words per sentence
        complex_prompt = (
            "Please analyze the socioeconomic factors that contributed to the "
            "industrial revolution in 18th century England and their lasting impacts."
        )
        
        simple_metrics = collector.collect_metrics(
            prompt=simple_prompt,
            response="Good",
            prompt_tokens=5,
            response_tokens=1,
            latency_ms=100.0
        )
        
        # Reset for second test
        collector.reset_session()
        
        complex_metrics = collector.collect_metrics(
            prompt=complex_prompt,
            response="Here is the analysis.",
            prompt_tokens=30,
            response_tokens=5,
            latency_ms=200.0
        )
        
        # Complex prompt should have higher complexity score
        assert complex_metrics["llm.prompt.complexity_score"] > simple_metrics["llm.prompt.complexity_score"]
    
    def test_refusal_detection(self, collector):
        """Test detection of refusal responses."""
        refusal_responses = [
            "I can't help with that request.",
            "I'm sorry, but I cannot provide that information.",
            "As an AI language model, I'm not able to do that.",
            "I must decline this request as it violates my guidelines.",
        ]
        
        for response in refusal_responses:
            metrics = collector.collect_metrics(
                prompt="Do something bad",
                response=response,
                prompt_tokens=5,
                response_tokens=10,
                latency_ms=100.0
            )
            assert metrics["llm.response.is_refusal"] == 1.0, f"Failed to detect refusal: {response}"
    
    def test_non_refusal_responses(self, collector):
        """Test that normal responses are not flagged as refusals."""
        normal_responses = [
            "Here is the information you requested.",
            "The answer to your question is 42.",
            "I'd be happy to help you with that!",
        ]
        
        for response in normal_responses:
            metrics = collector.collect_metrics(
                prompt="Tell me something",
                response=response,
                prompt_tokens=5,
                response_tokens=10,
                latency_ms=100.0
            )
            assert metrics["llm.response.is_refusal"] == 0.0, f"False positive refusal: {response}"
    
    def test_code_detection(self, collector):
        """Test detection of code in responses."""
        code_responses = [
            "Here is a function:\n```python\ndef hello():\n    print('Hi')\n```",
            "Use this: `const x = 5;`",
            "Define the function as:\ndef calculate(x):\n    return x * 2",
        ]
        
        for response in code_responses:
            metrics = collector.collect_metrics(
                prompt="Write some code",
                response=response,
                prompt_tokens=5,
                response_tokens=20,
                latency_ms=100.0
            )
            assert metrics["llm.response.has_code"] == 1.0, f"Failed to detect code: {response[:50]}"
    
    def test_truncation_detection(self, collector):
        """Test detection of truncated responses."""
        truncated_responses = [
            "The list includes: item 1, item 2, item 3...",
            "And there are many more factors to consider…",
            "This is a response that ends mid",  # No period
        ]
        
        for response in truncated_responses:
            metrics = collector.collect_metrics(
                prompt="List all the things",
                response=response,
                prompt_tokens=5,
                response_tokens=15,
                latency_ms=100.0
            )
            assert metrics["llm.response.is_truncated"] == 1.0, f"Failed to detect truncation: {response}"
    
    def test_question_counting(self, collector):
        """Test counting of questions in prompt."""
        prompts_with_questions = [
            ("What?", 1),
            ("What? Why? How?", 3),
            ("No questions here.", 0),
            ("Is this a test? Yes it is.", 1),
        ]
        
        for prompt, expected_count in prompts_with_questions:
            metrics = collector.collect_metrics(
                prompt=prompt,
                response="Answer",
                prompt_tokens=5,
                response_tokens=1,
                latency_ms=100.0
            )
            assert metrics["llm.prompt.question_count"] == float(expected_count), \
                f"Expected {expected_count} questions in: {prompt}"
    
    def test_session_tracking(self, collector):
        """Test session statistics tracking."""
        # Make several requests
        for i in range(5):
            collector.collect_metrics(
                prompt=f"Request {i}",
                response=f"Response {i}",
                prompt_tokens=10,
                response_tokens=10,
                latency_ms=100.0
            )
        
        summary = collector.get_session_summary()
        
        assert summary["session.total_requests"] == 5.0
        assert summary["session.total_tokens"] == 100.0  # 5 * 20
        assert summary["session.avg_tokens_per_request"] == 20.0
    
    def test_session_reset(self, collector):
        """Test session reset functionality."""
        # Make a request
        collector.collect_metrics(
            prompt="Test",
            response="Response",
            prompt_tokens=5,
            response_tokens=10,
            latency_ms=100.0
        )
        
        # Reset
        collector.reset_session()
        
        summary = collector.get_session_summary()
        assert summary["session.total_requests"] == 0.0
        assert summary["session.total_tokens"] == 0.0
    
    def test_context_utilization(self, collector):
        """Test context window utilization calculation."""
        # Use a collector with known context window
        collector = LLMMetricsCollector(model_context_window=1000)
        
        metrics = collector.collect_metrics(
            prompt="Test",
            response="Response",
            prompt_tokens=100,  # 10% of 1000
            response_tokens=50,
            latency_ms=100.0
        )
        
        assert metrics["llm.prompt.context_utilization"] == 10.0  # 10%


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
