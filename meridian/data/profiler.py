"""Data profiling and quality assessment for MERIDIAN"""

import warnings
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path
import json

from meridian.logging_config import get_logger
from meridian.utils.exceptions import DataError, ErrorContext

logger = get_logger("meridian.data.profiler")

warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class ColumnProfile:
    """Profile information for a single column"""
    name: str
    dtype: str
    count: int
    null_count: int
    null_percentage: float
    unique_count: int
    unique_percentage: float
    
    # Statistics (for numeric)
    mean: Optional[float] = None
    median: Optional[float] = None
    std: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    
    # Categories (for categorical)
    top_categories: Optional[Dict[str, int]] = None
    category_distribution: Optional[Dict[str, float]] = None
    
    # Quality metrics
    zeros_count: int = 0
    negative_count: int = 0
    outlier_count: int = 0
    outlier_percentage: float = 0.0
    
    # Data quality issues
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class DataProfile:
    """Complete data profile"""
    n_rows: int
    n_columns: int
    memory_usage_mb: float
    column_profiles: Dict[str, ColumnProfile]
    
    # Data types summary
    numeric_columns: List[str]
    categorical_columns: List[str]
    datetime_columns: List[str]
    text_columns: List[str]
    
    # Quality summary
    total_missing_values: int
    missing_value_percentage: float
    duplicate_rows: int
    duplicate_percentage: float
    
    # Correlations
    high_correlations: List[Tuple[str, str, float]] = field(default_factory=list)
    constant_columns: List[str] = field(default_factory=list)
    
    # Issues and recommendations
    critical_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "n_rows": self.n_rows,
            "n_columns": self.n_columns,
            "memory_usage_mb": self.memory_usage_mb,
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "datetime_columns": self.datetime_columns,
            "text_columns": self.text_columns,
            "total_missing_values": self.total_missing_values,
            "missing_value_percentage": self.missing_value_percentage,
            "duplicate_rows": self.duplicate_rows,
            "duplicate_percentage": self.duplicate_percentage,
            "high_correlations": self.high_correlations,
            "constant_columns": self.constant_columns,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "columns": {name: prof.to_dict() for name, prof in self.column_profiles.items()}
        }
    
    def save(self, path: Path) -> None:
        """Save profile to JSON"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
    
    def get_quality_score(self) -> float:
        """Calculate overall data quality score (0-100)"""
        score = 100.0
        
        # Deduct for missing values
        score -= min(self.missing_value_percentage, 20)
        
        # Deduct for duplicates
        score -= min(self.duplicate_percentage * 0.5, 10)
        
        # Deduct for constant columns
        if self.constant_columns:
            score -= len(self.constant_columns) * 2
        
        # Deduct for critical issues
        score -= len(self.critical_issues) * 5
        
        # Deduct for high correlations (redundancy)
        score -= min(len(self.high_correlations) * 2, 10)
        
        return max(score, 0)


class DataProfiler:
    """Comprehensive data profiling"""
    
    def __init__(
        self,
        outlier_method: str = "iqr",
        outlier_threshold: float = 1.5,
        correlation_threshold: float = 0.95,
        cardinality_threshold: int = 50,
        text_length_threshold: int = 100
    ):
        """
        Initialize profiler.
        
        Args:
            outlier_method: Method for outlier detection ("iqr", "zscore", "isolation")
            outlier_threshold: Threshold for outlier detection
            correlation_threshold: Threshold for high correlation warning
            cardinality_threshold: Max unique values for categorical
            text_length_threshold: Min avg length to identify text columns
        """
        self.outlier_method = outlier_method
        self.outlier_threshold = outlier_threshold
        self.correlation_threshold = correlation_threshold
        self.cardinality_threshold = cardinality_threshold
        self.text_length_threshold = text_length_threshold
    
    def profile(self, df: pd.DataFrame) -> DataProfile:
        """
        Generate comprehensive data profile.
        
        Args:
            df: DataFrame to profile
            
        Returns:
            DataProfile object
        """
        logger.info(f"Profiling data with shape {df.shape}")
        
        with ErrorContext("data_profiling", n_rows=len(df), n_cols=len(df.columns)):
            # Basic statistics
            n_rows = len(df)
            n_columns = len(df.columns)
            memory_usage_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
            
            # Duplicates
            duplicate_rows = df.duplicated().sum()
            duplicate_percentage = (duplicate_rows / n_rows * 100) if n_rows > 0 else 0
            
            # Profile each column
            column_profiles = {}
            numeric_columns = []
            categorical_columns = []
            datetime_columns = []
            text_columns = []
            
            for col in df.columns:
                col_profile = self._profile_column(df[col])
                column_profiles[col] = col_profile
                
                # Classify column type
                if col_profile.dtype in ['int64', 'float64', 'int32', 'float32']:
                    numeric_columns.append(col)
                elif col_profile.dtype in ['datetime64[ns]', 'datetime64']:
                    datetime_columns.append(col)
                elif self._is_text_column(df[col]):
                    text_columns.append(col)
                else:
                    categorical_columns.append(col)
            
            # Calculate correlations for numeric columns
            high_correlations = []
            if len(numeric_columns) > 1:
                corr_matrix = df[numeric_columns].corr()
                for i in range(len(numeric_columns)):
                    for j in range(i+1, len(numeric_columns)):
                        corr_value = abs(corr_matrix.iloc[i, j])
                        if corr_value > self.correlation_threshold:
                            high_correlations.append(
                                (numeric_columns[i], numeric_columns[j], corr_value)
                            )
            
            # Find constant columns
            constant_columns = [
                col for col, prof in column_profiles.items()
                if prof.unique_count == 1
            ]
            
            # Calculate total missing values
            total_missing = sum(prof.null_count for prof in column_profiles.values())
            missing_percentage = (total_missing / (n_rows * n_columns) * 100) if n_rows > 0 else 0
            
            # Compile issues and recommendations
            critical_issues = []
            warnings = []
            recommendations = []
            
            # Check for critical issues
            if missing_percentage > 50:
                critical_issues.append(f"Very high missing data: {missing_percentage:.1f}%")
            
            if duplicate_percentage > 20:
                critical_issues.append(f"High duplicate rows: {duplicate_percentage:.1f}%")
            
            if constant_columns:
                warnings.append(f"Constant columns found: {constant_columns}")
                recommendations.append("Consider removing constant columns")
            
            if high_correlations:
                warnings.append(f"High correlations found: {len(high_correlations)} pairs")
                recommendations.append("Consider removing redundant features")
            
            # Add column-specific issues
            for col, prof in column_profiles.items():
                critical_issues.extend([f"{col}: {issue}" for issue in prof.issues])
                warnings.extend([f"{col}: {warning}" for warning in prof.warnings])
            
            # General recommendations
            if missing_percentage > 10:
                recommendations.append("Implement missing value imputation strategy")
            
            if duplicate_percentage > 5:
                recommendations.append("Remove or investigate duplicate rows")
            
            if len(numeric_columns) > 20:
                recommendations.append("Consider dimensionality reduction")
            
            profile = DataProfile(
                n_rows=n_rows,
                n_columns=n_columns,
                memory_usage_mb=memory_usage_mb,
                column_profiles=column_profiles,
                numeric_columns=numeric_columns,
                categorical_columns=categorical_columns,
                datetime_columns=datetime_columns,
                text_columns=text_columns,
                total_missing_values=total_missing,
                missing_value_percentage=missing_percentage,
                duplicate_rows=duplicate_rows,
                duplicate_percentage=duplicate_percentage,
                high_correlations=high_correlations,
                constant_columns=constant_columns,
                critical_issues=critical_issues,
                warnings=warnings,
                recommendations=recommendations
            )
            
            quality_score = profile.get_quality_score()
            logger.info(f"Data profiling complete. Quality score: {quality_score:.1f}/100")
            
            return profile
    
    def _profile_column(self, series: pd.Series) -> ColumnProfile:
        """Profile a single column"""
        col_name = series.name
        dtype = str(series.dtype)
        count = len(series)
        
        # Missing values
        null_count = series.isna().sum()
        null_percentage = (null_count / count * 100) if count > 0 else 0
        
        # Unique values
        unique_count = series.nunique()
        unique_percentage = (unique_count / count * 100) if count > 0 else 0
        
        profile = ColumnProfile(
            name=col_name,
            dtype=dtype,
            count=count,
            null_count=null_count,
            null_percentage=null_percentage,
            unique_count=unique_count,
            unique_percentage=unique_percentage
        )
        
        # Remove nulls for further analysis
        series_clean = series.dropna()
        
        if len(series_clean) == 0:
            profile.issues.append("Column is entirely null")
            return profile
        
        # Numeric column analysis
        if series.dtype in ['int64', 'float64', 'int32', 'float32']:
            profile.mean = series_clean.mean()
            profile.median = series_clean.median()
            profile.std = series_clean.std()
            profile.min = series_clean.min()
            profile.max = series_clean.max()
            profile.q25 = series_clean.quantile(0.25)
            profile.q75 = series_clean.quantile(0.75)
            profile.skewness = series_clean.skew()
            profile.kurtosis = series_clean.kurtosis()
            
            # Count zeros and negatives
            profile.zeros_count = (series_clean == 0).sum()
            profile.negative_count = (series_clean < 0).sum()
            
            # Detect outliers
            outliers = self._detect_outliers(series_clean)
            profile.outlier_count = outliers.sum()
            profile.outlier_percentage = (profile.outlier_count / len(series_clean) * 100)
            
            # Add warnings
            if profile.outlier_percentage > 5:
                profile.warnings.append(f"High outlier percentage: {profile.outlier_percentage:.1f}%")
            
            if abs(profile.skewness) > 2:
                profile.warnings.append(f"Highly skewed distribution: {profile.skewness:.2f}")
            
            if profile.std == 0:
                profile.issues.append("Zero variance (constant values)")
            
            # Recommendations
            if profile.outlier_percentage > 5:
                profile.recommendations.append("Consider outlier treatment")
            
            if abs(profile.skewness) > 1:
                profile.recommendations.append("Consider log or power transformation")
        
        # Categorical column analysis
        else:
            # Get value counts
            value_counts = series_clean.value_counts()
            
            # Top categories
            top_k = min(10, len(value_counts))
            profile.top_categories = value_counts.head(top_k).to_dict()
            
            # Category distribution
            profile.category_distribution = (value_counts / len(series_clean)).to_dict()
            
            # Check for high cardinality
            if unique_count > self.cardinality_threshold and unique_percentage > 50:
                profile.warnings.append(f"High cardinality: {unique_count} unique values")
                profile.recommendations.append("Consider encoding or grouping categories")
            
            # Check for rare categories
            rare_categories = value_counts[value_counts < 5].index.tolist()
            if len(rare_categories) > 10:
                profile.warnings.append(f"Many rare categories: {len(rare_categories)}")
                profile.recommendations.append("Consider grouping rare categories")
        
        # General issues
        if null_percentage > 50:
            profile.issues.append(f"High missing values: {null_percentage:.1f}%")
        elif null_percentage > 20:
            profile.warnings.append(f"Significant missing values: {null_percentage:.1f}%")
        
        return profile
    
    def _detect_outliers(self, series: pd.Series) -> pd.Series:
        """Detect outliers in numeric series"""
        if self.outlier_method == "iqr":
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - self.outlier_threshold * IQR
            upper_bound = Q3 + self.outlier_threshold * IQR
            return (series < lower_bound) | (series > upper_bound)
        
        elif self.outlier_method == "zscore":
            z_scores = np.abs(stats.zscore(series))
            return z_scores > self.outlier_threshold
        
        elif self.outlier_method == "isolation":
            # Simplified isolation forest logic
            from sklearn.ensemble import IsolationForest
            iso = IsolationForest(contamination=0.1, random_state=42)
            outliers = iso.fit_predict(series.values.reshape(-1, 1))
            return pd.Series(outliers == -1, index=series.index)
        
        else:
            raise ValueError(f"Unknown outlier method: {self.outlier_method}")
    
    def _is_text_column(self, series: pd.Series) -> bool:
        """Check if column contains text data"""
        if series.dtype != 'object':
            return False
        
        # Sample for efficiency
        sample = series.dropna().head(100)
        if len(sample) == 0:
            return False
        
        # Check average string length
        avg_length = sample.astype(str).str.len().mean()
        
        # Check if strings contain spaces (likely text)
        contains_spaces = sample.astype(str).str.contains(' ').any()
        
        return avg_length > self.text_length_threshold or contains_spaces
    
    def generate_report(self, profile: DataProfile) -> str:
        """Generate text report from profile"""
        lines = []
        lines.append("=" * 60)
        lines.append("DATA QUALITY REPORT")
        lines.append("=" * 60)
        lines.append(f"Quality Score: {profile.get_quality_score():.1f}/100")
        lines.append("")
        
        # Basic info
        lines.append("DATASET OVERVIEW")
        lines.append("-" * 40)
        lines.append(f"Rows: {profile.n_rows:,}")
        lines.append(f"Columns: {profile.n_columns}")
        lines.append(f"Memory Usage: {profile.memory_usage_mb:.2f} MB")
        lines.append(f"Missing Values: {profile.total_missing_values:,} ({profile.missing_value_percentage:.1f}%)")
        lines.append(f"Duplicate Rows: {profile.duplicate_rows:,} ({profile.duplicate_percentage:.1f}%)")
        lines.append("")
        
        # Column types
        lines.append("COLUMN TYPES")
        lines.append("-" * 40)
        lines.append(f"Numeric: {len(profile.numeric_columns)} columns")
        lines.append(f"Categorical: {len(profile.categorical_columns)} columns")
        lines.append(f"Datetime: {len(profile.datetime_columns)} columns")
        lines.append(f"Text: {len(profile.text_columns)} columns")
        lines.append("")
        
        # Issues
        if profile.critical_issues:
            lines.append("CRITICAL ISSUES")
            lines.append("-" * 40)
            for issue in profile.critical_issues:
                lines.append(f"❌ {issue}")
            lines.append("")
        
        if profile.warnings:
            lines.append("WARNINGS")
            lines.append("-" * 40)
            for warning in profile.warnings[:10]:  # Limit to 10
                lines.append(f"⚠️  {warning}")
            if len(profile.warnings) > 10:
                lines.append(f"... and {len(profile.warnings) - 10} more warnings")
            lines.append("")
        
        # Recommendations
        if profile.recommendations:
            lines.append("RECOMMENDATIONS")
            lines.append("-" * 40)
            for rec in profile.recommendations:
                lines.append(f"→ {rec}")
            lines.append("")
        
        # Column details
        lines.append("COLUMN DETAILS")
        lines.append("-" * 40)
        for col_name, col_prof in profile.column_profiles.items():
            lines.append(f"\n{col_name} ({col_prof.dtype})")
            lines.append(f"  Missing: {col_prof.null_percentage:.1f}%")
            lines.append(f"  Unique: {col_prof.unique_count}")
            
            if col_prof.mean is not None:
                lines.append(f"  Mean: {col_prof.mean:.2f}, Std: {col_prof.std:.2f}")
                lines.append(f"  Range: [{col_prof.min:.2f}, {col_prof.max:.2f}]")
                if col_prof.outlier_percentage > 0:
                    lines.append(f"  Outliers: {col_prof.outlier_percentage:.1f}%")
        
        return "\n".join(lines)