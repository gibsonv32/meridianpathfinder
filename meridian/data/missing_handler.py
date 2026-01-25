"""Missing value handling strategies for MERIDIAN"""

from typing import Any, Dict, List, Optional, Union
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

from meridian.logging_config import get_logger
from meridian.utils.exceptions import DataError, ErrorContext

logger = get_logger("meridian.data.missing_handler")


class MissingStrategy(Enum):
    """Missing value imputation strategies"""
    DROP = "drop"
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    FORWARD_FILL = "forward_fill"
    BACKWARD_FILL = "backward_fill"
    INTERPOLATE = "interpolate"
    CONSTANT = "constant"
    KNN = "knn"
    ITERATIVE = "iterative"
    RANDOM_FOREST = "random_forest"
    INDICATOR = "indicator"
    SMART = "smart"  # Auto-select best strategy


class MissingValueHandler:
    """Handle missing values with various strategies"""
    
    def __init__(
        self,
        strategy: Union[str, MissingStrategy] = MissingStrategy.SMART,
        threshold: float = 0.5,
        add_indicator: bool = False,
        constant_value: Any = 0
    ):
        """
        Initialize missing value handler.
        
        Args:
            strategy: Imputation strategy
            threshold: Threshold for dropping columns (if > threshold missing)
            add_indicator: Add binary indicator for missingness
            constant_value: Value for constant imputation
        """
        if isinstance(strategy, str):
            strategy = MissingStrategy(strategy)
        
        self.strategy = strategy
        self.threshold = threshold
        self.add_indicator = add_indicator
        self.constant_value = constant_value
        self.imputers = {}
        self.strategies_per_column = {}
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fit and transform data with missing value handling.
        
        Args:
            df: DataFrame with missing values
            
        Returns:
            DataFrame with imputed values
        """
        logger.info(f"Handling missing values with strategy: {self.strategy.value}")
        
        with ErrorContext("missing_value_handling", strategy=self.strategy.value):
            # Create copy to avoid modifying original
            df_imputed = df.copy()
            
            # Add missing indicators if requested
            if self.add_indicator:
                df_imputed = self._add_missing_indicators(df_imputed)
            
            # Handle based on strategy
            if self.strategy == MissingStrategy.DROP:
                df_imputed = self._handle_drop(df_imputed)
            
            elif self.strategy == MissingStrategy.SMART:
                df_imputed = self._handle_smart(df_imputed)
            
            else:
                # Apply single strategy to all columns
                for col in df.columns:
                    if df[col].isna().any():
                        df_imputed[col] = self._impute_column(
                            df_imputed[col],
                            df_imputed,
                            self.strategy
                        )
            
            # Log results
            original_missing = df.isna().sum().sum()
            final_missing = df_imputed.isna().sum().sum()
            logger.info(
                f"Missing value handling complete. "
                f"Original: {original_missing}, Final: {final_missing}"
            )
            
            return df_imputed
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform new data using fitted imputers.
        
        Args:
            df: New DataFrame to transform
            
        Returns:
            Transformed DataFrame
        """
        if not self.imputers and not self.strategies_per_column:
            raise DataError("Handler must be fitted before transform")
        
        df_imputed = df.copy()
        
        # Add missing indicators if used during fit
        if self.add_indicator:
            df_imputed = self._add_missing_indicators(df_imputed)
        
        # Apply fitted strategies
        for col, strategy in self.strategies_per_column.items():
            if col in df.columns and df[col].isna().any():
                if col in self.imputers:
                    # Use fitted imputer
                    imputer = self.imputers[col]
                    if hasattr(imputer, 'transform'):
                        df_imputed[col] = imputer.transform(df[[col]]).ravel()
                    else:
                        # Simple value imputation
                        df_imputed[col].fillna(imputer, inplace=True)
                else:
                    # Apply strategy without fitting
                    df_imputed[col] = self._impute_column(
                        df_imputed[col],
                        df_imputed,
                        strategy,
                        fit=False
                    )
        
        return df_imputed
    
    def _handle_drop(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values by dropping"""
        # Drop columns with too many missing values
        missing_ratio = df.isna().sum() / len(df)
        cols_to_drop = missing_ratio[missing_ratio > self.threshold].index.tolist()
        
        if cols_to_drop:
            logger.warning(f"Dropping columns with >{self.threshold*100}% missing: {cols_to_drop}")
            df = df.drop(columns=cols_to_drop)
        
        # Drop rows with any missing values
        df = df.dropna()
        
        return df
    
    def _handle_smart(self, df: pd.DataFrame) -> pd.DataFrame:
        """Smart strategy selection per column"""
        for col in df.columns:
            if not df[col].isna().any():
                continue
            
            missing_ratio = df[col].isna().sum() / len(df)
            
            # Drop column if too many missing
            if missing_ratio > self.threshold:
                logger.warning(f"Dropping column {col}: {missing_ratio:.1%} missing")
                df = df.drop(columns=[col])
                continue
            
            # Select strategy based on data type and distribution
            strategy = self._select_best_strategy(df[col], df)
            self.strategies_per_column[col] = strategy
            
            logger.debug(f"Column {col}: using {strategy.value} strategy")
            df[col] = self._impute_column(df[col], df, strategy)
        
        return df
    
    def _select_best_strategy(
        self,
        series: pd.Series,
        df: pd.DataFrame
    ) -> MissingStrategy:
        """Select best imputation strategy for column"""
        dtype = series.dtype
        missing_ratio = series.isna().sum() / len(series)
        
        # Numeric columns
        if dtype in ['int64', 'float64', 'int32', 'float32']:
            series_clean = series.dropna()
            
            # Check distribution
            if len(series_clean) > 0:
                skewness = series_clean.skew()
                unique_ratio = series_clean.nunique() / len(series_clean)
                
                # Time series pattern detection
                if self._is_time_series(series_clean):
                    return MissingStrategy.INTERPOLATE
                
                # Low missing + normal distribution -> mean
                if missing_ratio < 0.1 and abs(skewness) < 1:
                    return MissingStrategy.MEAN
                
                # Skewed distribution -> median
                elif abs(skewness) > 1:
                    return MissingStrategy.MEDIAN
                
                # Many missing values -> advanced methods
                elif missing_ratio > 0.2:
                    # If we have other numeric features, use KNN
                    numeric_cols = df.select_dtypes(include=[np.number]).columns
                    if len(numeric_cols) > 1:
                        return MissingStrategy.KNN
                    else:
                        return MissingStrategy.MEDIAN
                
                else:
                    return MissingStrategy.MEDIAN
            
            return MissingStrategy.MEDIAN
        
        # Categorical columns
        elif dtype == 'object' or dtype.name == 'category':
            # Use mode for categorical
            return MissingStrategy.MODE
        
        # Datetime columns
        elif 'datetime' in str(dtype):
            return MissingStrategy.FORWARD_FILL
        
        # Boolean columns
        elif dtype == 'bool':
            return MissingStrategy.MODE
        
        else:
            return MissingStrategy.CONSTANT
    
    def _impute_column(
        self,
        series: pd.Series,
        df: pd.DataFrame,
        strategy: MissingStrategy,
        fit: bool = True
    ) -> pd.Series:
        """Impute missing values in a column"""
        col_name = series.name
        
        if strategy == MissingStrategy.MEAN:
            if fit:
                self.imputers[col_name] = series.mean()
            return series.fillna(self.imputers.get(col_name, series.mean()))
        
        elif strategy == MissingStrategy.MEDIAN:
            if fit:
                self.imputers[col_name] = series.median()
            return series.fillna(self.imputers.get(col_name, series.median()))
        
        elif strategy == MissingStrategy.MODE:
            if fit:
                mode_val = series.mode()
                self.imputers[col_name] = mode_val[0] if len(mode_val) > 0 else self.constant_value
            return series.fillna(self.imputers.get(col_name, self.constant_value))
        
        elif strategy == MissingStrategy.FORWARD_FILL:
            return series.fillna(method='ffill')
        
        elif strategy == MissingStrategy.BACKWARD_FILL:
            return series.fillna(method='bfill')
        
        elif strategy == MissingStrategy.INTERPOLATE:
            return series.interpolate(method='linear')
        
        elif strategy == MissingStrategy.CONSTANT:
            return series.fillna(self.constant_value)
        
        elif strategy == MissingStrategy.KNN:
            return self._knn_impute(series, df, fit)
        
        elif strategy == MissingStrategy.ITERATIVE:
            return self._iterative_impute(series, df, fit)
        
        elif strategy == MissingStrategy.RANDOM_FOREST:
            return self._rf_impute(series, df, fit)
        
        else:
            return series
    
    def _knn_impute(self, series: pd.Series, df: pd.DataFrame, fit: bool = True) -> pd.Series:
        """KNN imputation"""
        col_name = series.name
        
        # Get numeric columns for KNN
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if col_name not in numeric_cols:
            # Fallback for non-numeric
            return series.fillna(series.mode()[0] if len(series.mode()) > 0 else self.constant_value)
        
        # Prepare data
        X = df[numeric_cols].values
        
        if fit:
            imputer = KNNImputer(n_neighbors=5)
            X_imputed = imputer.fit_transform(X)
            self.imputers[col_name] = imputer
        else:
            imputer = self.imputers.get(col_name)
            if imputer:
                X_imputed = imputer.transform(X)
            else:
                return series
        
        # Get imputed column
        col_idx = numeric_cols.index(col_name)
        return pd.Series(X_imputed[:, col_idx], index=series.index, name=col_name)
    
    def _iterative_impute(self, series: pd.Series, df: pd.DataFrame, fit: bool = True) -> pd.Series:
        """Iterative imputation (MICE)"""
        col_name = series.name
        
        # Get numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if col_name not in numeric_cols:
            return series.fillna(series.mode()[0] if len(series.mode()) > 0 else self.constant_value)
        
        X = df[numeric_cols].values
        
        if fit:
            imputer = IterativeImputer(random_state=42, max_iter=10)
            X_imputed = imputer.fit_transform(X)
            self.imputers[col_name] = imputer
        else:
            imputer = self.imputers.get(col_name)
            if imputer:
                X_imputed = imputer.transform(X)
            else:
                return series
        
        col_idx = numeric_cols.index(col_name)
        return pd.Series(X_imputed[:, col_idx], index=series.index, name=col_name)
    
    def _rf_impute(self, series: pd.Series, df: pd.DataFrame, fit: bool = True) -> pd.Series:
        """Random Forest imputation"""
        col_name = series.name
        
        # Prepare features
        feature_cols = [c for c in df.columns if c != col_name and df[c].dtype in ['int64', 'float64']]
        
        if not feature_cols:
            return series.fillna(series.median() if series.dtype in ['int64', 'float64'] else series.mode()[0])
        
        # Split into train (non-missing) and predict (missing)
        mask = series.isna()
        
        if mask.sum() == 0:
            return series
        
        X_train = df.loc[~mask, feature_cols]
        y_train = series[~mask]
        X_pred = df.loc[mask, feature_cols]
        
        # Handle any missing values in features with simple imputation
        X_train = X_train.fillna(X_train.median())
        X_pred = X_pred.fillna(X_train.median())
        
        # Train model
        if series.dtype in ['int64', 'float64']:
            model = RandomForestRegressor(n_estimators=10, random_state=42)
        else:
            model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        model.fit(X_train, y_train)
        
        # Predict missing values
        predictions = model.predict(X_pred)
        
        # Fill missing values
        series_filled = series.copy()
        series_filled[mask] = predictions
        
        return series_filled
    
    def _add_missing_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add binary indicators for missing values"""
        for col in df.columns:
            if df[col].isna().any():
                indicator_col = f"{col}_was_missing"
                df[indicator_col] = df[col].isna().astype(int)
        
        return df
    
    def _is_time_series(self, series: pd.Series) -> bool:
        """Check if series has time series pattern"""
        if len(series) < 10:
            return False
        
        # Check for autocorrelation
        try:
            from statsmodels.stats.diagnostic import acorr_ljungbox
            result = acorr_ljungbox(series.dropna(), lags=min(10, len(series)//2))
            # If p-value < 0.05 for any lag, likely time series
            return (result['lb_pvalue'] < 0.05).any()
        except:
            return False
    
    def get_imputation_summary(self, df_original: pd.DataFrame, df_imputed: pd.DataFrame) -> Dict[str, Any]:
        """Get summary of imputation performed"""
        summary = {
            "total_missing_before": df_original.isna().sum().sum(),
            "total_missing_after": df_imputed.isna().sum().sum(),
            "columns_imputed": {},
            "columns_dropped": [],
            "rows_dropped": len(df_original) - len(df_imputed)
        }
        
        for col in df_original.columns:
            if col not in df_imputed.columns:
                summary["columns_dropped"].append(col)
            elif df_original[col].isna().any():
                summary["columns_imputed"][col] = {
                    "missing_before": df_original[col].isna().sum(),
                    "missing_after": df_imputed[col].isna().sum() if col in df_imputed.columns else 0,
                    "strategy": self.strategies_per_column.get(col, self.strategy).value
                }
        
        return summary