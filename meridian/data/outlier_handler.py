"""Outlier detection and treatment for MERIDIAN"""

from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.covariance import EllipticEnvelope
from sklearn.neighbors import LocalOutlierFactor
from sklearn.cluster import DBSCAN

from meridian.logging_config import get_logger
from meridian.utils.exceptions import DataError, ErrorContext

logger = get_logger("meridian.data.outlier_handler")


class OutlierMethod(Enum):
    """Outlier detection methods"""
    IQR = "iqr"
    ZSCORE = "zscore"
    ISOLATION_FOREST = "isolation_forest"
    ELLIPTIC_ENVELOPE = "elliptic_envelope"
    LOF = "lof"  # Local Outlier Factor
    DBSCAN = "dbscan"
    PERCENTILE = "percentile"
    MAD = "mad"  # Median Absolute Deviation


class OutlierTreatment(Enum):
    """Outlier treatment strategies"""
    REMOVE = "remove"
    CAP = "cap"  # Winsorization
    TRANSFORM = "transform"  # Log or other transformation
    IMPUTE = "impute"  # Replace with median/mean
    KEEP = "keep"  # Keep as is
    FLAG = "flag"  # Add indicator column


class OutlierHandler:
    """Handle outliers with various detection and treatment methods"""
    
    def __init__(
        self,
        method: Union[str, OutlierMethod] = OutlierMethod.IQR,
        treatment: Union[str, OutlierTreatment] = OutlierTreatment.CAP,
        threshold: float = 1.5,
        contamination: float = 0.1
    ):
        """
        Initialize outlier handler.
        
        Args:
            method: Detection method
            treatment: Treatment strategy
            threshold: Threshold for detection (IQR multiplier or z-score)
            contamination: Expected proportion of outliers
        """
        if isinstance(method, str):
            method = OutlierMethod(method)
        if isinstance(treatment, str):
            treatment = OutlierTreatment(treatment)
        
        self.method = method
        self.treatment = treatment
        self.threshold = threshold
        self.contamination = contamination
        self.outlier_bounds = {}
        self.outlier_models = {}
    
    def fit_detect(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fit and detect outliers in DataFrame.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with outlier indicators (True = outlier)
        """
        logger.info(f"Detecting outliers with method: {self.method.value}")
        
        with ErrorContext("outlier_detection", method=self.method.value):
            # Get numeric columns only
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if not numeric_cols:
                logger.warning("No numeric columns found for outlier detection")
                return pd.DataFrame(False, index=df.index, columns=df.columns)
            
            outliers = pd.DataFrame(False, index=df.index, columns=df.columns)
            
            if self.method in [OutlierMethod.IQR, OutlierMethod.ZSCORE, OutlierMethod.PERCENTILE, OutlierMethod.MAD]:
                # Univariate methods - apply per column
                for col in numeric_cols:
                    outliers[col] = self._detect_univariate(df[col])
            else:
                # Multivariate methods - apply to all numeric columns
                outliers[numeric_cols] = self._detect_multivariate(df[numeric_cols])
            
            # Log detection results
            n_outliers = outliers.sum().sum()
            pct_outliers = n_outliers / (len(df) * len(numeric_cols)) * 100
            logger.info(f"Detected {n_outliers} outliers ({pct_outliers:.1f}% of numeric values)")
            
            return outliers
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fit, detect, and treat outliers.
        
        Args:
            df: Input DataFrame
            
        Returns:
            DataFrame with treated outliers
        """
        # Detect outliers
        outliers = self.fit_detect(df)
        
        # Treat outliers
        return self.treat(df, outliers)
    
    def treat(self, df: pd.DataFrame, outliers: pd.DataFrame) -> pd.DataFrame:
        """
        Treat detected outliers.
        
        Args:
            df: Original DataFrame
            outliers: Boolean DataFrame indicating outliers
            
        Returns:
            DataFrame with treated outliers
        """
        logger.info(f"Treating outliers with strategy: {self.treatment.value}")
        
        with ErrorContext("outlier_treatment", treatment=self.treatment.value):
            df_treated = df.copy()
            
            if self.treatment == OutlierTreatment.REMOVE:
                # Remove rows with any outliers
                rows_with_outliers = outliers.any(axis=1)
                df_treated = df_treated[~rows_with_outliers]
                logger.info(f"Removed {rows_with_outliers.sum()} rows with outliers")
            
            elif self.treatment == OutlierTreatment.CAP:
                # Cap outliers at bounds
                for col in df.select_dtypes(include=[np.number]).columns:
                    if col in self.outlier_bounds:
                        lower, upper = self.outlier_bounds[col]
                        df_treated[col] = df_treated[col].clip(lower=lower, upper=upper)
            
            elif self.treatment == OutlierTreatment.TRANSFORM:
                # Apply transformation to reduce outlier impact
                for col in df.select_dtypes(include=[np.number]).columns:
                    if outliers[col].any():
                        df_treated[col] = self._transform_column(df_treated[col])
            
            elif self.treatment == OutlierTreatment.IMPUTE:
                # Replace outliers with median
                for col in df.select_dtypes(include=[np.number]).columns:
                    if outliers[col].any():
                        median = df[col][~outliers[col]].median()
                        df_treated.loc[outliers[col], col] = median
            
            elif self.treatment == OutlierTreatment.FLAG:
                # Add indicator columns
                for col in df.columns:
                    if outliers[col].any():
                        df_treated[f"{col}_outlier"] = outliers[col].astype(int)
            
            # Keep as is for OutlierTreatment.KEEP
            
            return df_treated
    
    def _detect_univariate(self, series: pd.Series) -> pd.Series:
        """Detect outliers in a single column"""
        # Remove NaN values for detection
        series_clean = series.dropna()
        outliers = pd.Series(False, index=series.index)
        
        if len(series_clean) < 3:
            return outliers
        
        if self.method == OutlierMethod.IQR:
            Q1 = series_clean.quantile(0.25)
            Q3 = series_clean.quantile(0.75)
            IQR = Q3 - Q1
            
            lower = Q1 - self.threshold * IQR
            upper = Q3 + self.threshold * IQR
            
            self.outlier_bounds[series.name] = (lower, upper)
            outliers = (series < lower) | (series > upper)
        
        elif self.method == OutlierMethod.ZSCORE:
            z_scores = np.abs(stats.zscore(series_clean))
            outlier_indices = series_clean[z_scores > self.threshold].index
            outliers[outlier_indices] = True
            
            # Store bounds for capping
            mean = series_clean.mean()
            std = series_clean.std()
            self.outlier_bounds[series.name] = (
                mean - self.threshold * std,
                mean + self.threshold * std
            )
        
        elif self.method == OutlierMethod.PERCENTILE:
            lower = series_clean.quantile(self.contamination / 2)
            upper = series_clean.quantile(1 - self.contamination / 2)
            
            self.outlier_bounds[series.name] = (lower, upper)
            outliers = (series < lower) | (series > upper)
        
        elif self.method == OutlierMethod.MAD:
            median = series_clean.median()
            mad = np.median(np.abs(series_clean - median))
            
            if mad == 0:
                # Use IQR as fallback
                return self._detect_univariate_iqr(series)
            
            modified_z_scores = 0.6745 * (series_clean - median) / mad
            outlier_indices = series_clean[np.abs(modified_z_scores) > self.threshold].index
            outliers[outlier_indices] = True
            
            self.outlier_bounds[series.name] = (
                median - self.threshold * mad / 0.6745,
                median + self.threshold * mad / 0.6745
            )
        
        return outliers
    
    def _detect_univariate_iqr(self, series: pd.Series) -> pd.Series:
        """Fallback IQR detection"""
        series_clean = series.dropna()
        Q1 = series_clean.quantile(0.25)
        Q3 = series_clean.quantile(0.75)
        IQR = Q3 - Q1
        
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        
        return (series < lower) | (series > upper)
    
    def _detect_multivariate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect outliers using multivariate methods"""
        # Remove rows with NaN for multivariate detection
        df_clean = df.dropna()
        
        if len(df_clean) < 10:
            logger.warning("Not enough samples for multivariate outlier detection")
            return pd.DataFrame(False, index=df.index, columns=df.columns)
        
        outliers = pd.DataFrame(False, index=df.index, columns=df.columns)
        
        if self.method == OutlierMethod.ISOLATION_FOREST:
            model = IsolationForest(
                contamination=self.contamination,
                random_state=42
            )
            predictions = model.fit_predict(df_clean)
            outlier_mask = predictions == -1
            outliers.loc[df_clean.index, :] = outlier_mask.reshape(-1, 1)
            self.outlier_models['isolation_forest'] = model
        
        elif self.method == OutlierMethod.ELLIPTIC_ENVELOPE:
            try:
                model = EllipticEnvelope(
                    contamination=self.contamination,
                    random_state=42
                )
                predictions = model.fit_predict(df_clean)
                outlier_mask = predictions == -1
                outliers.loc[df_clean.index, :] = outlier_mask.reshape(-1, 1)
                self.outlier_models['elliptic'] = model
            except:
                logger.warning("Elliptic Envelope failed, falling back to Isolation Forest")
                return self._detect_multivariate_isolation(df)
        
        elif self.method == OutlierMethod.LOF:
            model = LocalOutlierFactor(
                contamination=self.contamination,
                novelty=False
            )
            predictions = model.fit_predict(df_clean)
            outlier_mask = predictions == -1
            outliers.loc[df_clean.index, :] = outlier_mask.reshape(-1, 1)
        
        elif self.method == OutlierMethod.DBSCAN:
            model = DBSCAN(eps=0.5, min_samples=5)
            predictions = model.fit_predict(df_clean)
            outlier_mask = predictions == -1
            outliers.loc[df_clean.index, :] = outlier_mask.reshape(-1, 1)
        
        return outliers
    
    def _detect_multivariate_isolation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fallback to Isolation Forest"""
        df_clean = df.dropna()
        outliers = pd.DataFrame(False, index=df.index, columns=df.columns)
        
        model = IsolationForest(contamination=self.contamination, random_state=42)
        predictions = model.fit_predict(df_clean)
        outlier_mask = predictions == -1
        outliers.loc[df_clean.index, :] = outlier_mask.reshape(-1, 1)
        
        return outliers
    
    def _transform_column(self, series: pd.Series) -> pd.Series:
        """Apply transformation to reduce outlier impact"""
        # Try log transformation for positive values
        if (series > 0).all():
            return np.log1p(series)
        
        # Try square root for non-negative
        elif (series >= 0).all():
            return np.sqrt(series)
        
        # Use rank transformation as fallback
        else:
            return series.rank(pct=True)
    
    def get_outlier_summary(
        self,
        df: pd.DataFrame,
        outliers: pd.DataFrame
    ) -> Dict[str, Any]:
        """Get summary of outlier detection"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        summary = {
            "method": self.method.value,
            "total_outliers": outliers.sum().sum(),
            "outlier_percentage": (outliers.sum().sum() / (len(df) * len(numeric_cols)) * 100),
            "columns": {}
        }
        
        for col in numeric_cols:
            if col in outliers.columns:
                n_outliers = outliers[col].sum()
                if n_outliers > 0:
                    summary["columns"][col] = {
                        "count": int(n_outliers),
                        "percentage": float(n_outliers / len(df) * 100),
                        "bounds": self.outlier_bounds.get(col, (None, None))
                    }
        
        return summary
    
    def visualize_outliers(
        self,
        df: pd.DataFrame,
        outliers: pd.DataFrame,
        columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate outlier visualization data"""
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        viz_data = {}
        
        for col in columns:
            if col in df.columns and col in outliers.columns:
                viz_data[col] = {
                    "values": df[col].tolist(),
                    "outliers": outliers[col].tolist(),
                    "bounds": self.outlier_bounds.get(col, (None, None)),
                    "statistics": {
                        "mean": float(df[col].mean()),
                        "median": float(df[col].median()),
                        "std": float(df[col].std()),
                        "q1": float(df[col].quantile(0.25)),
                        "q3": float(df[col].quantile(0.75))
                    }
                }
        
        return viz_data


class RobustScaler:
    """Robust scaling using median and MAD"""
    
    def __init__(self):
        self.median_ = None
        self.mad_ = None
    
    def fit(self, X: pd.DataFrame) -> "RobustScaler":
        """Fit the scaler"""
        self.median_ = X.median()
        self.mad_ = (X - self.median_).abs().median()
        # Prevent division by zero
        self.mad_[self.mad_ == 0] = 1.0
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform data"""
        if self.median_ is None:
            raise ValueError("Scaler must be fitted before transform")
        return (X - self.median_) / self.mad_
    
    def fit_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform"""
        return self.fit(X).transform(X)
    
    def inverse_transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Inverse transform"""
        if self.median_ is None:
            raise ValueError("Scaler must be fitted before inverse_transform")
        return X * self.mad_ + self.median_