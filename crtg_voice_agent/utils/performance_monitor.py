import time
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring and optimization."""
    call_id: str
    start_time: float
    end_time: Optional[float] = None
    transcription_time: Optional[float] = None
    gpt_processing_time: Optional[float] = None
    tts_generation_time: Optional[float] = None
    total_response_time: Optional[float] = None
    user_silence_time: Optional[float] = None
    interruption_count: int = 0
    error_count: int = 0
    
    @property
    def total_duration(self) -> Optional[float]:
        """Calculate total call duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def processing_efficiency(self) -> Optional[float]:
        """Calculate processing efficiency (non-silence time / total time)."""
        if self.total_duration and self.user_silence_time:
            return (self.total_duration - self.user_silence_time) / self.total_duration
        return None

class PerformanceMonitor:
    """Monitor and optimize performance metrics."""
    
    def __init__(self):
        self.active_calls: Dict[str, PerformanceMetrics] = {}
        self.metrics_history: list = []
        self.avg_response_time = 0.0
        self.avg_transcription_time = 0.0
        self.avg_gpt_time = 0.0
        self.avg_tts_time = 0.0
        
    def start_call(self, call_id: str) -> PerformanceMetrics:
        """Start monitoring a new call."""
        metrics = PerformanceMetrics(
            call_id=call_id,
            start_time=time.time()
        )
        self.active_calls[call_id] = metrics
        logger.info(f"Started performance monitoring for call: {call_id}")
        return metrics
    
    def end_call(self, call_id: str):
        """End monitoring for a call."""
        if call_id in self.active_calls:
            metrics = self.active_calls[call_id]
            metrics.end_time = time.time()
            
            # Calculate averages
            self._update_averages(metrics)
            
            # Store in history
            self.metrics_history.append(metrics)
            
            # Keep only last 100 calls in history
            if len(self.metrics_history) > 100:
                self.metrics_history.pop(0)
            
            # Clean up active calls
            del self.active_calls[call_id]
            
            logger.info(f"Ended performance monitoring for call: {call_id}")
            logger.info(f"Call metrics: {self._format_metrics(metrics)}")
    
    def _update_averages(self, metrics: PerformanceMetrics):
        """Update average performance metrics."""
        if metrics.total_response_time:
            self.avg_response_time = self._calculate_moving_average(
                self.avg_response_time, metrics.total_response_time
            )
        
        if metrics.transcription_time:
            self.avg_transcription_time = self._calculate_moving_average(
                self.avg_transcription_time, metrics.transcription_time
            )
        
        if metrics.gpt_processing_time:
            self.avg_gpt_time = self._calculate_moving_average(
                self.avg_gpt_time, metrics.gpt_processing_time
            )
        
        if metrics.tts_generation_time:
            self.avg_tts_time = self._calculate_moving_average(
                self.avg_tts_time, metrics.tts_generation_time
            )
    
    def _calculate_moving_average(self, current_avg: float, new_value: float, alpha: float = 0.1) -> float:
        """Calculate exponential moving average."""
        return alpha * new_value + (1 - alpha) * current_avg
    
    def _format_metrics(self, metrics: PerformanceMetrics) -> str:
        """Format metrics for logging."""
        return (
            f"Response: {metrics.total_response_time:.2f}s, "
            f"Transcription: {metrics.transcription_time:.2f}s, "
            f"GPT: {metrics.gpt_processing_time:.2f}s, "
            f"TTS: {metrics.tts_generation_time:.2f}s, "
            f"Efficiency: {metrics.processing_efficiency:.2%}"
        )
    
    @asynccontextmanager
    async def monitor_transcription(self, call_id: str):
        """Context manager for monitoring transcription time."""
        metrics = self.active_calls.get(call_id)
        if metrics:
            start_time = time.time()
            try:
                yield
            finally:
                metrics.transcription_time = time.time() - start_time
                logger.debug(f"Transcription time for {call_id}: {metrics.transcription_time:.3f}s")
    
    @asynccontextmanager
    async def monitor_gpt_processing(self, call_id: str):
        """Context manager for monitoring GPT processing time."""
        metrics = self.active_calls.get(call_id)
        if metrics:
            start_time = time.time()
            try:
                yield
            finally:
                metrics.gpt_processing_time = time.time() - start_time
                logger.debug(f"GPT processing time for {call_id}: {metrics.gpt_processing_time:.3f}s")
    
    @asynccontextmanager
    async def monitor_tts_generation(self, call_id: str):
        """Context manager for monitoring TTS generation time."""
        metrics = self.active_calls.get(call_id)
        if metrics:
            start_time = time.time()
            try:
                yield
            finally:
                metrics.tts_generation_time = time.time() - start_time
                logger.debug(f"TTS generation time for {call_id}: {metrics.tts_generation_time:.3f}s")
    
    @asynccontextmanager
    async def monitor_response_time(self, call_id: str):
        """Context manager for monitoring total response time."""
        metrics = self.active_calls.get(call_id)
        if metrics:
            start_time = time.time()
            try:
                yield
            finally:
                metrics.total_response_time = time.time() - start_time
                logger.debug(f"Total response time for {call_id}: {metrics.total_response_time:.3f}s")
    
    def record_interruption(self, call_id: str):
        """Record an interruption event."""
        metrics = self.active_calls.get(call_id)
        if metrics:
            metrics.interruption_count += 1
            logger.debug(f"Interruption recorded for {call_id}: {metrics.interruption_count}")
    
    def record_error(self, call_id: str):
        """Record an error event."""
        metrics = self.active_calls.get(call_id)
        if metrics:
            metrics.error_count += 1
            logger.warning(f"Error recorded for {call_id}: {metrics.error_count}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "active_calls": len(self.active_calls),
            "avg_response_time": round(self.avg_response_time, 3),
            "avg_transcription_time": round(self.avg_transcription_time, 3),
            "avg_gpt_time": round(self.avg_gpt_time, 3),
            "avg_tts_time": round(self.avg_tts_time, 3),
            "total_calls_monitored": len(self.metrics_history),
            "recent_metrics": [
                {
                    "call_id": m.call_id,
                    "total_response_time": round(m.total_response_time or 0, 3),
                    "interruption_count": m.interruption_count,
                    "error_count": m.error_count
                }
                for m in self.metrics_history[-10:]
            ]
        }
    
    def should_optimize(self) -> bool:
        """Determine if optimization is needed based on performance metrics."""
        # Trigger optimization if average response time exceeds 3 seconds
        return self.avg_response_time > 3.0
    
    def get_optimization_recommendations(self) -> list:
        """Get optimization recommendations based on performance data."""
        recommendations = []
        
        if self.avg_transcription_time > 1.0:
            recommendations.append("Consider upgrading Deepgram model or optimizing audio quality")
        
        if self.avg_gpt_time > 1.5:
            recommendations.append("Consider using faster GPT model or implementing response caching")
        
        if self.avg_tts_time > 0.8:
            recommendations.append("Consider optimizing TTS parameters or using faster voice model")
        
        if self.avg_response_time > 3.0:
            recommendations.append("Implement response streaming and parallel processing")
        
        return recommendations

# Global performance monitor instance
performance_monitor = PerformanceMonitor()