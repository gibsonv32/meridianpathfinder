"""Data quality advisor that proactively suggests improvements and auto-fixes issues."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

from meridian.data.healer import DataHealer
from meridian.data.feature_healer import FeatureHealer
from meridian.data.schema_monitor import SchemaMonitor, DriftType, QualityIssue
from meridian.core.circuit_breaker import CircuitBreaker


class QualityAdvisor:
    """
    Unified data quality advisor that combines healing, monitoring, and proactive suggestions.
    Acts as the orchestrator for all self-healing data operations.
    """
    
    def __init__(
        self,
        project_path: Path,
        llm_provider=None,
        circuit_breaker: Optional[CircuitBreaker] = None
    ):
        """
        Initialize quality advisor.
        
        Args:
            project_path: Project path
            llm_provider: LLM provider for intelligent suggestions
            circuit_breaker: Shared circuit breaker for cost control
        """
        self.project_path = project_path
        self.llm = llm_provider
        
        # Initialize circuit breaker (shared across all components)
        if circuit_breaker:
            self.circuit_breaker = circuit_breaker
        else:
            cb_path = project_path / ".meridian" / "circuit_breaker.json"
            self.circuit_breaker = CircuitBreaker(
                max_failures=15,
                max_cost_usd=10.0,
                persistence_path=cb_path
            )
        
        # Initialize components with shared circuit breaker
        self.data_healer = DataHealer(llm_provider, project_path, self.circuit_breaker)
        self.feature_healer = FeatureHealer(llm_provider, project_path, self.circuit_breaker)
        self.schema_monitor = SchemaMonitor(project_path, llm_provider, self.circuit_breaker)
        
        # Track fixes applied
        self.fixes_applied = []
    
    def load_and_heal(
        self,
        filepath: Path,
        dataset_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load data with full self-healing and quality assessment.
        
        Args:
            filepath: Path to data file
            dataset_name: Optional name for tracking
            
        Returns:
            Healed DataFrame
        """
        dataset_name = dataset_name or filepath.stem
        
        print(f"\n{'=' * 60}")
        print(f"📊 QUALITY ADVISOR: Loading {filepath.name}")
        print(f"{'=' * 60}")
        
        # Step 1: Load with healing
        print("\n1️⃣ Loading data with self-healing...")
        try:
            df = self.data_healer.resilient_read_csv(filepath)
            print(f"   ✅ Data loaded successfully")
            self.fixes_applied.append(("csv_loading", "success"))
        except Exception as e:
            print(f"   ❌ Failed to load: {e}")
            raise
        
        # Step 2: Detect schema drift
        print("\n2️⃣ Checking schema drift...")
        drifts = self.schema_monitor.detect_drift(df, dataset_name)
        if drifts:
            print(f"   ⚠️ Detected {len(drifts)} schema changes")
            self._handle_drift(df, drifts)
        else:
            print(f"   ✅ Schema stable")
        
        # Step 3: Assess quality
        print("\n3️⃣ Assessing data quality...")
        quality_issues = self.schema_monitor.assess_quality(df)
        print(f"   Found {len(quality_issues)} quality issues")
        
        # Step 4: Auto-fix quality issues
        if quality_issues:
            df = self._fix_quality_issues(df, quality_issues)
        
        # Step 5: Generate report
        print("\n4️⃣ Generating quality report...")
        report = self._generate_report(df, dataset_name, drifts, quality_issues)
        
        return df
    
    def _handle_drift(self, df: pd.DataFrame, drifts: List[DriftType]) -> pd.DataFrame:
        """Handle detected schema drift."""
        critical_drifts = [d for d in drifts if d.severity in ["high", "critical"]]
        
        for drift in critical_drifts[:5]:  # Limit to 5 auto-fixes
            print(f"   🔧 Fixing: {drift.description}")
            
            if drift.drift_type == "missing_column" and drift.auto_fixable:
                # Add missing column with default value
                df[drift.column] = None
                self.fixes_applied.append((f"add_{drift.column}", "auto"))
                
            elif drift.drift_type == "type_change" and drift.suggested_fix:
                # Try to convert type
                try:
                    exec(drift.suggested_fix, {"df": df})
                    self.fixes_applied.append((f"convert_{drift.column}", "auto"))
                except:
                    print(f"      ⚠️ Could not apply fix: {drift.suggested_fix}")
        
        return df
    
    def _fix_quality_issues(self, df: pd.DataFrame, issues: List[QualityIssue]) -> pd.DataFrame:
        """Auto-fix quality issues where possible."""
        # Group issues by severity
        errors = [i for i in issues if i.severity == "error" and i.auto_fixable]
        warnings = [i for i in issues if i.severity == "warning" and i.auto_fixable]
        
        fixed_count = 0
        max_fixes = 10  # Limit auto-fixes
        
        # Fix errors first
        for issue in errors[:max_fixes]:
            if issue.fix_code and self.circuit_breaker.can_attempt_healing("quality_fix"):
                try:
                    print(f"   🔧 Fixing {issue.issue_type} in {issue.column or 'dataset'}")
                    
                    # Execute fix - skip boolean columns for string operations
                    if issue.column and issue.column in df.columns:
                        if df[issue.column].dtype == 'bool' and '.str.' in issue.fix_code:
                            print(f"      ⚠️ Skipping string operation on boolean column")
                            continue
                    
                    # Execute fix
                    local_vars = {"df": df, "pd": pd, "np": np}
                    exec(issue.fix_code, {}, local_vars)
                    df = local_vars.get("df", df)
                    
                    self.fixes_applied.append((issue.issue_type, issue.column))
                    self.circuit_breaker.record_success("quality_fix", 0.005)  # Small cost
                    fixed_count += 1
                    
                except Exception as e:
                    print(f"      ⚠️ Fix failed: {str(e)[:100]}")
                    self.circuit_breaker.record_failure("quality_fix", str(e), 0.005)
        
        # Fix warnings if budget allows
        if fixed_count < max_fixes:
            for issue in warnings[:(max_fixes - fixed_count)]:
                if issue.fix_code and self.circuit_breaker.can_attempt_healing("quality_fix"):
                    try:
                        # Skip boolean columns for string operations
                        if issue.column and issue.column in df.columns:
                            if df[issue.column].dtype == 'bool' and '.str.' in issue.fix_code:
                                continue
                        
                        local_vars = {"df": df, "pd": pd, "np": np}
                        exec(issue.fix_code, {}, local_vars)
                        df = local_vars.get("df", df)
                        
                        self.fixes_applied.append((issue.issue_type, issue.column))
                        self.circuit_breaker.record_success("quality_fix", 0.005)
                        fixed_count += 1
                        
                    except:
                        pass  # Silently skip warning fixes that fail
        
        if fixed_count > 0:
            print(f"   ✅ Applied {fixed_count} automatic fixes")
        
        return df
    
    def _generate_report(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        drifts: List[DriftType],
        quality_issues: List[QualityIssue]
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        
        # Get improvement suggestions
        improvements = self.schema_monitor.suggest_improvements(df, dataset_name)
        
        # Summary statistics
        report = {
            "dataset": dataset_name,
            "shape": df.shape,
            "memory_usage": f"{df.memory_usage(deep=True).sum() / 1024**2:.2f} MB",
            "schema_drift": {
                "detected": len(drifts) > 0,
                "count": len(drifts),
                "critical": sum(1 for d in drifts if d.severity in ["high", "critical"])
            },
            "quality": {
                "total_issues": len(quality_issues),
                "errors": sum(1 for i in quality_issues if i.severity == "error"),
                "warnings": sum(1 for i in quality_issues if i.severity == "warning"),
                "auto_fixed": len([f for f in self.fixes_applied if f[1] == "auto"])
            },
            "healing": {
                "csv_fixes": len(self.data_healer.fix_history),
                "feature_fixes": len(self.feature_healer.fix_history),
                "total_cost": f"${self.circuit_breaker.total_cost:.3f}",
                "budget_remaining": f"${self.circuit_breaker.max_cost - self.circuit_breaker.total_cost:.2f}"
            },
            "recommendations": improvements.get("recommendations", [])
        }
        
        # Print summary
        print(f"\n📋 Quality Report Summary:")
        print(f"   Shape: {report['shape']}")
        print(f"   Memory: {report['memory_usage']}")
        print(f"   Issues fixed: {report['quality']['auto_fixed']}")
        print(f"   Cost: {report['healing']['total_cost']}")
        
        if report['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in report['recommendations'][:3]:
                print(f"   {rec}")
        
        return report
    
    def suggest_pipeline_improvements(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest improvements for ML pipeline based on data quality.
        
        Args:
            df: DataFrame to analyze
            target_col: Optional target column for ML
            
        Returns:
            Pipeline improvement suggestions
        """
        suggestions = {
            "preprocessing": [],
            "feature_engineering": [],
            "validation": []
        }
        
        # Preprocessing suggestions
        for col in df.columns:
            if col == target_col:
                continue
            
            # Missing values
            null_pct = df[col].isna().sum() / len(df) * 100
            if null_pct > 30:
                suggestions["preprocessing"].append(
                    f"Consider dropping '{col}' (>{null_pct:.0f}% missing)"
                )
            elif null_pct > 0:
                if pd.api.types.is_numeric_dtype(df[col]):
                    suggestions["preprocessing"].append(
                        f"Impute '{col}' with median/mean"
                    )
                else:
                    suggestions["preprocessing"].append(
                        f"Impute '{col}' with mode or 'MISSING'"
                    )
        
        # Feature engineering suggestions
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            suggestions["feature_engineering"].append(
                "Consider polynomial features for numeric columns"
            )
        
        categorical_cols = df.select_dtypes(include=['object']).columns
        high_cardinality = [c for c in categorical_cols if df[c].nunique() > 20]
        if high_cardinality:
            suggestions["feature_engineering"].append(
                f"Use target encoding for high-cardinality columns: {high_cardinality[:3]}"
            )
        
        # Validation suggestions
        if df.duplicated().any():
            suggestions["validation"].append(
                "Remove duplicates before train/test split"
            )
        
        if target_col and target_col in df.columns:
            if pd.api.types.is_numeric_dtype(df[target_col]):
                if df[target_col].nunique() < 10:
                    suggestions["validation"].append(
                        "Target looks categorical - ensure proper problem framing"
                    )
            
            # Class imbalance
            if df[target_col].nunique() == 2:
                class_balance = df[target_col].value_counts(normalize=True)
                if class_balance.min() < 0.2:
                    suggestions["validation"].append(
                        "Address class imbalance with SMOTE or class weights"
                    )
        
        return suggestions
    
    def monitor_pipeline_health(self) -> Dict[str, Any]:
        """
        Monitor overall pipeline health based on healing history.
        
        Returns:
            Pipeline health metrics
        """
        health = {
            "status": "healthy",
            "metrics": {
                "csv_healing_rate": 0,
                "feature_healing_rate": 0,
                "circuit_breaker_usage": 0,
                "cached_fixes": 0
            },
            "alerts": []
        }
        
        # Calculate healing rates
        total_csv_attempts = len(self.data_healer.fix_history) + len(self.fixes_applied)
        if total_csv_attempts > 0:
            health["metrics"]["csv_healing_rate"] = len(self.data_healer.fix_history) / total_csv_attempts
        
        # Circuit breaker usage
        cb_status = self.circuit_breaker.get_status()
        health["metrics"]["circuit_breaker_usage"] = cb_status["total_cost"] / cb_status["max_cost"]
        
        # Cached fixes
        health["metrics"]["cached_fixes"] = len(self.data_healer.fix_history) + len(self.feature_healer.fix_history)
        
        # Generate alerts
        if health["metrics"]["circuit_breaker_usage"] > 0.8:
            health["alerts"].append("⚠️ Circuit breaker near limit (>80% budget used)")
            health["status"] = "warning"
        
        if cb_status["state"] == "open":
            health["alerts"].append("🚨 Circuit breaker OPEN - healing disabled")
            health["status"] = "critical"
        
        if health["metrics"]["csv_healing_rate"] < 0.5 and total_csv_attempts > 5:
            health["alerts"].append("⚠️ Low healing success rate - review data sources")
            health["status"] = "warning"
        
        return health