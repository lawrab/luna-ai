"""
LLM service implementation with circuit breaker and retry logic.
"""
import asyncio
import time
from typing import Dict, List, Optional, Any

import httpx
import ollama
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..core.types import LLMProvider, LLMConfig, ServiceStatus, LLMException, CorrelationId
from ..core.logging import get_logger, LoggingMixin, with_correlation_id
from ..core.di import Injectable


logger = get_logger(__name__)


class CircuitBreaker:
    """Simple circuit breaker for LLM calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True
    
    def on_success(self) -> None:
        """Record successful execution."""
        self.failure_count = 0
        self.state = "closed"
    
    def on_failure(self) -> None:
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class OllamaService(Injectable, LoggingMixin):
    """
    Production-ready Ollama LLM service with circuit breaker, retries, and monitoring.
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._status = ServiceStatus.INITIALIZING
        self._circuit_breaker = CircuitBreaker()
        self._client: Optional[ollama.AsyncClient] = None
        self._metrics = {
            "requests_total": 0,
            "requests_failed": 0,
            "avg_response_time_ms": 0.0,
            "total_tokens": 0
        }
    
    @property
    def name(self) -> str:
        return "ollama-llm-service"
    
    @property
    def status(self) -> ServiceStatus:
        return self._status
    
    async def start(self) -> None:
        """Start the LLM service."""
        try:
            self._client = ollama.AsyncClient(host=self.config.base_url)
            
            # Test connection
            if await self.health_check():
                self._status = ServiceStatus.HEALTHY
                self.logger.info(
                    f"LLM service started successfully",
                    extra={"extra_fields": {
                        "model": self.config.model_name,
                        "base_url": self.config.base_url
                    }}
                )
            else:
                self._status = ServiceStatus.DEGRADED
                self.logger.warning("LLM service started but health check failed")
                
        except Exception as e:
            self._status = ServiceStatus.FAILED
            self.logger.error(f"Failed to start LLM service: {e}", exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the LLM service."""
        self._status = ServiceStatus.SHUTDOWN
        if self._client:
            # Ollama client doesn't need explicit cleanup
            self._client = None
        self.logger.info("LLM service stopped")
    
    async def health_check(self) -> bool:
        """Check if LLM service is healthy."""
        if not self._client:
            return False
            
        try:
            # Try to list models as a health check
            await asyncio.wait_for(
                self._client.list(),
                timeout=5.0
            )
            return True
        except Exception as e:
            self.logger.warning(f"LLM health check failed: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.RequestError, asyncio.TimeoutError))
    )
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        correlation_id: Optional[CorrelationId] = None,
        **kwargs
    ) -> str:
        """Generate a response from the LLM with retries and circuit breaker."""
        if not self._circuit_breaker.can_execute():
            raise LLMException("Circuit breaker is open - LLM service is unavailable")
        
        if not self._client:
            raise LLMException("LLM service not started")
        
        start_time = time.time()
        
        try:
            # Log request
            request_context = {
                "model": self.config.model_name,
                "message_count": len(messages),
                "correlation_id": correlation_id.value if correlation_id else None
            }
            
            if correlation_id:
                with with_correlation_id(correlation_id):
                    self.logger.info("Sending request to LLM", extra={"extra_fields": request_context})
            else:
                self.logger.info("Sending request to LLM", extra={"extra_fields": request_context})
            
            # Prepare request
            request_kwargs = {
                "model": self.config.model_name,
                "messages": messages,
                "options": {
                    "temperature": kwargs.get("temperature", self.config.temperature),
                }
            }
            
            # Make request with timeout
            response = await asyncio.wait_for(
                self._client.chat(**request_kwargs),
                timeout=self.config.timeout_seconds
            )
            
            # Extract response text
            response_text = response.get("message", {}).get("content", "")
            
            # Record success metrics
            response_time_ms = (time.time() - start_time) * 1000
            self._update_metrics(response_time_ms, success=True)
            self._circuit_breaker.on_success()
            
            # Log response
            response_context = {
                "response_length": len(response_text),
                "response_time_ms": response_time_ms,
                "correlation_id": correlation_id.value if correlation_id else None
            }
            
            if correlation_id:
                with with_correlation_id(correlation_id):
                    self.logger.info("Received response from LLM", extra={"extra_fields": response_context})
            else:
                self.logger.info("Received response from LLM", extra={"extra_fields": response_context})
            
            return response_text
            
        except Exception as e:
            # Record failure metrics
            response_time_ms = (time.time() - start_time) * 1000
            self._update_metrics(response_time_ms, success=False)
            self._circuit_breaker.on_failure()
            
            error_msg = f"LLM request failed: {e}"
            if correlation_id:
                with with_correlation_id(correlation_id):
                    self.logger.error(error_msg, exc_info=True)
            else:
                self.logger.error(error_msg, exc_info=True)
            
            raise LLMException(error_msg, correlation_id)
    
    def _update_metrics(self, response_time_ms: float, success: bool) -> None:
        """Update internal metrics."""
        self._metrics["requests_total"] += 1
        if not success:
            self._metrics["requests_failed"] += 1
        
        # Update average response time (simple moving average)
        total_requests = self._metrics["requests_total"]
        current_avg = self._metrics["avg_response_time_ms"]
        self._metrics["avg_response_time_ms"] = (
            (current_avg * (total_requests - 1) + response_time_ms) / total_requests
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        circuit_breaker_state = {
            "state": self._circuit_breaker.state,
            "failure_count": self._circuit_breaker.failure_count,
            "last_failure_time": self._circuit_breaker.last_failure_time
        }
        
        return {
            **self._metrics,
            "circuit_breaker": circuit_breaker_state,
            "status": self.status.value
        }