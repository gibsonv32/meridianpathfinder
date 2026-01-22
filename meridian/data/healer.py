"""Self-healing data ingestion with Try-Heal-Retry pattern."""

from pathlib import Path
from typing import Optional, Literal, Dict, Any
import hashlib
import json

import pandas as pd
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, retry_if_exception_type

from meridian.core.circuit_breaker import CircuitBreaker


class CsvFixParams(BaseModel):
    """Parameters for fixing CSV reading issues."""
    sep: str = Field(default=",", description="Delimiter: ',' '|' ';' or '\\t'")
    encoding: str = Field(default="utf-8")
    header: Optional[int] = Field(default=0)
    engine: Literal["python", "c"] = "python"
    skiprows: Optional[int] = None
    on_bad_lines: Literal["error", "skip", "warn"] = "skip"  # Added for robustness
    quotechar: Optional[str] = '"'


class DataHealer:
    """Self-healing data loader with LLM-powered error diagnosis."""
    
    def __init__(self, llm_provider, project_path: Path, circuit_breaker: Optional[CircuitBreaker] = None):
        self.llm = llm_provider
        self.project_path = project_path
        self.fix_cache_path = project_path / ".meridian" / "healer_cache.json"
        self.fix_history = self._load_cache()
        
        # Use provided circuit breaker or create new one
        if circuit_breaker:
            self.circuit_breaker = circuit_breaker
        else:
            cb_path = project_path / ".meridian" / "circuit_breaker.json"
            self.circuit_breaker = CircuitBreaker(
                max_failures=10,
                max_cost_usd=2.0,
                persistence_path=cb_path
            )
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cached fixes from disk."""
        if self.fix_cache_path.exists():
            with open(self.fix_cache_path, "r") as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Persist successful fixes to disk."""
        self.fix_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.fix_cache_path, "w") as f:
            json.dump(self.fix_history, f, indent=2)
    
    def _get_file_hash(self, filepath: Path) -> str:
        """Get hash of file's first 1KB for cache key."""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read(1024)).hexdigest()
    
    def diagnose_csv_error(self, filepath: Path, error_trace: str) -> Dict[str, Any]:
        """Use LLM to diagnose CSV loading errors."""
        # Read first 5 lines as evidence
        try:
            with open(filepath, "r", errors="replace") as f:
                snippet = "".join([f.readline() for _ in range(5)])
        except:
            snippet = "<<UNREADABLE>>"
        
        # Also check file size for context
        file_size = filepath.stat().st_size / 1024  # KB
        
        prompt = f"""CSV loading failed with error:
{error_trace}

File: {filepath.name} ({file_size:.1f} KB)
First 5 lines:
```
{snippet}
```

Diagnose the issue and return correct pandas.read_csv parameters.
Common issues: wrong delimiter, encoding, quote escaping, header row."""
        
        # Check circuit breaker before healing
        if not self.circuit_breaker.can_attempt_healing("csv_diagnosis"):
            raise RuntimeError("Circuit breaker is open - manual intervention required")
        
        try:
            # Use structured output with gpt-oss-120b (fast with speculation)
            fix = self.llm.complete_structured(
                prompt=prompt,
                schema=CsvFixParams,
                system="You are a data format expert. Diagnose CSV issues accurately."
            )
            
            # Record success
            self.circuit_breaker.record_success("csv_diagnosis")
            result = fix.model_dump()
            
            # Override comma default if semicolon detected in snippet
            if ';' in snippet and result.get('sep') == ',':
                result['sep'] = ';'
                
            return result
            
        except Exception as e:
            # Record failure
            self.circuit_breaker.record_failure("csv_diagnosis", str(e))
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((pd.errors.ParserError, UnicodeDecodeError))
    )
    def resilient_read_csv(self, filepath: Path, **kwargs) -> pd.DataFrame:
        """Self-healing CSV loader with automatic retry."""
        filepath = Path(filepath)
        cache_key = f"{filepath.name}_{self._get_file_hash(filepath)}"
        
        # Check cache first
        if cache_key in self.fix_history:
            print(f"  ℹ Using cached fix for {filepath.name}")
            kwargs.update(self.fix_history[cache_key])
        
        try:
            df = pd.read_csv(filepath, **kwargs)
            
            # Validate the DataFrame
            if df.empty:
                raise ValueError("DataFrame is empty after loading")
            if df.shape[1] == 1 and kwargs.get('sep', ',') == ',':
                raise ValueError("Only 1 column detected - likely wrong delimiter")
            
            # Success! Cache the working params
            if cache_key not in self.fix_history:
                self.fix_history[cache_key] = kwargs
                self._save_cache()
                
            return df
            
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as e:
            print(f"  ⚠ CSV loading failed: {str(e)[:100]}")
            print(f"  🔧 Attempting self-healing...")
            
            # Diagnose and get fix
            fix = self.diagnose_csv_error(filepath, str(e))
            print(f"  💡 Trying fix: sep='{fix['sep']}', encoding='{fix['encoding']}'")
            
            # Update kwargs with fix
            kwargs.update(fix)
            
            # Retry with fixed params
            df = pd.read_csv(filepath, **kwargs)
            
            # Cache successful fix
            self.fix_history[cache_key] = kwargs
            self._save_cache()
            print(f"  ✅ Self-healing successful!")
            
            return df