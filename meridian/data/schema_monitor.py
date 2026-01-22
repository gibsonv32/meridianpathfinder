"""Schema drift detection and data quality monitoring with self-healing suggestions."""

from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
import json
import hashlib

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field

from meridian.core.circuit_breaker import CircuitBreaker


class ColumnSchema(BaseModel):
    """Schema information for a single column."""
    name: str
    dtype: str
    nullable: bool
    unique_count: int
    null_count: int
    sample_values: List[Any] = Field(default_factory=list)
    statistics: Optional[Dict[str, float]] = None  # min, max, mean, std for numeric


class DatasetSchema(BaseModel):
    """Complete schema for a dataset."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    shape: Tuple[int, int]
    columns: List[ColumnSchema]
    column_order: List[str]
    fingerprint: str = ""
    
    def compute_fingerprint(self) -> str:
        """Compute a fingerprint for this schema."""
        schema_str = f"{self.shape}|{','.join(self.column_order)}|"
        schema_str += "|".join([f"{c.name}:{c.dtype}:{c.nullable}" for c in self.columns])
        self.fingerprint = hashlib.md5(schema_str.encode()).hexdigest()
        return self.fingerprint


class DriftType(BaseModel):
    """Information about detected drift."""
    drift_type: str = Field(description="Type: 'new_column', 'missing_column', 'type_change', 'distribution', 'cardinality'")
    column: str
    severity: str = Field(description="Severity: 'low', 'medium', 'high', 'critical'")
    description: str
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False


class QualityIssue(BaseModel):
    """Data quality issue detected."""
    issue_type: str = Field(description="Type: 'missing_values', 'outliers', 'duplicates', 'inconsistent_format'")
    column: Optional[str] = None
    severity: str = Field(description="Severity: 'info', 'warning', 'error'")
    description: str
    recommendation: str
    auto_fixable: bool = False
    fix_code: Optional[str] = None


class SchemaMonitor:
    """
    Monitor schema drift and data quality with self-healing recommendations.
    Tracks schema evolution over time and suggests fixes.
    """
    
    def __init__(
        self,
        project_path: Path,
        llm_provider=None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize schema monitor.
        
        Args:
            project_path: Project path for storing schemas
            llm_provider: Optional LLM for intelligent suggestions
            circuit_breaker: Optional circuit breaker for cost control
        """
        self.project_path = project_path
        self.llm = llm_provider
        self.schema_path = project_path / ".meridian" / "schemas"
        self.schema_path.mkdir(parents=True, exist_ok=True)
        
        # Schema history
        self.schema_history: Dict[str, List[DatasetSchema]] = self._load_history()
        
        # Circuit breaker
        if circuit_breaker:
            self.circuit_breaker = circuit_breaker
        else:
            cb_path = project_path / ".meridian" / "circuit_breaker.json"
            self.circuit_breaker = CircuitBreaker(
                max_failures=10,
                max_cost_usd=5.0,
                persistence_path=cb_path
            )
    
    def _load_history(self) -> Dict[str, List[DatasetSchema]]:
        """Load schema history from disk."""
        history = {}
        history_file = self.schema_path / "schema_history.json"
        
        if history_file.exists():
            with open(history_file, "r") as f:
                data = json.load(f)
                for dataset_name, schemas in data.items():
                    history[dataset_name] = [DatasetSchema(**s) for s in schemas]
        
        return history
    
    def _save_history(self):
        """Save schema history to disk."""
        history_file = self.schema_path / "schema_history.json"
        
        # Convert to JSON-serializable format
        data = {}
        for dataset_name, schemas in self.schema_history.items():
            data[dataset_name] = [s.model_dump() for s in schemas]
        
        with open(history_file, "w") as f:
            json.dump(data, f, indent=2, default=str)
    
    def extract_schema(self, df: pd.DataFrame) -> DatasetSchema:
        """
        Extract schema from a DataFrame.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Dataset schema
        """
        columns = []
        
        for col in df.columns:
            # Get column info
            series = df[col]
            dtype_str = str(series.dtype)
            
            # Statistics for numeric columns
            stats = None
            if pd.api.types.is_numeric_dtype(series):
                stats = {
                    "min": float(series.min()) if not series.isna().all() else None,
                    "max": float(series.max()) if not series.isna().all() else None,
                    "mean": float(series.mean()) if not series.isna().all() else None,
                    "std": float(series.std()) if not series.isna().all() else None,
                }
            
            # Sample values (convert to JSON-serializable)
            sample = series.dropna().head(5).tolist()
            sample = [str(v) if not isinstance(v, (int, float, str, bool, type(None))) else v for v in sample]
            
            columns.append(ColumnSchema(
                name=col,
                dtype=dtype_str,
                nullable=series.isna().any(),
                unique_count=series.nunique(),
                null_count=series.isna().sum(),
                sample_values=sample,
                statistics=stats
            ))
        
        schema = DatasetSchema(
            shape=(len(df), len(df.columns)),
            columns=columns,
            column_order=list(df.columns)
        )
        schema.compute_fingerprint()
        
        return schema
    
    def detect_drift(
        self,
        current_df: pd.DataFrame,
        dataset_name: str,
        baseline_schema: Optional[DatasetSchema] = None
    ) -> List[DriftType]:
        """
        Detect schema drift from baseline or history.
        
        Args:
            current_df: Current DataFrame
            dataset_name: Name for tracking
            baseline_schema: Optional baseline to compare against
            
        Returns:
            List of detected drifts
        """
        current_schema = self.extract_schema(current_df)
        
        # Get baseline (last known schema or provided)
        if baseline_schema is None:
            if dataset_name in self.schema_history and self.schema_history[dataset_name]:
                baseline_schema = self.schema_history[dataset_name][-1]
            else:
                # First time seeing this dataset
                self.schema_history[dataset_name] = [current_schema]
                self._save_history()
                return []
        
        drifts = []
        
        # Check for column changes
        baseline_cols = set(baseline_schema.column_order)
        current_cols = set(current_schema.column_order)
        
        # New columns
        for col in current_cols - baseline_cols:
            drifts.append(DriftType(
                drift_type="new_column",
                column=col,
                severity="medium",
                description=f"New column '{col}' detected",
                suggested_fix=f"Add '{col}' to expected schema",
                auto_fixable=True
            ))
        
        # Missing columns
        for col in baseline_cols - current_cols:
            drifts.append(DriftType(
                drift_type="missing_column",
                column=col,
                severity="high",
                description=f"Expected column '{col}' is missing",
                suggested_fix=f"df['{col}'] = None  # Add with default value",
                auto_fixable=True
            ))
        
        # Check existing columns
        baseline_col_map = {c.name: c for c in baseline_schema.columns}
        current_col_map = {c.name: c for c in current_schema.columns}
        
        for col in baseline_cols & current_cols:
            baseline_col = baseline_col_map[col]
            current_col = current_col_map[col]
            
            # Type changes
            if baseline_col.dtype != current_col.dtype:
                drifts.append(DriftType(
                    drift_type="type_change",
                    column=col,
                    severity="high",
                    description=f"Column '{col}' type changed from {baseline_col.dtype} to {current_col.dtype}",
                    suggested_fix=f"df['{col}'] = df['{col}'].astype('{baseline_col.dtype}')",
                    auto_fixable=True
                ))
            
            # Cardinality changes (for categorical)
            if not pd.api.types.is_numeric_dtype(current_df[col]):
                cardinality_change = abs(current_col.unique_count - baseline_col.unique_count)
                if cardinality_change > baseline_col.unique_count * 0.5:  # 50% change
                    drifts.append(DriftType(
                        drift_type="cardinality",
                        column=col,
                        severity="low",
                        description=f"Column '{col}' cardinality changed from {baseline_col.unique_count} to {current_col.unique_count}",
                        suggested_fix=None,
                        auto_fixable=False
                    ))
            
            # Distribution changes (for numeric)
            if baseline_col.statistics and current_col.statistics:
                if baseline_col.statistics.get('mean') and current_col.statistics.get('mean'):
                    mean_change = abs(baseline_col.statistics['mean'] - current_col.statistics['mean'])
                    if baseline_col.statistics.get('std') and baseline_col.statistics['std'] > 0:
                        if mean_change > 2 * baseline_col.statistics['std']:  # 2 std shift
                            drifts.append(DriftType(
                                drift_type="distribution",
                                column=col,
                                severity="medium",
                                description=f"Column '{col}' distribution shifted significantly",
                                suggested_fix=f"# Investigate distribution change in '{col}'",
                                auto_fixable=False
                            ))
        
        # Update history
        if current_schema.fingerprint != baseline_schema.fingerprint:
            if dataset_name not in self.schema_history:
                self.schema_history[dataset_name] = []
            self.schema_history[dataset_name].append(current_schema)
            self._save_history()
        
        return drifts
    
    def assess_quality(self, df: pd.DataFrame) -> List[QualityIssue]:
        """
        Assess data quality and provide recommendations.
        
        Args:
            df: DataFrame to assess
            
        Returns:
            List of quality issues with recommendations
        """
        issues = []
        
        # Check for missing values
        for col in df.columns:
            null_pct = df[col].isna().sum() / len(df) * 100
            if null_pct > 50:
                severity = "error"
            elif null_pct > 20:
                severity = "warning"
            elif null_pct > 0:
                severity = "info"
            else:
                continue
            
            if pd.api.types.is_numeric_dtype(df[col]):
                fix_code = f"df['{col}'].fillna(df['{col}'].median())"
            else:
                fix_code = f"df['{col}'].fillna('MISSING')"
            
            issues.append(QualityIssue(
                issue_type="missing_values",
                column=col,
                severity=severity,
                description=f"Column '{col}' has {null_pct:.1f}% missing values",
                recommendation=f"Consider imputation or removal",
                auto_fixable=True,
                fix_code=fix_code
            ))
        
        # Check for duplicates
        dup_count = df.duplicated().sum()
        if dup_count > 0:
            dup_pct = dup_count / len(df) * 100
            issues.append(QualityIssue(
                issue_type="duplicates",
                severity="warning" if dup_pct > 5 else "info",
                description=f"Dataset has {dup_count} ({dup_pct:.1f}%) duplicate rows",
                recommendation="Remove duplicates unless intentional",
                auto_fixable=True,
                fix_code="df.drop_duplicates(inplace=True)"
            ))
        
        # Check for outliers in numeric columns
        for col in df.select_dtypes(include=[np.number]).columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            outliers = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
            
            if outliers > 0:
                outlier_pct = outliers / len(df) * 100
                issues.append(QualityIssue(
                    issue_type="outliers",
                    column=col,
                    severity="warning" if outlier_pct > 5 else "info",
                    description=f"Column '{col}' has {outliers} ({outlier_pct:.1f}%) extreme outliers",
                    recommendation="Review outliers - may need capping or removal",
                    auto_fixable=True,
                    fix_code=f"df['{col}'] = df['{col}'].clip(lower=df['{col}'].quantile(0.01), upper=df['{col}'].quantile(0.99))"
                ))
        
        # Check for inconsistent string formats
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() < 100:  # Only check low-cardinality
                # Skip if column contains boolean-like values
                sample_val = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                if sample_val is not None and not isinstance(sample_val, (bool, np.bool_)):
                    # Check for case inconsistencies
                    unique_vals = df[col].dropna().unique()
                    try:
                        # Only process if values are strings
                        unique_lower = [str(v).lower() for v in unique_vals]
                        if len(unique_vals) != len(set(unique_lower)):
                            issues.append(QualityIssue(
                                issue_type="inconsistent_format",
                                column=col,
                                severity="info",
                                description=f"Column '{col}' has inconsistent casing",
                                recommendation="Standardize string casing",
                                auto_fixable=True,
                                fix_code=f"df['{col}'] = df['{col}'].astype(str).str.lower()"
                            ))
                    except:
                        # Skip if not string-like
                        pass
        
        return issues
    
    def suggest_improvements(
        self,
        df: pd.DataFrame,
        dataset_name: str
    ) -> Dict[str, Any]:
        """
        Provide comprehensive suggestions for data improvement.
        
        Args:
            df: DataFrame to analyze
            dataset_name: Name for tracking
            
        Returns:
            Dictionary with drift, quality, and improvement suggestions
        """
        # Detect drift
        drifts = self.detect_drift(df, dataset_name)
        
        # Assess quality
        quality_issues = self.assess_quality(df)
        
        # Generate improvement plan
        improvements = {
            "schema_drift": {
                "detected": len(drifts) > 0,
                "drifts": [d.model_dump() for d in drifts],
                "critical_count": sum(1 for d in drifts if d.severity in ["high", "critical"]),
                "auto_fixable": [d for d in drifts if d.auto_fixable]
            },
            "quality_assessment": {
                "total_issues": len(quality_issues),
                "by_severity": {
                    "error": sum(1 for i in quality_issues if i.severity == "error"),
                    "warning": sum(1 for i in quality_issues if i.severity == "warning"),
                    "info": sum(1 for i in quality_issues if i.severity == "info")
                },
                "issues": [i.model_dump() for i in quality_issues],
                "auto_fixable": [i for i in quality_issues if i.auto_fixable]
            },
            "recommendations": self._generate_recommendations(drifts, quality_issues)
        }
        
        # Use LLM for advanced suggestions if available
        if self.llm and self.circuit_breaker.can_attempt_healing("quality_advice"):
            try:
                improvements["llm_insights"] = self._get_llm_insights(df, drifts, quality_issues)
                self.circuit_breaker.record_success("quality_advice")
            except Exception as e:
                self.circuit_breaker.record_failure("quality_advice", str(e))
                improvements["llm_insights"] = None
        
        return improvements
    
    def _generate_recommendations(
        self,
        drifts: List[DriftType],
        quality_issues: List[QualityIssue]
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # High priority drift fixes
        critical_drifts = [d for d in drifts if d.severity in ["high", "critical"]]
        if critical_drifts:
            recommendations.append(f"🚨 Fix {len(critical_drifts)} critical schema issues immediately")
        
        # Quality improvements
        error_issues = [i for i in quality_issues if i.severity == "error"]
        if error_issues:
            recommendations.append(f"⚠️ Address {len(error_issues)} data quality errors")
        
        # Auto-fixable items
        auto_fixes = len([d for d in drifts if d.auto_fixable]) + len([i for i in quality_issues if i.auto_fixable])
        if auto_fixes > 0:
            recommendations.append(f"✅ {auto_fixes} issues can be auto-fixed with healing")
        
        # General advice
        if len(quality_issues) == 0 and len(drifts) == 0:
            recommendations.append("✨ Data quality looks good!")
        elif len(recommendations) == 0:
            recommendations.append("📊 Review minor issues when convenient")
        
        return recommendations
    
    def _get_llm_insights(
        self,
        df: pd.DataFrame,
        drifts: List[DriftType],
        quality_issues: List[QualityIssue]
    ) -> str:
        """Get LLM insights on data quality."""
        prompt = f"""Analyze this data quality report and provide actionable insights:

Schema Drift Issues: {len(drifts)}
- Critical: {sum(1 for d in drifts if d.severity == "critical")}
- High: {sum(1 for d in drifts if d.severity == "high")}

Quality Issues: {len(quality_issues)}
- Errors: {sum(1 for i in quality_issues if i.severity == "error")}
- Warnings: {sum(1 for i in quality_issues if i.severity == "warning")}

Dataset shape: {df.shape}
Columns: {list(df.columns)[:10]}

Provide 2-3 specific, actionable recommendations for improving data quality."""

        response = self.llm.complete(prompt, max_tokens=200)
        return response