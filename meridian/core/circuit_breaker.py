"""Circuit breaker for controlling self-healing costs and preventing runaway LLM usage."""

import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
from pathlib import Path


class CircuitBreaker:
    """
    Circuit breaker pattern for self-healing operations.
    Prevents excessive LLM costs and tracks healing attempts.
    """
    
    def __init__(
        self,
        max_failures: int = 10,
        max_cost_usd: float = 5.0,
        reset_timeout: int = 3600,  # seconds
        persistence_path: Optional[Path] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            max_failures: Maximum failures before opening circuit
            max_cost_usd: Maximum cost in USD before opening
            reset_timeout: Seconds before attempting reset after open
            persistence_path: Path to persist state across restarts
        """
        self.max_failures = max_failures
        self.max_cost = max_cost_usd
        self.reset_timeout = reset_timeout
        self.persistence_path = persistence_path
        
        # State: closed, open, half_open
        self.state = "closed"
        self.failures = 0
        self.total_cost = 0.0
        self.last_failure_time = None
        self.healing_history = []
        
        # Cost estimates per operation (conservative)
        self.cost_estimates = {
            "csv_diagnosis": 0.01,
            "feature_fix": 0.02,
            "code_generation": 0.05,
            "schema_detection": 0.01
        }
        
        # Load persisted state if available
        if persistence_path and persistence_path.exists():
            self._load_state()
    
    def can_attempt_healing(self, operation_type: str = "csv_diagnosis") -> bool:
        """
        Check if healing attempt is allowed.
        
        Args:
            operation_type: Type of healing operation
            
        Returns:
            True if healing can proceed
        """
        # Update state based on timeout
        self._check_timeout()
        
        if self.state == "open":
            return False
        
        # Check cost budget
        estimated_cost = self.cost_estimates.get(operation_type, 0.02)
        if self.total_cost + estimated_cost > self.max_cost:
            self._open_circuit("Cost limit exceeded")
            return False
        
        return True
    
    def record_success(self, operation_type: str, actual_cost: Optional[float] = None):
        """
        Record successful healing attempt.
        
        Args:
            operation_type: Type of operation
            actual_cost: Actual cost if known
        """
        cost = actual_cost or self.cost_estimates.get(operation_type, 0.02)
        self.total_cost += cost
        
        # Reset failure count on success
        if self.state == "half_open":
            self.state = "closed"
            self.failures = 0
        
        # Log healing
        self.healing_history.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation_type,
            "status": "success",
            "cost": cost
        })
        
        self._save_state()
    
    def record_failure(self, operation_type: str, error: str, actual_cost: Optional[float] = None):
        """
        Record failed healing attempt.
        
        Args:
            operation_type: Type of operation
            error: Error message
            actual_cost: Actual cost if known
        """
        cost = actual_cost or self.cost_estimates.get(operation_type, 0.02)
        self.total_cost += cost
        self.failures += 1
        self.last_failure_time = time.time()
        
        # Log healing
        self.healing_history.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation_type,
            "status": "failure",
            "error": error[:200],  # Truncate long errors
            "cost": cost
        })
        
        # Check if circuit should open
        if self.failures >= self.max_failures:
            self._open_circuit(f"Max failures ({self.max_failures}) exceeded")
        elif self.state == "half_open":
            # Failed in half-open state, reopen
            self._open_circuit("Failure in half-open state")
        
        self._save_state()
    
    def _open_circuit(self, reason: str):
        """Open the circuit breaker."""
        self.state = "open"
        self.last_failure_time = time.time()
        
        # Create detailed error message
        error_msg = (
            f"Circuit breaker OPEN: {reason}\n"
            f"  Failures: {self.failures}/{self.max_failures}\n"
            f"  Cost: ${self.total_cost:.2f}/${self.max_cost:.2f}\n"
            f"  Manual intervention required or wait {self.reset_timeout}s"
        )
        
        print(f"⚠️  {error_msg}")
        self._save_state()
        
        raise RuntimeError(error_msg)
    
    def _check_timeout(self):
        """Check if circuit can be reset after timeout."""
        if self.state == "open" and self.last_failure_time:
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.reset_timeout:
                self.state = "half_open"
                print("ℹ️  Circuit breaker entering half-open state (testing recovery)")
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self.state = "closed"
        self.failures = 0
        # Don't reset cost - keep tracking total spend
        print("✓ Circuit breaker manually reset")
        self._save_state()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "state": self.state,
            "failures": self.failures,
            "max_failures": self.max_failures,
            "total_cost": round(self.total_cost, 2),
            "max_cost": self.max_cost,
            "budget_remaining": round(self.max_cost - self.total_cost, 2),
            "recent_healings": self.healing_history[-5:]  # Last 5
        }
    
    def _save_state(self):
        """Persist state to disk."""
        if not self.persistence_path:
            return
        
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        
        state_data = {
            "state": self.state,
            "failures": self.failures,
            "total_cost": self.total_cost,
            "last_failure_time": self.last_failure_time,
            "healing_history": self.healing_history[-100:]  # Keep last 100
        }
        
        with open(self.persistence_path, "w") as f:
            json.dump(state_data, f, indent=2)
    
    def _load_state(self):
        """Load persisted state from disk."""
        if not self.persistence_path or not self.persistence_path.exists():
            return
        
        try:
            with open(self.persistence_path, "r") as f:
                state_data = json.load(f)
            
            self.state = state_data.get("state", "closed")
            self.failures = state_data.get("failures", 0)
            self.total_cost = state_data.get("total_cost", 0.0)
            self.last_failure_time = state_data.get("last_failure_time")
            self.healing_history = state_data.get("healing_history", [])
        except Exception as e:
            print(f"Warning: Could not load circuit breaker state: {e}")