"""Data Quality and Preprocessing Module for MERIDIAN"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class DataQualityReport:
    """Comprehensive data quality assessment report"""
    
    dataset_name: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Basic info
    n_rows: int = 0
    n_columns: int = 0
    memory_usage_mb: float = 0.0
    
    # Data types
    column_types: Dict[str, str] = field(default_factory=dict)
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    datetime_columns: List[str] = field(default_factory=list)
    
    # Missing values
    missing_counts: Dict[str, int] = field(default_factory=dict)
    missing_percentages: Dict[str, float] = field(default_factory=dict)
    columns_with_missing: List[str] = field(default_factory=list)
    
    # Duplicates
    n_duplicates: int = 0
    duplicate_percentage: float = 0.0
    
    # Outliers (for numeric columns)
    outlier_counts: Dict[str, int] = field(default_factory=dict)
    outlier_methods: Dict[str, str] = field(default_factory=dict)
    
    # Statistical summary
    numeric_summary: Dict[str, Dict[str, float]] = field(default_factory=dict)
    categorical_summary: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Data issues
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Quality scores
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    validity_score: float = 0.0
    overall_quality_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            "dataset_name": self.dataset_name,
            "timestamp": self.timestamp,
            "basic_info": {
                "n_rows": self.n_rows,
                "n_columns": self.n_columns,
                "memory_usage_mb": self.memory_usage_mb
            },
            "data_types": {
                "column_types": self.column_types,
                "numeric_columns": self.numeric_columns,
                "categorical_columns": self.categorical_columns,
                "datetime_columns": self.datetime_columns
            },
            "missing_values": {
                "counts": self.missing_counts,
                "percentages": self.missing_percentages,
                "columns_with_missing": self.columns_with_missing
            },
            "duplicates": {
                "n_duplicates": self.n_duplicates,
                "percentage": self.duplicate_percentage
            },
            "outliers": {
                "counts": self.outlier_counts,
                "methods": self.outlier_methods
            },
            "summaries": {
                "numeric": self.numeric_summary,
                "categorical": self.categorical_summary
            },
            "quality_assessment": {
                "issues": self.issues,
                "warnings": self.warnings,
                "recommendations": self.recommendations
            },
            "quality_scores": {
                "completeness": self.completeness_score,
                "consistency": self.consistency_score,
                "validity": self.validity_score,
                "overall": self.overall_quality_score
            }
        }


class DataQualityAnalyzer:
    """Analyze data quality and generate comprehensive reports"""
    
    def __init__(self, outlier_method: str = "iqr", outlier_threshold: float = 1.5):
        """
        Initialize analyzer
        
        Args:
            outlier_method: Method for outlier detection ('iqr', 'zscore', 'isolation')
            outlier_threshold: Threshold for outlier detection
        """
        self.outlier_method = outlier_method
        self.outlier_threshold = outlier_threshold
        
    def analyze(self, df: pd.DataFrame, dataset_name: str = "dataset") -> DataQualityReport:
        """
        Perform comprehensive data quality analysis
        
        Args:
            df: DataFrame to analyze
            dataset_name: Name for the dataset
            
        Returns:
            DataQualityReport with complete analysis
        """
        report = DataQualityReport(dataset_name=dataset_name)
        
        # Basic info
        report.n_rows = len(df)
        report.n_columns = len(df.columns)
        report.memory_usage_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        
        # Analyze data types
        self._analyze_data_types(df, report)
        
        # Check missing values
        self._analyze_missing_values(df, report)
        
        # Check duplicates
        self._analyze_duplicates(df, report)
        
        # Detect outliers
        self._detect_outliers(df, report)
        
        # Generate summaries
        self._generate_summaries(df, report)
        
        # Calculate quality scores
        self._calculate_quality_scores(df, report)
        
        # Generate recommendations
        self._generate_recommendations(report)
        
        return report
    
    def _analyze_data_types(self, df: pd.DataFrame, report: DataQualityReport):
        """Analyze and categorize column data types"""
        for col in df.columns:
            dtype = str(df[col].dtype)
            report.column_types[col] = dtype
            
            if pd.api.types.is_numeric_dtype(df[col]):
                report.numeric_columns.append(col)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                report.datetime_columns.append(col)
            else:
                # Check if it could be datetime
                if self._could_be_datetime(df[col]):
                    report.warnings.append(f"Column '{col}' might be a datetime")
                report.categorical_columns.append(col)
                
                # Check cardinality
                n_unique = df[col].nunique()
                if n_unique == len(df):
                    report.warnings.append(f"Column '{col}' has all unique values (possible ID)")
                elif n_unique == 1:
                    report.issues.append(f"Column '{col}' has only one unique value")
    
    def _could_be_datetime(self, series: pd.Series, sample_size: int = 100) -> bool:
        """Check if a series could be converted to datetime"""
        try:
            sample = series.dropna().head(sample_size)
            if len(sample) > 0:
                pd.to_datetime(sample, errors='coerce')
                # If more than 80% convert successfully, likely datetime
                return pd.to_datetime(sample, errors='coerce').notna().mean() > 0.8
        except:
            pass
        return False
    
    def _analyze_missing_values(self, df: pd.DataFrame, report: DataQualityReport):
        """Analyze missing values in the dataset"""
        missing_counts = df.isnull().sum()
        missing_percentages = (missing_counts / len(df)) * 100
        
        for col in df.columns:
            if missing_counts[col] > 0:
                report.missing_counts[col] = int(missing_counts[col])
                report.missing_percentages[col] = float(missing_percentages[col])
                report.columns_with_missing.append(col)
                
                if missing_percentages[col] > 50:
                    report.issues.append(f"Column '{col}' has {missing_percentages[col]:.1f}% missing values")
                elif missing_percentages[col] > 20:
                    report.warnings.append(f"Column '{col}' has {missing_percentages[col]:.1f}% missing values")
    
    def _analyze_duplicates(self, df: pd.DataFrame, report: DataQualityReport):
        """Analyze duplicate rows"""
        n_duplicates = df.duplicated().sum()
        report.n_duplicates = int(n_duplicates)
        report.duplicate_percentage = (n_duplicates / len(df)) * 100
        
        if report.duplicate_percentage > 10:
            report.issues.append(f"Dataset has {report.duplicate_percentage:.1f}% duplicate rows")
        elif report.duplicate_percentage > 5:
            report.warnings.append(f"Dataset has {report.duplicate_percentage:.1f}% duplicate rows")
    
    def _detect_outliers(self, df: pd.DataFrame, report: DataQualityReport):
        """Detect outliers in numeric columns"""
        for col in report.numeric_columns:
            if col not in df.columns:
                continue
                
            series = df[col].dropna()
            if len(series) == 0:
                continue
                
            outliers = []
            
            if self.outlier_method == "iqr":
                Q1 = series.quantile(0.25)
                Q3 = series.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - self.outlier_threshold * IQR
                upper_bound = Q3 + self.outlier_threshold * IQR
                outliers = series[(series < lower_bound) | (series > upper_bound)]
                
            elif self.outlier_method == "zscore":
                z_scores = np.abs(stats.zscore(series))
                outliers = series[z_scores > self.outlier_threshold]
            
            if len(outliers) > 0:
                report.outlier_counts[col] = len(outliers)
                report.outlier_methods[col] = self.outlier_method
                
                outlier_pct = (len(outliers) / len(series)) * 100
                if outlier_pct > 10:
                    report.warnings.append(f"Column '{col}' has {outlier_pct:.1f}% outliers")
    
    def _generate_summaries(self, df: pd.DataFrame, report: DataQualityReport):
        """Generate statistical summaries"""
        # Numeric summaries
        for col in report.numeric_columns:
            if col in df.columns:
                series = df[col].dropna()
                if len(series) > 0:
                    report.numeric_summary[col] = {
                        "mean": float(series.mean()),
                        "median": float(series.median()),
                        "std": float(series.std()),
                        "min": float(series.min()),
                        "max": float(series.max()),
                        "q25": float(series.quantile(0.25)),
                        "q75": float(series.quantile(0.75)),
                        "skewness": float(series.skew()),
                        "kurtosis": float(series.kurtosis())
                    }
        
        # Categorical summaries
        for col in report.categorical_columns:
            if col in df.columns:
                value_counts = df[col].value_counts()
                report.categorical_summary[col] = {
                    "n_unique": int(df[col].nunique()),
                    "top_value": str(value_counts.iloc[0]) if len(value_counts) > 0 else None,
                    "top_frequency": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                    "top_5_values": value_counts.head(5).to_dict()
                }
    
    def _calculate_quality_scores(self, df: pd.DataFrame, report: DataQualityReport):
        """Calculate data quality scores"""
        # Completeness: Based on missing values
        total_cells = report.n_rows * report.n_columns
        missing_cells = sum(report.missing_counts.values())
        report.completeness_score = max(0, (1 - missing_cells / total_cells) * 100)
        
        # Consistency: Based on duplicates and data type issues
        consistency_penalties = report.duplicate_percentage
        if report.issues:
            consistency_penalties += len(report.issues) * 5
        report.consistency_score = max(0, 100 - consistency_penalties)
        
        # Validity: Based on outliers and warnings
        validity_penalties = 0
        if report.outlier_counts:
            avg_outlier_pct = np.mean([
                (count / report.n_rows) * 100 
                for count in report.outlier_counts.values()
            ])
            validity_penalties += avg_outlier_pct
        validity_penalties += len(report.warnings) * 2
        report.validity_score = max(0, 100 - validity_penalties)
        
        # Overall score (weighted average)
        report.overall_quality_score = (
            report.completeness_score * 0.4 +
            report.consistency_score * 0.3 +
            report.validity_score * 0.3
        )
    
    def _generate_recommendations(self, report: DataQualityReport):
        """Generate actionable recommendations"""
        # Missing value recommendations
        if report.columns_with_missing:
            high_missing = [col for col, pct in report.missing_percentages.items() if pct > 50]
            if high_missing:
                report.recommendations.append(
                    f"Consider dropping columns with >50% missing: {', '.join(high_missing)}"
                )
            
            moderate_missing = [col for col, pct in report.missing_percentages.items() if 5 < pct <= 50]
            if moderate_missing:
                report.recommendations.append(
                    f"Impute missing values for: {', '.join(moderate_missing)}"
                )
        
        # Duplicate recommendations
        if report.n_duplicates > 0:
            report.recommendations.append(
                f"Remove {report.n_duplicates} duplicate rows"
            )
        
        # Outlier recommendations
        if report.outlier_counts:
            report.recommendations.append(
                f"Review and handle outliers in: {', '.join(report.outlier_counts.keys())}"
            )
        
        # Data type recommendations
        for warning in report.warnings:
            if "might be a datetime" in warning:
                col = warning.split("'")[1]
                report.recommendations.append(f"Convert '{col}' to datetime type")
        
        # Scale recommendations
        high_variance_cols = []
        for col, stats in report.numeric_summary.items():
            if stats['std'] > stats['mean'] * 2:  # High coefficient of variation
                high_variance_cols.append(col)
        if high_variance_cols:
            report.recommendations.append(
                f"Consider scaling/normalizing: {', '.join(high_variance_cols)}"
            )


class DataPreprocessor:
    """Automated data preprocessing pipeline"""
    
    def __init__(self):
        """Initialize preprocessor"""
        self.transformations = []
        self.fit_params = {}
    
    def auto_clean(self, 
                   df: pd.DataFrame,
                   handle_missing: str = "smart",
                   handle_outliers: str = "clip",
                   handle_duplicates: bool = True,
                   scale_numeric: str = "standard") -> pd.DataFrame:
        """
        Automatically clean and preprocess data
        
        Args:
            df: DataFrame to clean
            handle_missing: Strategy for missing values ('drop', 'mean', 'median', 'mode', 'smart')
            handle_outliers: Strategy for outliers ('keep', 'clip', 'remove')
            handle_duplicates: Whether to remove duplicates
            scale_numeric: Scaling strategy ('none', 'standard', 'minmax', 'robust')
            
        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()
        
        # Remove duplicates
        if handle_duplicates:
            n_before = len(df_clean)
            df_clean = df_clean.drop_duplicates()
            n_after = len(df_clean)
            if n_before > n_after:
                logger.info(f"Removed {n_before - n_after} duplicate rows")
        
        # Handle missing values
        df_clean = self._handle_missing_values(df_clean, strategy=handle_missing)
        
        # Handle outliers
        df_clean = self._handle_outliers(df_clean, strategy=handle_outliers)
        
        # Scale numeric features
        if scale_numeric != "none":
            df_clean = self._scale_numeric_features(df_clean, method=scale_numeric)
        
        return df_clean
    
    def _handle_missing_values(self, df: pd.DataFrame, strategy: str = "smart") -> pd.DataFrame:
        """Handle missing values based on strategy"""
        df_clean = df.copy()
        
        if strategy == "drop":
            return df_clean.dropna()
        
        for col in df_clean.columns:
            if df_clean[col].isnull().any():
                if strategy == "smart":
                    # Smart imputation based on data type and distribution
                    if pd.api.types.is_numeric_dtype(df_clean[col]):
                        # Use median for skewed, mean for normal
                        skewness = df_clean[col].skew()
                        if abs(skewness) > 1:
                            fill_value = df_clean[col].median()
                        else:
                            fill_value = df_clean[col].mean()
                    else:
                        # Use mode for categorical
                        fill_value = df_clean[col].mode()[0] if not df_clean[col].mode().empty else "missing"
                
                elif strategy == "mean" and pd.api.types.is_numeric_dtype(df_clean[col]):
                    fill_value = df_clean[col].mean()
                elif strategy == "median" and pd.api.types.is_numeric_dtype(df_clean[col]):
                    fill_value = df_clean[col].median()
                elif strategy == "mode":
                    fill_value = df_clean[col].mode()[0] if not df_clean[col].mode().empty else "missing"
                else:
                    continue
                
                df_clean[col].fillna(fill_value, inplace=True)
                self.fit_params[f"{col}_fill_value"] = fill_value
        
        return df_clean
    
    def _handle_outliers(self, df: pd.DataFrame, strategy: str = "clip") -> pd.DataFrame:
        """Handle outliers based on strategy"""
        if strategy == "keep":
            return df
        
        df_clean = df.copy()
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            Q1 = df_clean[col].quantile(0.25)
            Q3 = df_clean[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            if strategy == "clip":
                df_clean[col] = df_clean[col].clip(lower_bound, upper_bound)
            elif strategy == "remove":
                df_clean = df_clean[(df_clean[col] >= lower_bound) & (df_clean[col] <= upper_bound)]
            
            self.fit_params[f"{col}_bounds"] = (lower_bound, upper_bound)
        
        return df_clean
    
    def _scale_numeric_features(self, df: pd.DataFrame, method: str = "standard") -> pd.DataFrame:
        """Scale numeric features"""
        from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
        
        df_clean = df.copy()
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        
        if len(numeric_cols) == 0:
            return df_clean
        
        if method == "standard":
            scaler = StandardScaler()
        elif method == "minmax":
            scaler = MinMaxScaler()
        elif method == "robust":
            scaler = RobustScaler()
        else:
            return df_clean
        
        df_clean[numeric_cols] = scaler.fit_transform(df_clean[numeric_cols])
        self.fit_params[f"scaler_{method}"] = scaler
        
        return df_clean
    
    def save_pipeline(self, path: Path):
        """Save preprocessing pipeline parameters"""
        import joblib
        
        # Separate serializable params from sklearn objects
        simple_params = {}
        complex_params = {}
        
        for key, value in self.fit_params.items():
            if isinstance(value, (int, float, str, list, tuple)):
                simple_params[key] = value
            else:
                complex_params[key] = value
        
        # Save simple params as JSON
        with open(path / "preprocessing_params.json", "w") as f:
            json.dump(simple_params, f, indent=2)
        
        # Save complex params as pickle
        if complex_params:
            joblib.dump(complex_params, path / "preprocessing_objects.pkl")
        
        logger.info(f"Saved preprocessing pipeline to {path}")


def generate_quality_report(data_path: str, output_path: Optional[str] = None) -> DataQualityReport:
    """
    Generate a data quality report for a dataset
    
    Args:
        data_path: Path to the data file
        output_path: Optional path to save the report
        
    Returns:
        DataQualityReport object
    """
    # Load data
    df = pd.read_csv(data_path)
    dataset_name = Path(data_path).stem
    
    # Analyze quality
    analyzer = DataQualityAnalyzer()
    report = analyzer.analyze(df, dataset_name=dataset_name)
    
    # Save report if path provided
    if output_path:
        with open(output_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"Saved quality report to {output_path}")
    
    return report


def auto_preprocess(data_path: str, output_path: Optional[str] = None) -> pd.DataFrame:
    """
    Automatically preprocess a dataset with smart defaults
    
    Args:
        data_path: Path to the data file
        output_path: Optional path to save cleaned data
        
    Returns:
        Preprocessed DataFrame
    """
    # Load data
    df = pd.read_csv(data_path)
    
    # Analyze quality first
    analyzer = DataQualityAnalyzer()
    report = analyzer.analyze(df, dataset_name=Path(data_path).stem)
    
    # Preprocess based on analysis
    preprocessor = DataPreprocessor()
    
    # Determine strategies based on quality report
    missing_strategy = "smart"
    outlier_strategy = "clip" if report.outlier_counts else "keep"
    scale_strategy = "robust" if report.outlier_counts else "standard"
    
    df_clean = preprocessor.auto_clean(
        df,
        handle_missing=missing_strategy,
        handle_outliers=outlier_strategy,
        handle_duplicates=True,
        scale_numeric=scale_strategy
    )
    
    # Save if path provided
    if output_path:
        df_clean.to_csv(output_path, index=False)
        logger.info(f"Saved cleaned data to {output_path}")
    
    return df_clean