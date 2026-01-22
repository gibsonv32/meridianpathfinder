"""Automated preprocessing pipeline for MERIDIAN"""

from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass
import numpy as np
import pandas as pd
from pathlib import Path
import json
import pickle
from datetime import datetime

from meridian.data.profiler import DataProfiler
from meridian.data.missing_handler import MissingValueHandler, MissingStrategy
from meridian.data.outlier_handler import OutlierHandler, OutlierMethod, OutlierTreatment
from meridian.data.feature_engineer import FeatureEngineer, AutoFeatureEngineer
from meridian.data.transformer import DataTransformer, TimeSeriesTransformer

from meridian.logging_config import get_logger
from meridian.utils.exceptions import DataError, ErrorContext
from meridian.utils.file_ops import atomic_write

logger = get_logger("meridian.data.preprocessor")


class PreprocessingStrategy(Enum):
    """Preprocessing strategies"""
    MINIMAL = "minimal"  # Just handle missing values
    STANDARD = "standard"  # Missing + outliers + basic features
    ADVANCED = "advanced"  # Full feature engineering
    CUSTOM = "custom"  # User-defined pipeline
    AUTO = "auto"  # Automatically determine based on data


@dataclass
class PreprocessingConfig:
    """Configuration for preprocessing pipeline"""
    strategy: PreprocessingStrategy = PreprocessingStrategy.AUTO
    
    # Missing value handling
    missing_strategy: MissingStrategy = MissingStrategy.SMART
    missing_threshold: float = 0.5
    add_missing_indicators: bool = False
    
    # Outlier handling
    outlier_method: OutlierMethod = OutlierMethod.IQR
    outlier_treatment: OutlierTreatment = OutlierTreatment.CAP
    outlier_threshold: float = 1.5
    
    # Feature engineering
    auto_engineer: bool = True
    create_polynomial: bool = False
    create_interactions: bool = False
    target_feature_count: Optional[int] = None
    
    # Scaling
    scale_features: bool = True
    scaling_strategy: str = "standard"
    
    # Validation
    validate_output: bool = True
    min_variance: float = 1e-10
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "strategy": self.strategy.value,
            "missing_strategy": self.missing_strategy.value,
            "missing_threshold": self.missing_threshold,
            "add_missing_indicators": self.add_missing_indicators,
            "outlier_method": self.outlier_method.value,
            "outlier_treatment": self.outlier_treatment.value,
            "outlier_threshold": self.outlier_threshold,
            "auto_engineer": self.auto_engineer,
            "create_polynomial": self.create_polynomial,
            "create_interactions": self.create_interactions,
            "target_feature_count": self.target_feature_count,
            "scale_features": self.scale_features,
            "scaling_strategy": self.scaling_strategy,
            "validate_output": self.validate_output,
            "min_variance": self.min_variance
        }
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "PreprocessingConfig":
        """Create from dictionary"""
        return cls(
            strategy=PreprocessingStrategy(config.get("strategy", "auto")),
            missing_strategy=MissingStrategy(config.get("missing_strategy", "smart")),
            missing_threshold=config.get("missing_threshold", 0.5),
            add_missing_indicators=config.get("add_missing_indicators", False),
            outlier_method=OutlierMethod(config.get("outlier_method", "iqr")),
            outlier_treatment=OutlierTreatment(config.get("outlier_treatment", "cap")),
            outlier_threshold=config.get("outlier_threshold", 1.5),
            auto_engineer=config.get("auto_engineer", True),
            create_polynomial=config.get("create_polynomial", False),
            create_interactions=config.get("create_interactions", False),
            target_feature_count=config.get("target_feature_count"),
            scale_features=config.get("scale_features", True),
            scaling_strategy=config.get("scaling_strategy", "standard"),
            validate_output=config.get("validate_output", True),
            min_variance=config.get("min_variance", 1e-10)
        )


@dataclass
class PreprocessingResult:
    """Result of preprocessing pipeline"""
    original_shape: Tuple[int, int]
    final_shape: Tuple[int, int]
    n_missing_imputed: int
    n_outliers_treated: int
    n_features_engineered: int
    n_features_dropped: int
    processing_time: float
    steps_performed: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "original_shape": self.original_shape,
            "final_shape": self.final_shape,
            "n_missing_imputed": self.n_missing_imputed,
            "n_outliers_treated": self.n_outliers_treated,
            "n_features_engineered": self.n_features_engineered,
            "n_features_dropped": self.n_features_dropped,
            "processing_time": self.processing_time,
            "steps_performed": self.steps_performed,
            "warnings": self.warnings
        }


