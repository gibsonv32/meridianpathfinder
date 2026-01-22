"""Automated Feature Engineering Module for MERIDIAN

Provides:
- Automated feature generation
- Interaction features
- Polynomial features  
- Time-based features
- Domain-specific transformations
- Feature selection
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.preprocessing import PolynomialFeatures
from sklearn.feature_selection import (
    SelectKBest, f_classif, f_regression,
    mutual_info_classif, mutual_info_regression,
    RFE, SelectFromModel
)
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

logger = logging.getLogger(__name__)


@dataclass
class FeatureEngineeringResult:
    """Results from automated feature engineering"""
    
    original_features: List[str]
    engineered_features: List[str]
    selected_features: List[str]
    feature_importance: Dict[str, float]
    transformations_applied: List[str]
    n_features_before: int
    n_features_after: int
    selection_method: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "original_features": self.original_features,
            "engineered_features": self.engineered_features,
            "selected_features": self.selected_features,
            "feature_importance": self.feature_importance,
            "transformations_applied": self.transformations_applied,
            "n_features_before": self.n_features_before,
            "n_features_after": self.n_features_after,
            "selection_method": self.selection_method
        }


class AutoFeatureEngineer:
    """Automated feature engineering pipeline"""
    
    def __init__(self, 
                 task_type: str = "classification",
                 max_features: Optional[int] = None,
                 selection_method: str = "auto"):
        """
        Initialize feature engineer
        
        Args:
            task_type: 'classification' or 'regression'
            max_features: Maximum number of features to select
            selection_method: 'auto', 'univariate', 'model_based', 'rfe'
        """
        self.task_type = task_type
        self.max_features = max_features
        self.selection_method = selection_method
        self.transformers = []
        self.selector = None
        self.feature_names = []
    
    def engineer_features(self, 
                          X: pd.DataFrame,
                          y: Optional[pd.Series] = None,
                          include_interactions: bool = True,
                          include_polynomial: bool = True,
                          include_ratios: bool = True,
                          include_log: bool = True,
                          include_binning: bool = True,
                          select_features: bool = True) -> Tuple[pd.DataFrame, FeatureEngineeringResult]:
        """
        Perform automated feature engineering
        
        Args:
            X: Input features
            y: Target variable (needed for feature selection)
            include_interactions: Create interaction features
            include_polynomial: Create polynomial features
            include_ratios: Create ratio features
            include_log: Create log transformations
            include_binning: Create binned features
            select_features: Perform feature selection
            
        Returns:
            Tuple of (transformed_X, FeatureEngineeringResult)
        """
        original_features = X.columns.tolist()
        X_engineered = X.copy()
        transformations = []
        
        # Numeric and categorical columns
        numeric_cols = X_engineered.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = X_engineered.select_dtypes(exclude=[np.number]).columns.tolist()
        
        # 1. Handle categorical features
        if categorical_cols:
            X_engineered = self._encode_categorical(X_engineered, categorical_cols)
            transformations.append("categorical_encoding")
        
        # 2. Create interaction features
        if include_interactions and len(numeric_cols) >= 2:
            X_engineered = self._create_interactions(X_engineered, numeric_cols)
            transformations.append("interactions")
        
        # 3. Create polynomial features
        if include_polynomial and len(numeric_cols) > 0:
            X_engineered = self._create_polynomial(X_engineered, numeric_cols)
            transformations.append("polynomial")
        
        # 4. Create ratio features
        if include_ratios and len(numeric_cols) >= 2:
            X_engineered = self._create_ratios(X_engineered, numeric_cols)
            transformations.append("ratios")
        
        # 5. Create log transformations
        if include_log and len(numeric_cols) > 0:
            X_engineered = self._create_log_features(X_engineered, numeric_cols)
            transformations.append("log_transform")
        
        # 6. Create binned features
        if include_binning and len(numeric_cols) > 0:
            X_engineered = self._create_binned_features(X_engineered, numeric_cols)
            transformations.append("binning")
        
        # 7. Remove highly correlated features
        X_engineered = self._remove_correlated_features(X_engineered)
        
        engineered_features = X_engineered.columns.tolist()
        
        # 8. Feature selection
        selected_features = engineered_features
        feature_importance = {}
        
        if select_features and y is not None:
            X_selected, selected_features, feature_importance = self._select_features(
                X_engineered, y
            )
            X_engineered = X_selected
        
        # Create result
        result = FeatureEngineeringResult(
            original_features=original_features,
            engineered_features=engineered_features,
            selected_features=selected_features,
            feature_importance=feature_importance,
            transformations_applied=transformations,
            n_features_before=len(original_features),
            n_features_after=len(selected_features),
            selection_method=self.selection_method if select_features else "none"
        )
        
        return X_engineered, result
    
    def _encode_categorical(self, X: pd.DataFrame, categorical_cols: List[str]) -> pd.DataFrame:
        """Encode categorical features"""
        X_encoded = X.copy()
        
        for col in categorical_cols:
            # Use one-hot encoding for low cardinality
            if X[col].nunique() <= 10:
                dummies = pd.get_dummies(X[col], prefix=col, drop_first=True)
                X_encoded = pd.concat([X_encoded.drop(columns=[col]), dummies], axis=1)
            else:
                # Use target encoding for high cardinality
                # Simple mean encoding for now
                X_encoded[f"{col}_encoded"] = X_encoded[col].factorize()[0]
                X_encoded = X_encoded.drop(columns=[col])
        
        return X_encoded
    
    def _create_interactions(self, X: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
        """Create interaction features"""
        X_inter = X.copy()
        
        # Create top interactions (limit to avoid explosion)
        n_interactions = min(10, len(numeric_cols) * (len(numeric_cols) - 1) // 2)
        interactions_created = 0
        
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                if interactions_created >= n_interactions:
                    break
                    
                # Multiplication interaction
                X_inter[f"{col1}_x_{col2}"] = X[col1] * X[col2]
                interactions_created += 1
            
            if interactions_created >= n_interactions:
                break
        
        return X_inter
    
    def _create_polynomial(self, X: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
        """Create polynomial features"""
        X_poly = X.copy()
        
        # Create squared features for top numeric columns
        cols_to_square = numeric_cols[:5]  # Limit to avoid explosion
        
        for col in cols_to_square:
            X_poly[f"{col}_squared"] = X[col] ** 2
            
            # Also add sqrt for positive values
            if (X[col] >= 0).all():
                X_poly[f"{col}_sqrt"] = np.sqrt(X[col])
        
        return X_poly
    
    def _create_ratios(self, X: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
        """Create ratio features"""
        X_ratio = X.copy()
        
        # Create ratios for top pairs
        n_ratios = min(5, len(numeric_cols) * (len(numeric_cols) - 1) // 2)
        ratios_created = 0
        
        for i, col1 in enumerate(numeric_cols):
            for col2 in numeric_cols[i+1:]:
                if ratios_created >= n_ratios:
                    break
                
                # Avoid division by zero
                if (X[col2] != 0).all():
                    X_ratio[f"{col1}_div_{col2}"] = X[col1] / X[col2]
                    ratios_created += 1
            
            if ratios_created >= n_ratios:
                break
        
        return X_ratio
    
    def _create_log_features(self, X: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
        """Create log transformations"""
        X_log = X.copy()
        
        for col in numeric_cols[:5]:  # Limit to top 5
            # Only for positive values
            if (X[col] > 0).all():
                X_log[f"{col}_log"] = np.log1p(X[col])
            elif (X[col] >= 0).all():
                # Add small constant for zero values
                X_log[f"{col}_log"] = np.log1p(X[col] + 1e-8)
        
        return X_log
    
    def _create_binned_features(self, X: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
        """Create binned features"""
        X_binned = X.copy()
        
        for col in numeric_cols[:3]:  # Limit to top 3
            # Create quantile bins
            try:
                X_binned[f"{col}_bin"], bins = pd.qcut(
                    X[col], q=4, labels=['Q1', 'Q2', 'Q3', 'Q4'], 
                    retbins=True, duplicates='drop'
                )
                # One-hot encode bins
                dummies = pd.get_dummies(X_binned[f"{col}_bin"], prefix=f"{col}_bin")
                X_binned = pd.concat([X_binned.drop(columns=[f"{col}_bin"]), dummies], axis=1)
            except:
                # Skip if binning fails
                pass
        
        return X_binned
    
    def _remove_correlated_features(self, X: pd.DataFrame, threshold: float = 0.95) -> pd.DataFrame:
        """Remove highly correlated features"""
        # Calculate correlation matrix
        numeric_cols = X.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return X
        
        corr_matrix = X[numeric_cols].corr().abs()
        
        # Select upper triangle
        upper_tri = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        
        # Find features with correlation greater than threshold
        to_drop = [column for column in upper_tri.columns if any(upper_tri[column] > threshold)]
        
        # Drop features
        return X.drop(columns=to_drop)
    
    def _select_features(self, X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, List[str], Dict[str, float]]:
        """Perform feature selection"""
        if self.selection_method == "auto":
            # Choose method based on number of features
            if len(X.columns) < 20:
                method = "univariate"
            elif len(X.columns) < 100:
                method = "model_based"
            else:
                method = "univariate"  # Fast for many features
        else:
            method = self.selection_method
        
        # Determine number of features to select
        if self.max_features:
            k = min(self.max_features, len(X.columns))
        else:
            k = min(len(X.columns), max(10, len(X.columns) // 2))
        
        if method == "univariate":
            # Univariate feature selection
            if self.task_type == "classification":
                selector = SelectKBest(score_func=f_classif, k=k)
            else:
                selector = SelectKBest(score_func=f_regression, k=k)
            
            X_selected = selector.fit_transform(X, y)
            selected_indices = selector.get_support(indices=True)
            selected_features = X.columns[selected_indices].tolist()
            
            # Get importance scores
            scores = selector.scores_[selected_indices]
            feature_importance = dict(zip(selected_features, scores / scores.max()))
        
        elif method == "model_based":
            # Model-based feature selection
            if self.task_type == "classification":
                model = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
            else:
                model = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
            
            model.fit(X, y)
            
            # Select from model
            selector = SelectFromModel(model, max_features=k)
            X_selected = selector.fit_transform(X, y)
            selected_indices = selector.get_support(indices=True)
            selected_features = X.columns[selected_indices].tolist()
            
            # Get feature importance
            importances = model.feature_importances_[selected_indices]
            feature_importance = dict(zip(selected_features, importances))
        
        elif method == "rfe":
            # Recursive feature elimination
            if self.task_type == "classification":
                estimator = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
            else:
                estimator = RandomForestRegressor(n_estimators=50, random_state=42, n_jobs=-1)
            
            selector = RFE(estimator, n_features_to_select=k)
            X_selected = selector.fit_transform(X, y)
            selected_features = X.columns[selector.support_].tolist()
            
            # Get ranking
            feature_importance = {}
            for feat, rank in zip(X.columns, selector.ranking_):
                if rank == 1:  # Selected features
                    feature_importance[feat] = 1.0 / rank
        
        else:
            # No selection
            X_selected = X
            selected_features = X.columns.tolist()
            feature_importance = {feat: 1.0 for feat in selected_features}
        
        # Create DataFrame with selected features
        X_selected_df = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
        
        # Sort feature importance
        feature_importance = dict(sorted(feature_importance.items(), 
                                       key=lambda x: x[1], reverse=True))
        
        return X_selected_df, selected_features, feature_importance


class TimeSeriesFeatureEngineer:
    """Feature engineering specifically for time series data"""
    
    def __init__(self, datetime_col: Optional[str] = None):
        """
        Initialize time series feature engineer
        
        Args:
            datetime_col: Name of datetime column
        """
        self.datetime_col = datetime_col
    
    def create_time_features(self, 
                            df: pd.DataFrame,
                            target_col: Optional[str] = None,
                            lag_periods: List[int] = [1, 7, 30],
                            rolling_windows: List[int] = [7, 30],
                            include_seasonality: bool = True) -> pd.DataFrame:
        """
        Create time series features
        
        Args:
            df: DataFrame with time series data
            target_col: Target column for lag features
            lag_periods: Lag periods to create
            rolling_windows: Rolling window sizes
            include_seasonality: Include seasonal features
            
        Returns:
            DataFrame with time features
        """
        df_time = df.copy()
        
        # Ensure datetime index or column
        if self.datetime_col:
            df_time[self.datetime_col] = pd.to_datetime(df_time[self.datetime_col])
            df_time = df_time.set_index(self.datetime_col)
        
        # 1. Calendar features
        if include_seasonality:
            df_time = self._create_calendar_features(df_time)
        
        # 2. Lag features
        if target_col and target_col in df_time.columns:
            df_time = self._create_lag_features(df_time, target_col, lag_periods)
        
        # 3. Rolling statistics
        if target_col and target_col in df_time.columns:
            df_time = self._create_rolling_features(df_time, target_col, rolling_windows)
        
        # 4. Trend features
        df_time = self._create_trend_features(df_time)
        
        return df_time
    
    def _create_calendar_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create calendar-based features"""
        df_cal = df.copy()
        
        # Extract datetime components
        df_cal['year'] = df_cal.index.year
        df_cal['month'] = df_cal.index.month
        df_cal['day'] = df_cal.index.day
        df_cal['dayofweek'] = df_cal.index.dayofweek
        df_cal['quarter'] = df_cal.index.quarter
        df_cal['dayofyear'] = df_cal.index.dayofyear
        df_cal['weekofyear'] = df_cal.index.isocalendar().week
        
        # Cyclical encoding for periodic features
        df_cal['month_sin'] = np.sin(2 * np.pi * df_cal['month'] / 12)
        df_cal['month_cos'] = np.cos(2 * np.pi * df_cal['month'] / 12)
        df_cal['day_sin'] = np.sin(2 * np.pi * df_cal['day'] / 31)
        df_cal['day_cos'] = np.cos(2 * np.pi * df_cal['day'] / 31)
        df_cal['dayofweek_sin'] = np.sin(2 * np.pi * df_cal['dayofweek'] / 7)
        df_cal['dayofweek_cos'] = np.cos(2 * np.pi * df_cal['dayofweek'] / 7)
        
        # Holiday indicator (simplified - you'd want real holiday calendar)
        df_cal['is_weekend'] = df_cal['dayofweek'].isin([5, 6]).astype(int)
        df_cal['is_month_start'] = df_cal.index.is_month_start.astype(int)
        df_cal['is_month_end'] = df_cal.index.is_month_end.astype(int)
        df_cal['is_quarter_start'] = df_cal.index.is_quarter_start.astype(int)
        df_cal['is_quarter_end'] = df_cal.index.is_quarter_end.astype(int)
        
        return df_cal
    
    def _create_lag_features(self, df: pd.DataFrame, target_col: str, lag_periods: List[int]) -> pd.DataFrame:
        """Create lag features"""
        df_lag = df.copy()
        
        for lag in lag_periods:
            df_lag[f'{target_col}_lag_{lag}'] = df_lag[target_col].shift(lag)
            
            # Difference features
            df_lag[f'{target_col}_diff_{lag}'] = df_lag[target_col].diff(lag)
        
        return df_lag
    
    def _create_rolling_features(self, df: pd.DataFrame, target_col: str, windows: List[int]) -> pd.DataFrame:
        """Create rolling window features"""
        df_roll = df.copy()
        
        for window in windows:
            # Rolling statistics
            df_roll[f'{target_col}_roll_mean_{window}'] = df_roll[target_col].rolling(window).mean()
            df_roll[f'{target_col}_roll_std_{window}'] = df_roll[target_col].rolling(window).std()
            df_roll[f'{target_col}_roll_min_{window}'] = df_roll[target_col].rolling(window).min()
            df_roll[f'{target_col}_roll_max_{window}'] = df_roll[target_col].rolling(window).max()
            
            # Exponential weighted statistics
            df_roll[f'{target_col}_ewm_mean_{window}'] = df_roll[target_col].ewm(span=window).mean()
        
        return df_roll
    
    def _create_trend_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create trend features"""
        df_trend = df.copy()
        
        # Time index as numeric feature
        df_trend['time_index'] = range(len(df_trend))
        
        # Polynomial time features
        df_trend['time_index_squared'] = df_trend['time_index'] ** 2
        df_trend['time_index_cubed'] = df_trend['time_index'] ** 3
        
        return df_trend