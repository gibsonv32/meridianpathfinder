"""Self-healing feature engineering with automatic transformation fixes."""

from pathlib import Path
from typing import Optional, Dict, Any, List, Union
import json
import traceback
import ast
import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from meridian.core.circuit_breaker import CircuitBreaker


class FeatureTransformFix(BaseModel):
    """Suggested fix for feature transformation."""
    transform_type: str = Field(description="Type: 'fillna', 'astype', 'encode', 'scale', 'custom'")
    code: str = Field(description="Python code to apply the transformation")
    explanation: str = Field(description="Why this fix is needed")
    safe_to_apply: bool = Field(default=True, description="Whether fix is safe to auto-apply")


class FeatureHealer:
    """
    Self-healing feature engineering that automatically fixes transformation errors.
    Uses LLM to diagnose issues and suggest pandas/numpy transformations.
    """
    
    def __init__(
        self, 
        llm_provider, 
        project_path: Path,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize feature healer.
        
        Args:
            llm_provider: LLM provider for diagnosis
            project_path: Project path for caching
            circuit_breaker: Optional shared circuit breaker
        """
        self.llm = llm_provider
        self.project_path = project_path
        self.fix_cache_path = project_path / ".meridian" / "feature_healer_cache.json"
        self.fix_history = self._load_cache()
        
        # Use provided circuit breaker or create new one
        if circuit_breaker:
            self.circuit_breaker = circuit_breaker
        else:
            cb_path = project_path / ".meridian" / "circuit_breaker.json"
            self.circuit_breaker = CircuitBreaker(
                max_failures=10,
                max_cost_usd=5.0,
                persistence_path=cb_path
            )
        
        # Common transformation templates
        self.transform_templates = {
            "fillna": "df['{col}'].fillna({value})",
            "astype": "df['{col}'].astype({dtype})",
            "encode": "pd.get_dummies(df['{col}'], prefix='{col}')",
            "scale": "(df['{col}'] - df['{col}'].mean()) / df['{col}'].std()",
            "log": "np.log1p(df['{col}'].clip(lower=0))",
            "clip": "df['{col}'].clip(lower={min}, upper={max})"
        }
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cached fixes from disk."""
        if self.fix_cache_path.exists():
            with open(self.fix_cache_path, "r") as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save successful fixes to disk."""
        self.fix_cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.fix_cache_path, "w") as f:
            json.dump(self.fix_history, f, indent=2)
    
    def diagnose_transform_error(
        self, 
        column_name: str,
        data_sample: pd.Series,
        operation: str,
        error_trace: str
    ) -> FeatureTransformFix:
        """
        Diagnose feature transformation error and suggest fix.
        
        Args:
            column_name: Column that failed
            data_sample: Sample of the data
            operation: What operation was attempted
            error_trace: Error message
            
        Returns:
            Suggested fix
        """
        # Create diagnostic context
        sample_values = data_sample.head(10).to_list() if len(data_sample) > 0 else []
        dtype = str(data_sample.dtype)
        null_count = data_sample.isna().sum()
        unique_count = data_sample.nunique()
        
        prompt = f"""Feature transformation failed on column '{column_name}'.

Operation attempted: {operation}
Error: {error_trace}

Column info:
- Data type: {dtype}
- Sample values: {sample_values}
- Null count: {null_count}/{len(data_sample)}
- Unique values: {unique_count}

Diagnose the issue and provide a pandas/numpy transformation to fix it.
Common fixes:
1. Handle NaN values before numeric operations
2. Convert dtypes before mathematical operations
3. Encode categorical variables properly
4. Handle infinity/overflow in scaling

Return a safe transformation that won't fail."""

        # Check circuit breaker
        if not self.circuit_breaker.can_attempt_healing("feature_fix"):
            raise RuntimeError("Circuit breaker open - manual intervention required")
        
        try:
            # Use structured output for the fix
            fix = self.llm.complete_structured(
                prompt=prompt,
                schema=FeatureTransformFix,
                system="You are a data engineering expert. Provide safe, working pandas transformations."
            )
            
            # Validate the code is safe
            fix = self._validate_fix_safety(fix, column_name)
            
            # Record success
            self.circuit_breaker.record_success("feature_fix")
            
            return fix
            
        except Exception as e:
            # Record failure
            self.circuit_breaker.record_failure("feature_fix", str(e))
            raise
    
    def _validate_fix_safety(self, fix: FeatureTransformFix, column_name: str) -> FeatureTransformFix:
        """
        Validate that suggested fix is safe to execute.
        
        Args:
            fix: Suggested fix
            column_name: Column name
            
        Returns:
            Validated fix with safety flag
        """
        # Check for dangerous operations
        dangerous_keywords = [
            "exec", "eval", "__import__", "compile", "open",
            "subprocess", "os.system", "input", "raw_input"
        ]
        
        code_lower = fix.code.lower()
        for keyword in dangerous_keywords:
            if keyword in code_lower:
                fix.safe_to_apply = False
                fix.explanation += f" [WARNING: Contains potentially unsafe operation: {keyword}]"
                break
        
        # Try to parse as valid Python
        try:
            ast.parse(fix.code)
        except SyntaxError:
            fix.safe_to_apply = False
            fix.explanation += " [WARNING: Invalid Python syntax]"
        
        return fix
    
    def heal_transformation(
        self,
        df: pd.DataFrame,
        column: str,
        operation: str,
        fallback_value: Any = None
    ) -> pd.Series:
        """
        Attempt to heal a failed transformation.
        
        Args:
            df: DataFrame
            column: Column to transform
            operation: Operation that failed
            fallback_value: Fallback value if healing fails
            
        Returns:
            Transformed series
        """
        cache_key = f"{column}_{operation}_{str(df[column].dtype)}"
        
        # Check cache first
        if cache_key in self.fix_history:
            cached_fix = self.fix_history[cache_key]
            try:
                # Execute cached fix
                local_vars = {"df": df, "pd": pd, "np": np, "column": column}
                exec(cached_fix["code"], {}, local_vars)
                return local_vars.get("result", df[column])
            except:
                # Cached fix failed, remove it
                del self.fix_history[cache_key]
        
        # Try the original operation first
        try:
            return eval(operation, {"df": df, "pd": pd, "np": np})
        except Exception as e:
            error_trace = str(e)
            
            print(f"  ⚠ Feature transformation failed: {error_trace[:100]}")
            print(f"  🔧 Attempting self-healing for column '{column}'...")
            
            # Diagnose and get fix
            try:
                fix = self.diagnose_transform_error(
                    column, 
                    df[column],
                    operation,
                    error_trace
                )
                
                if not fix.safe_to_apply:
                    print(f"  ⚠️ Fix not safe to auto-apply: {fix.explanation}")
                    if fallback_value is not None:
                        return pd.Series([fallback_value] * len(df))
                    raise ValueError(f"Unsafe fix suggested: {fix.explanation}")
                
                print(f"  💡 Applying fix: {fix.transform_type}")
                print(f"     {fix.explanation}")
                
                # Execute the fix
                local_vars = {"df": df, "pd": pd, "np": np, "column": column}
                exec(f"result = {fix.code}", {}, local_vars)
                result = local_vars.get("result")
                
                if result is None or not isinstance(result, (pd.Series, np.ndarray)):
                    raise ValueError("Fix did not produce valid result")
                
                # Cache successful fix
                self.fix_history[cache_key] = {
                    "code": fix.code,
                    "explanation": fix.explanation,
                    "transform_type": fix.transform_type
                }
                self._save_cache()
                
                print(f"  ✅ Self-healing successful!")
                return result if isinstance(result, pd.Series) else pd.Series(result)
                
            except Exception as heal_error:
                print(f"  ❌ Healing failed: {heal_error}")
                
                # Ultimate fallback
                if fallback_value is not None:
                    print(f"  📌 Using fallback value: {fallback_value}")
                    return pd.Series([fallback_value] * len(df))
                raise
    
    def batch_heal_features(
        self,
        df: pd.DataFrame,
        transformations: Dict[str, str],
        fallback_values: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Apply multiple transformations with healing.
        
        Args:
            df: Input DataFrame
            transformations: Dict of column -> transformation code
            fallback_values: Optional fallback values per column
            
        Returns:
            Transformed DataFrame
        """
        df_result = df.copy()
        fallback_values = fallback_values or {}
        
        success_count = 0
        healed_count = 0
        
        for column, transform_code in transformations.items():
            if column not in df.columns:
                print(f"  ⚠️ Column '{column}' not found in DataFrame")
                continue
            
            try:
                # Try direct transformation first
                result = eval(transform_code, {"df": df_result, "pd": pd, "np": np})
                
                # Handle different result types
                if isinstance(result, pd.DataFrame):
                    # For operations like pd.get_dummies that return DataFrame
                    for new_col in result.columns:
                        df_result[new_col] = result[new_col]
                    if column in df_result.columns and column not in result.columns:
                        df_result = df_result.drop(columns=[column])
                elif isinstance(result, pd.Series):
                    df_result[column] = result
                else:
                    df_result[column] = result
                    
                success_count += 1
                
            except Exception:
                # Use healer
                healed_series = self.heal_transformation(
                    df_result,
                    column,
                    transform_code,
                    fallback_values.get(column)
                )
                
                # Handle healed results
                if isinstance(healed_series, pd.DataFrame):
                    for new_col in healed_series.columns:
                        df_result[new_col] = healed_series[new_col]
                    if column in df_result.columns and column not in healed_series.columns:
                        df_result = df_result.drop(columns=[column])
                else:
                    df_result[column] = healed_series
                    
                healed_count += 1
        
        print(f"\n📊 Feature Engineering Summary:")
        print(f"   Direct success: {success_count}/{len(transformations)}")
        print(f"   Self-healed: {healed_count}/{len(transformations)}")
        print(f"   Total cost: ${self.circuit_breaker.total_cost:.3f}")
        
        return df_result
    
    def suggest_transformations(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Suggest transformations for all columns based on data characteristics.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dict of column -> suggested transformation
        """
        suggestions = {}
        
        for column in df.columns:
            series = df[column]
            
            # Numeric columns
            if pd.api.types.is_numeric_dtype(series):
                if series.isna().any():
                    suggestions[column] = f"df['{column}'].fillna(df['{column}'].median())"
                elif series.min() < 0 and series.max() > 0:
                    suggestions[column] = f"(df['{column}'] - df['{column}'].mean()) / df['{column}'].std()"
                elif series.min() >= 0:
                    suggestions[column] = f"np.log1p(df['{column}'])"
            
            # Categorical columns
            elif pd.api.types.is_object_dtype(series):
                if series.nunique() < 10:
                    suggestions[column] = f"pd.get_dummies(df['{column}'], prefix='{column}')"
                else:
                    suggestions[column] = f"df['{column}'].astype('category').cat.codes"
            
            # Boolean columns
            elif pd.api.types.is_bool_dtype(series):
                suggestions[column] = f"df['{column}'].astype(int)"
        
        return suggestions