class AutoPreprocessor:
    """Automated preprocessing pipeline"""
    
    def __init__(self, config: Optional[PreprocessingConfig] = None):
        """
        Initialize preprocessor.
        
        Args:
            config: Preprocessing configuration
        """
        self.config = config or PreprocessingConfig()
        
        # Initialize components
        self.profiler = DataProfiler()
        self.missing_handler = None
        self.outlier_handler = None
        self.feature_engineer = None
        self.transformer = None
        
        # State
        self.is_fitted = False
        self.feature_names = []
        self.preprocessing_result = None
    
    def fit_transform(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None
    ) -> Tuple[pd.DataFrame, PreprocessingResult]:
        """
        Fit and transform data through preprocessing pipeline.
        
        Args:
            X: Input features
            y: Target variable (optional, for supervised preprocessing)
            
        Returns:
            Preprocessed features and result summary
        """
        logger.info(f"Starting preprocessing pipeline with strategy: {self.config.strategy.value}")
        
        with ErrorContext("preprocessing_pipeline"):
            start_time = datetime.now()
            original_shape = X.shape
            steps_performed = []
            warnings = []
            
            # Determine strategy if auto
            if self.config.strategy == PreprocessingStrategy.AUTO:
                self._determine_strategy(X, y)
            
            # Step 1: Data Profiling
            logger.info("Step 1: Profiling data")
            profile = self.profiler.profile(X)
            
            # Check for issues
            if profile.missing_ratio > 0.8:
                warnings.append(f"High missing ratio: {profile.missing_ratio:.1%}")
            
            # Step 2: Handle Missing Values
            if profile.n_missing > 0:
                logger.info("Step 2: Handling missing values")
                self.missing_handler = MissingValueHandler(
                    strategy=self.config.missing_strategy,
                    threshold=self.config.missing_threshold,
                    add_indicator=self.config.add_missing_indicators
                )
                X = self.missing_handler.fit_transform(X)
                steps_performed.append("missing_value_imputation")
            
            n_missing_imputed = profile.n_missing
            
            # Step 3: Handle Outliers
            if self.config.strategy in [PreprocessingStrategy.STANDARD, PreprocessingStrategy.ADVANCED]:
                logger.info("Step 3: Handling outliers")
                self.outlier_handler = OutlierHandler(
                    method=self.config.outlier_method,
                    treatment=self.config.outlier_treatment,
                    threshold=self.config.outlier_threshold
                )
                outliers = self.outlier_handler.fit_detect(X)
                X = self.outlier_handler.treat(X, outliers)
                n_outliers_treated = outliers.sum().sum()
                steps_performed.append("outlier_treatment")
            else:
                n_outliers_treated = 0
            
            # Step 4: Feature Engineering
            n_features_before = X.shape[1]
            
            if self.config.strategy == PreprocessingStrategy.ADVANCED:
                logger.info("Step 4: Engineering features")
                
                if self.config.auto_engineer:
                    # Use automatic feature engineering
                    auto_engineer = AutoFeatureEngineer()
                    X = auto_engineer.fit_transform(
                        X, y,
                        target_feature_count=self.config.target_feature_count
                    )
                    self.feature_engineer = auto_engineer.engineer
                else:
                    # Manual feature engineering
                    self.feature_engineer = FeatureEngineer()
                    X = self.feature_engineer.fit_transform(X, y, auto_engineer=False)
                    
                    if self.config.create_polynomial:
                        numeric_cols = X.select_dtypes(include=[np.number]).columns[:5]
                        if len(numeric_cols) > 0:
                            X = self.feature_engineer.create_polynomial_features(
                                X, numeric_cols.tolist(), degree=2
                            )
                
                steps_performed.append("feature_engineering")
            
            n_features_engineered = X.shape[1] - n_features_before
            
            # Step 5: Data Transformation
            if self.config.strategy != PreprocessingStrategy.MINIMAL:
                logger.info("Step 5: Transforming features")
                self.transformer = DataTransformer()
                X = self.transformer.auto_transform(X)
                steps_performed.append("transformation")
            
            # Step 6: Feature Scaling
            if self.config.scale_features:
                logger.info("Step 6: Scaling features")
                if self.feature_engineer:
                    X = self.feature_engineer.scale_features(
                        X, strategy=self.config.scaling_strategy
                    )
                else:
                    from sklearn.preprocessing import StandardScaler
                    scaler = StandardScaler()
                    numeric_cols = X.select_dtypes(include=[np.number]).columns
                    X[numeric_cols] = scaler.fit_transform(X[numeric_cols])
                
                steps_performed.append("scaling")
            
            # Step 7: Validation and Cleanup
            if self.config.validate_output:
                logger.info("Step 7: Validating output")
                X, n_dropped = self._validate_and_clean(X)
            else:
                n_dropped = 0
            
            # Store feature names
            self.feature_names = X.columns.tolist()
            self.is_fitted = True
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Create result
            self.preprocessing_result = PreprocessingResult(
                original_shape=original_shape,
                final_shape=X.shape,
                n_missing_imputed=n_missing_imputed,
                n_outliers_treated=n_outliers_treated,
                n_features_engineered=n_features_engineered,
                n_features_dropped=n_dropped,
                processing_time=processing_time,
                steps_performed=steps_performed,
                warnings=warnings
            )
            
            logger.info(
                f"Preprocessing complete. Shape: {original_shape} -> {X.shape}. "
                f"Time: {processing_time:.2f}s"
            )
            
            return X, self.preprocessing_result
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Transform new data using fitted preprocessor.
        
        Args:
            X: New data to transform
            
        Returns:
            Transformed data
        """
        if not self.is_fitted:
            raise DataError("Preprocessor must be fitted before transform")
        
        logger.info(f"Transforming new data with shape {X.shape}")
        
        # Apply fitted transformations
        if self.missing_handler:
            X = self.missing_handler.transform(X)
        
        if self.outlier_handler:
            outliers = self.outlier_handler.fit_detect(X)
            X = self.outlier_handler.treat(X, outliers)
        
        if self.feature_engineer:
            X = self.feature_engineer.transform(X)
        
        if self.transformer:
            # Note: auto_transform will refit, might want to store fitted transforms
            X = self.transformer.auto_transform(X)
        
        # Ensure same columns as training
        for col in self.feature_names:
            if col not in X.columns:
                X[col] = 0  # Fill missing columns with 0
        
        X = X[self.feature_names]  # Reorder and select columns
        
        return X
    
    def _determine_strategy(self, X: pd.DataFrame, y: Optional[pd.Series]) -> None:
        """Automatically determine preprocessing strategy"""
        n_samples, n_features = X.shape
        
        # Simple heuristics for strategy selection
        if n_samples < 100 or n_features < 5:
            self.config.strategy = PreprocessingStrategy.MINIMAL
            logger.info("Selected MINIMAL strategy due to small dataset")
        
        elif n_samples < 1000 or n_features < 20:
            self.config.strategy = PreprocessingStrategy.STANDARD
            logger.info("Selected STANDARD strategy for medium dataset")
        
        else:
            self.config.strategy = PreprocessingStrategy.ADVANCED
            logger.info("Selected ADVANCED strategy for large dataset")
    
    def _validate_and_clean(self, X: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """Validate and clean processed data"""
        n_dropped = 0
        
        # Remove constant features
        constant_cols = []
        for col in X.columns:
            if X[col].nunique() <= 1:
                constant_cols.append(col)
        
        if constant_cols:
            logger.warning(f"Dropping {len(constant_cols)} constant features")
            X = X.drop(columns=constant_cols)
            n_dropped += len(constant_cols)
        
        # Remove low variance features
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        low_var_cols = []
        
        for col in numeric_cols:
            if X[col].var() < self.config.min_variance:
                low_var_cols.append(col)
        
        if low_var_cols:
            logger.warning(f"Dropping {len(low_var_cols)} low variance features")
            X = X.drop(columns=low_var_cols)
            n_dropped += len(low_var_cols)
        
        # Check for infinite values
        inf_cols = []
        for col in X.select_dtypes(include=[np.number]).columns:
            if np.isinf(X[col]).any():
                inf_cols.append(col)
                X[col] = X[col].replace([np.inf, -np.inf], np.nan).fillna(X[col].median())
        
        if inf_cols:
            logger.warning(f"Replaced infinite values in {len(inf_cols)} columns")
        
        return X, n_dropped
    
    def save(self, filepath: Union[str, Path]) -> None:
        """
        Save preprocessor to file.
        
        Args:
            filepath: Path to save file
        """
        filepath = Path(filepath)
        
        # Prepare state
        state = {
            "config": self.config.to_dict(),
            "feature_names": self.feature_names,
            "is_fitted": self.is_fitted,
            "preprocessing_result": self.preprocessing_result.to_dict() if self.preprocessing_result else None,
            "components": {
                "missing_handler": self.missing_handler,
                "outlier_handler": self.outlier_handler,
                "feature_engineer": self.feature_engineer,
                "transformer": self.transformer
            }
        }
        
        # Save with atomic write
        with atomic_write(filepath, mode='wb') as f:
            pickle.dump(state, f)
        
        logger.info(f"Saved preprocessor to {filepath}")
    
    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "AutoPreprocessor":
        """
        Load preprocessor from file.
        
        Args:
            filepath: Path to saved file
            
        Returns:
            Loaded preprocessor
        """
        filepath = Path(filepath)
        
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        
        # Create preprocessor
        preprocessor = cls(PreprocessingConfig.from_dict(state["config"]))
        
        # Restore state
        preprocessor.feature_names = state["feature_names"]
        preprocessor.is_fitted = state["is_fitted"]
        
        if state["preprocessing_result"]:
            preprocessor.preprocessing_result = PreprocessingResult(**state["preprocessing_result"])
        
        # Restore components
        components = state["components"]
        preprocessor.missing_handler = components["missing_handler"]
        preprocessor.outlier_handler = components["outlier_handler"]
        preprocessor.feature_engineer = components["feature_engineer"]
        preprocessor.transformer = components["transformer"]
        
        logger.info(f"Loaded preprocessor from {filepath}")
        
        return preprocessor
    
    def get_summary(self) -> Dict[str, Any]:
        """Get preprocessing summary"""
        summary = {
            "config": self.config.to_dict(),
            "is_fitted": self.is_fitted,
            "feature_names": self.feature_names[:10] if self.feature_names else [],
            "n_features": len(self.feature_names)
        }
        
        if self.preprocessing_result:
            summary["result"] = self.preprocessing_result.to_dict()
        
        return summary


class DataQualityPipeline:
    """Complete data quality and preprocessing pipeline"""
    
    def __init__(self):
        """Initialize data quality pipeline"""
        self.preprocessor = None
        self.profiler = DataProfiler()
        self.profile_before = None
        self.profile_after = None
    
    def process(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
        config: Optional[PreprocessingConfig] = None
    ) -> Tuple[pd.DataFrame, pd.Series, Dict[str, Any]]:
        """
        Process data through complete pipeline.
        
        Args:
            df: Input DataFrame
            target_col: Name of target column
            config: Preprocessing configuration
            
        Returns:
            X (features), y (target), and quality report
        """
        logger.info("Starting data quality pipeline")
        
        # Separate target
        if target_col and target_col in df.columns:
            y = df[target_col]
            X = df.drop(columns=[target_col])
        else:
            y = None
            X = df
        
        # Profile before
        self.profile_before = self.profiler.profile(X)
        
        # Preprocess
        self.preprocessor = AutoPreprocessor(config)
        X_processed, result = self.preprocessor.fit_transform(X, y)
        
        # Profile after
        self.profile_after = self.profiler.profile(X_processed)
        
        # Generate quality report
        quality_report = self._generate_quality_report()
        
        logger.info("Data quality pipeline complete")
        
        return X_processed, y, quality_report
    
    def _generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        report = {
            "preprocessing": self.preprocessor.preprocessing_result.to_dict(),
            "quality_improvement": {
                "missing_ratio": {
                    "before": self.profile_before.missing_ratio,
                    "after": self.profile_after.missing_ratio,
                    "improvement": self.profile_before.missing_ratio - self.profile_after.missing_ratio
                },
                "duplicate_ratio": {
                    "before": self.profile_before.duplicate_ratio,
                    "after": self.profile_after.duplicate_ratio,
                    "improvement": self.profile_before.duplicate_ratio - self.profile_after.duplicate_ratio
                }
            },
            "feature_changes": {
                "n_features_before": self.profile_before.n_columns,
                "n_features_after": self.profile_after.n_columns,
                "n_features_added": self.profile_after.n_columns - self.profile_before.n_columns
            },
            "warnings": self.preprocessor.preprocessing_result.warnings
        }
        
        return report