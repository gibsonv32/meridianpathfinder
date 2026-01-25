"""Data transformation utilities for MERIDIAN"""

from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import (
    FunctionTransformer,
    KBinsDiscretizer,
    Binarizer
)
import json
from pathlib import Path

from meridian.logging_config import get_logger
from meridian.utils.exceptions import DataError, ErrorContext

logger = get_logger("meridian.data.transformer")


class TransformationType(Enum):
    """Transformation types"""
    LOG = "log"
    LOG1P = "log1p"
    SQRT = "sqrt"
    SQUARE = "square"
    RECIPROCAL = "reciprocal"
    EXPONENTIAL = "exponential"
    BOX_COX = "box_cox"
    YEO_JOHNSON = "yeo_johnson"
    QUANTILE = "quantile"
    RANK = "rank"
    BINNING = "binning"
    BINARIZE = "binarize"
    DIFFERENCE = "difference"
    CUMULATIVE = "cumulative"
    ROLLING = "rolling"
    LAG = "lag"
    CUSTOM = "custom"


class DataTransformer:
    """Apply various data transformations"""
    
    def __init__(self):
        """Initialize data transformer"""
        self.transformations = {}
        self.transformation_params = {}
        self.inverse_functions = {}
    
    def fit_transform(
        self,
        df: pd.DataFrame,
        transformations: Optional[Dict[str, Union[str, TransformationType]]] = None
    ) -> pd.DataFrame:
        """
        Fit and apply transformations.
        
        Args:
            df: Input DataFrame
            transformations: Dict mapping column names to transformation types
            
        Returns:
            Transformed DataFrame
        """
        logger.info(f"Applying transformations to {len(transformations or {})} columns")
        
        with ErrorContext("data_transformation"):
            df_transformed = df.copy()
            
            if transformations:
                for col, transform_type in transformations.items():
                    if col in df.columns:
                        df_transformed[col] = self.transform_column(
                            df_transformed[col],
                            transform_type
                        )
            else:
                # Auto-detect and apply transformations
                df_transformed = self.auto_transform(df_transformed)
            
            return df_transformed
    
    def transform_column(
        self,
        series: pd.Series,
        transform_type: Union[str, TransformationType],
        **kwargs
    ) -> pd.Series:
        """
        Transform a single column.
        
        Args:
            series: Column to transform
            transform_type: Type of transformation
            **kwargs: Additional parameters for transformation
            
        Returns:
            Transformed series
        """
        if isinstance(transform_type, str):
            transform_type = TransformationType(transform_type)
        
        col_name = series.name
        logger.debug(f"Applying {transform_type.value} transformation to {col_name}")
        
        # Store transformation info
        self.transformations[col_name] = transform_type
        self.transformation_params[col_name] = kwargs
        
        # Apply transformation
        if transform_type == TransformationType.LOG:
            return self._log_transform(series)
        elif transform_type == TransformationType.LOG1P:
            return self._log1p_transform(series)
        elif transform_type == TransformationType.SQRT:
            return self._sqrt_transform(series)
        elif transform_type == TransformationType.SQUARE:
            return self._square_transform(series)
        elif transform_type == TransformationType.RECIPROCAL:
            return self._reciprocal_transform(series)
        elif transform_type == TransformationType.EXPONENTIAL:
            return self._exp_transform(series)
        elif transform_type == TransformationType.BOX_COX:
            return self._boxcox_transform(series)
        elif transform_type == TransformationType.YEO_JOHNSON:
            return self._yeojohnson_transform(series)
        elif transform_type == TransformationType.QUANTILE:
            return self._quantile_transform(series)
        elif transform_type == TransformationType.RANK:
            return self._rank_transform(series)
        elif transform_type == TransformationType.BINNING:
            return self._binning_transform(series, **kwargs)
        elif transform_type == TransformationType.BINARIZE:
            return self._binarize_transform(series, **kwargs)
        elif transform_type == TransformationType.DIFFERENCE:
            return self._difference_transform(series, **kwargs)
        elif transform_type == TransformationType.CUMULATIVE:
            return self._cumulative_transform(series, **kwargs)
        elif transform_type == TransformationType.ROLLING:
            return self._rolling_transform(series, **kwargs)
        elif transform_type == TransformationType.LAG:
            return self._lag_transform(series, **kwargs)
        elif transform_type == TransformationType.CUSTOM:
            return self._custom_transform(series, **kwargs)
        else:
            return series
    
    def inverse_transform(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Inverse transform data.
        
        Args:
            df: Transformed DataFrame
            columns: Columns to inverse transform (None for all)
            
        Returns:
            Original scale DataFrame
        """
        df_inverse = df.copy()
        
        if columns is None:
            columns = list(self.transformations.keys())
        
        for col in columns:
            if col in df.columns and col in self.inverse_functions:
                inverse_func = self.inverse_functions[col]
                df_inverse[col] = inverse_func(df[col])
        
        return df_inverse
    
    def auto_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Automatically detect and apply appropriate transformations"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            # Check distribution and apply appropriate transformation
            series = df[col].dropna()
            
            if len(series) < 10:
                continue
            
            # Check skewness
            skewness = series.skew()
            
            if abs(skewness) > 1:  # Highly skewed
                # Try different transformations and pick best
                best_transform = self._find_best_transform(series)
                if best_transform:
                    df[col] = self.transform_column(df[col], best_transform)
                    logger.info(f"Applied {best_transform} to {col} (skewness: {skewness:.2f})")
        
        return df
    
    def _find_best_transform(self, series: pd.Series) -> Optional[TransformationType]:
        """Find best transformation to normalize distribution"""
        series_clean = series.dropna()
        
        if len(series_clean) < 10:
            return None
        
        best_transform = None
        best_score = abs(series_clean.skew())
        
        # Test different transformations
        transforms_to_test = []
        
        # For positive skew
        if series_clean.skew() > 0:
            if (series_clean > 0).all():
                transforms_to_test.extend([
                    TransformationType.LOG,
                    TransformationType.SQRT,
                    TransformationType.BOX_COX
                ])
            elif (series_clean >= 0).all():
                transforms_to_test.extend([
                    TransformationType.LOG1P,
                    TransformationType.SQRT,
                    TransformationType.YEO_JOHNSON
                ])
            else:
                transforms_to_test.append(TransformationType.YEO_JOHNSON)
        
        # For negative skew
        else:
            if (series_clean > 0).all():
                transforms_to_test.extend([
                    TransformationType.SQUARE,
                    TransformationType.EXPONENTIAL,
                    TransformationType.BOX_COX
                ])
            else:
                transforms_to_test.append(TransformationType.YEO_JOHNSON)
        
        for transform in transforms_to_test:
            try:
                # Apply transformation
                if transform == TransformationType.LOG:
                    transformed = np.log(series_clean)
                elif transform == TransformationType.LOG1P:
                    transformed = np.log1p(series_clean)
                elif transform == TransformationType.SQRT:
                    transformed = np.sqrt(series_clean)
                elif transform == TransformationType.SQUARE:
                    transformed = series_clean ** 2
                elif transform == TransformationType.EXPONENTIAL:
                    transformed = np.exp(series_clean)
                elif transform == TransformationType.BOX_COX:
                    transformed, _ = stats.boxcox(series_clean)
                elif transform == TransformationType.YEO_JOHNSON:
                    transformed, _ = stats.yeojohnson(series_clean)
                else:
                    continue
                
                # Check if transformation improved skewness
                new_skew = abs(pd.Series(transformed).skew())
                if new_skew < best_score:
                    best_score = new_skew
                    best_transform = transform
                    
            except:
                continue
        
        # Only return if significant improvement
        if best_transform and best_score < 0.5:
            return best_transform
        
        return None
    
    # Transformation methods
    def _log_transform(self, series: pd.Series) -> pd.Series:
        """Log transformation"""
        if (series <= 0).any():
            raise ValueError(f"Log transform requires positive values. Column: {series.name}")
        
        transformed = np.log(series)
        self.inverse_functions[series.name] = np.exp
        return transformed
    
    def _log1p_transform(self, series: pd.Series) -> pd.Series:
        """Log(1+x) transformation"""
        if (series < 0).any():
            raise ValueError(f"Log1p transform requires non-negative values. Column: {series.name}")
        
        transformed = np.log1p(series)
        self.inverse_functions[series.name] = np.expm1
        return transformed
    
    def _sqrt_transform(self, series: pd.Series) -> pd.Series:
        """Square root transformation"""
        if (series < 0).any():
            raise ValueError(f"Sqrt transform requires non-negative values. Column: {series.name}")
        
        transformed = np.sqrt(series)
        self.inverse_functions[series.name] = lambda x: x ** 2
        return transformed
    
    def _square_transform(self, series: pd.Series) -> pd.Series:
        """Square transformation"""
        transformed = series ** 2
        self.inverse_functions[series.name] = np.sqrt
        return transformed
    
    def _reciprocal_transform(self, series: pd.Series) -> pd.Series:
        """Reciprocal (1/x) transformation"""
        if (series == 0).any():
            raise ValueError(f"Reciprocal transform cannot handle zero values. Column: {series.name}")
        
        transformed = 1 / series
        self.inverse_functions[series.name] = lambda x: 1 / x
        return transformed
    
    def _exp_transform(self, series: pd.Series) -> pd.Series:
        """Exponential transformation"""
        transformed = np.exp(series)
        self.inverse_functions[series.name] = np.log
        return transformed
    
    def _boxcox_transform(self, series: pd.Series) -> pd.Series:
        """Box-Cox transformation"""
        if (series <= 0).any():
            raise ValueError(f"Box-Cox requires positive values. Column: {series.name}")
        
        transformed, lambda_param = stats.boxcox(series)
        
        # Store lambda for inverse transform
        self.transformation_params[series.name]['lambda'] = lambda_param
        
        # Define inverse function
        def inverse_boxcox(x):
            if lambda_param == 0:
                return np.exp(x)
            else:
                return (x * lambda_param + 1) ** (1 / lambda_param)
        
        self.inverse_functions[series.name] = inverse_boxcox
        
        return pd.Series(transformed, index=series.index, name=series.name)
    
    def _yeojohnson_transform(self, series: pd.Series) -> pd.Series:
        """Yeo-Johnson transformation"""
        transformed, lambda_param = stats.yeojohnson(series.dropna())
        
        # Store lambda
        self.transformation_params[series.name]['lambda'] = lambda_param
        
        # Apply to full series
        result = series.copy()
        result[series.notna()] = transformed
        
        return result
    
    def _quantile_transform(self, series: pd.Series) -> pd.Series:
        """Quantile transformation to uniform distribution"""
        from sklearn.preprocessing import QuantileTransformer
        
        qt = QuantileTransformer(output_distribution='uniform')
        transformed = qt.fit_transform(series.values.reshape(-1, 1)).ravel()
        
        # Store transformer for inverse
        self.transformation_params[series.name]['quantile_transformer'] = qt
        self.inverse_functions[series.name] = lambda x: qt.inverse_transform(
            x.values.reshape(-1, 1)
        ).ravel()
        
        return pd.Series(transformed, index=series.index, name=series.name)
    
    def _rank_transform(self, series: pd.Series) -> pd.Series:
        """Rank transformation"""
        return series.rank(pct=True)
    
    def _binning_transform(
        self,
        series: pd.Series,
        n_bins: int = 5,
        strategy: str = 'quantile'
    ) -> pd.Series:
        """Discretize into bins"""
        kbd = KBinsDiscretizer(n_bins=n_bins, encode='ordinal', strategy=strategy)
        transformed = kbd.fit_transform(series.values.reshape(-1, 1)).ravel()
        
        self.transformation_params[series.name]['binner'] = kbd
        
        return pd.Series(transformed, index=series.index, name=series.name)
    
    def _binarize_transform(
        self,
        series: pd.Series,
        threshold: float = 0.0
    ) -> pd.Series:
        """Binarize based on threshold"""
        binarizer = Binarizer(threshold=threshold)
        transformed = binarizer.fit_transform(series.values.reshape(-1, 1)).ravel()
        
        return pd.Series(transformed, index=series.index, name=series.name)
    
    def _difference_transform(
        self,
        series: pd.Series,
        periods: int = 1
    ) -> pd.Series:
        """Difference transformation for time series"""
        return series.diff(periods=periods)
    
    def _cumulative_transform(
        self,
        series: pd.Series,
        method: str = 'sum'
    ) -> pd.Series:
        """Cumulative transformation"""
        if method == 'sum':
            return series.cumsum()
        elif method == 'product':
            return series.cumprod()
        elif method == 'max':
            return series.cummax()
        elif method == 'min':
            return series.cummin()
        else:
            return series
    
    def _rolling_transform(
        self,
        series: pd.Series,
        window: int = 3,
        method: str = 'mean'
    ) -> pd.Series:
        """Rolling window transformation"""
        rolling = series.rolling(window=window, min_periods=1)
        
        if method == 'mean':
            return rolling.mean()
        elif method == 'std':
            return rolling.std()
        elif method == 'min':
            return rolling.min()
        elif method == 'max':
            return rolling.max()
        elif method == 'median':
            return rolling.median()
        else:
            return series
    
    def _lag_transform(
        self,
        series: pd.Series,
        periods: int = 1
    ) -> pd.Series:
        """Lag transformation for time series"""
        return series.shift(periods=periods)
    
    def _custom_transform(
        self,
        series: pd.Series,
        func: Callable,
        inverse_func: Optional[Callable] = None
    ) -> pd.Series:
        """Apply custom transformation function"""
        transformed = series.apply(func)
        
        if inverse_func:
            self.inverse_functions[series.name] = inverse_func
        
        return transformed
    
    def save_config(self, filepath: Union[str, Path]) -> None:
        """Save transformation configuration"""
        config = {
            "transformations": {
                col: trans.value for col, trans in self.transformations.items()
            },
            "parameters": self.transformation_params
        }
        
        filepath = Path(filepath)
        with open(filepath, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        logger.info(f"Saved transformation config to {filepath}")
    
    def load_config(self, filepath: Union[str, Path]) -> None:
        """Load transformation configuration"""
        filepath = Path(filepath)
        
        with open(filepath, 'r') as f:
            config = json.load(f)
        
        self.transformations = {
            col: TransformationType(trans)
            for col, trans in config["transformations"].items()
        }
        self.transformation_params = config["parameters"]
        
        logger.info(f"Loaded transformation config from {filepath}")
    
    def get_transformation_summary(self) -> Dict[str, Any]:
        """Get summary of applied transformations"""
        return {
            "n_transformations": len(self.transformations),
            "transformations": {
                col: {
                    "type": trans.value,
                    "params": self.transformation_params.get(col, {}),
                    "has_inverse": col in self.inverse_functions
                }
                for col, trans in self.transformations.items()
            }
        }


class TimeSeriesTransformer:
    """Specialized transformations for time series data"""
    
    def __init__(self):
        """Initialize time series transformer"""
        self.transformations = {}
    
    def create_time_features(
        self,
        df: pd.DataFrame,
        date_column: str,
        features: List[str] = ['year', 'month', 'day', 'dayofweek', 'quarter']
    ) -> pd.DataFrame:
        """
        Create time-based features.
        
        Args:
            df: Input DataFrame
            date_column: Name of date column
            features: List of features to create
            
        Returns:
            DataFrame with time features
        """
        df = df.copy()
        
        # Ensure datetime
        df[date_column] = pd.to_datetime(df[date_column])
        
        # Create features
        if 'year' in features:
            df[f'{date_column}_year'] = df[date_column].dt.year
        if 'month' in features:
            df[f'{date_column}_month'] = df[date_column].dt.month
        if 'day' in features:
            df[f'{date_column}_day'] = df[date_column].dt.day
        if 'dayofweek' in features:
            df[f'{date_column}_dayofweek'] = df[date_column].dt.dayofweek
        if 'quarter' in features:
            df[f'{date_column}_quarter'] = df[date_column].dt.quarter
        if 'weekofyear' in features:
            df[f'{date_column}_weekofyear'] = df[date_column].dt.isocalendar().week
        if 'hour' in features:
            df[f'{date_column}_hour'] = df[date_column].dt.hour
        if 'minute' in features:
            df[f'{date_column}_minute'] = df[date_column].dt.minute
        
        return df
    
    def create_lag_features(
        self,
        df: pd.DataFrame,
        columns: List[str],
        lags: List[int] = [1, 2, 3]
    ) -> pd.DataFrame:
        """Create lag features"""
        df = df.copy()
        
        for col in columns:
            for lag in lags:
                df[f'{col}_lag_{lag}'] = df[col].shift(lag)
        
        return df
    
    def create_rolling_features(
        self,
        df: pd.DataFrame,
        columns: List[str],
        windows: List[int] = [3, 7],
        stats: List[str] = ['mean', 'std']
    ) -> pd.DataFrame:
        """Create rolling window features"""
        df = df.copy()
        
        for col in columns:
            for window in windows:
                for stat in stats:
                    feature_name = f'{col}_rolling_{window}_{stat}'
                    
                    if stat == 'mean':
                        df[feature_name] = df[col].rolling(window=window, min_periods=1).mean()
                    elif stat == 'std':
                        df[feature_name] = df[col].rolling(window=window, min_periods=1).std()
                    elif stat == 'min':
                        df[feature_name] = df[col].rolling(window=window, min_periods=1).min()
                    elif stat == 'max':
                        df[feature_name] = df[col].rolling(window=window, min_periods=1).max()
        
        return df
    
    def detrend(
        self,
        series: pd.Series,
        method: str = 'linear'
    ) -> pd.Series:
        """Remove trend from time series"""
        from scipy import signal
        
        if method == 'linear':
            detrended = signal.detrend(series.dropna())
            result = series.copy()
            result[series.notna()] = detrended
            return result
        elif method == 'difference':
            return series.diff()
        else:
            return series
    
    def seasonal_decompose(
        self,
        series: pd.Series,
        period: Optional[int] = None
    ) -> Dict[str, pd.Series]:
        """Decompose time series into trend, seasonal, and residual"""
        from statsmodels.tsa.seasonal import seasonal_decompose
        
        # Need at least 2 periods of data
        if period and len(series) < 2 * period:
            logger.warning("Not enough data for seasonal decomposition")
            return {
                'trend': series,
                'seasonal': pd.Series(0, index=series.index),
                'residual': pd.Series(0, index=series.index)
            }
        
        try:
            decomposition = seasonal_decompose(
                series,
                period=period,
                extrapolate_trend='freq'
            )
            
            return {
                'trend': decomposition.trend,
                'seasonal': decomposition.seasonal,
                'residual': decomposition.resid
            }
        except:
            logger.warning("Seasonal decomposition failed")
            return {
                'trend': series,
                'seasonal': pd.Series(0, index=series.index),
                'residual': pd.Series(0, index=series.index)
            }