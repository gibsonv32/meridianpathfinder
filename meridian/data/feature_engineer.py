"""Feature engineering utilities for MERIDIAN"""

from typing import Any, Dict, List, Optional, Union, Tuple
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.preprocessing import (
    PolynomialFeatures,
    OneHotEncoder,
    LabelEncoder,
    OrdinalEncoder,
    StandardScaler,
    MinMaxScaler,
    RobustScaler,
    QuantileTransformer,
    PowerTransformer
)
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.feature_selection import (
    SelectKBest,
    f_classif,
    f_regression,
    mutual_info_classif,
    mutual_info_regression,
    RFE,
    SelectFromModel
)
import warnings
warnings.filterwarnings('ignore')

from meridian.logging_config import get_logger
from meridian.utils.exceptions import DataError, ErrorContext

logger = get_logger("meridian.data.feature_engineer")


class FeatureType(Enum):
    """Feature engineering types"""
    POLYNOMIAL = "polynomial"
    INTERACTION = "interaction"
    BINNING = "binning"
    ENCODING = "encoding"
    SCALING = "scaling"
    TEXT = "text"
    TIME = "time"
    AGGREGATION = "aggregation"
    MATHEMATICAL = "mathematical"
    DOMAIN = "domain"


class EncodingStrategy(Enum):
    """Categorical encoding strategies"""
    ONEHOT = "onehot"
    LABEL = "label"
    ORDINAL = "ordinal"
    TARGET = "target"
    FREQUENCY = "frequency"
    BINARY = "binary"
    HASHING = "hashing"
    EMBEDDING = "embedding"


class ScalingStrategy(Enum):
    """Feature scaling strategies"""
    STANDARD = "standard"
    MINMAX = "minmax"
    ROBUST = "robust"
    QUANTILE = "quantile"
    POWER = "power"
    NORMALIZER = "normalizer"


class FeatureEngineer:
    """Comprehensive feature engineering pipeline"""
    
    def __init__(self):
        """Initialize feature engineer"""
        self.encoders = {}
        self.scalers = {}
        self.transformers = {}
        self.feature_metadata = {}
        self.original_columns = []
        self.engineered_features = []
    
    def fit_transform(
        self,
        df: pd.DataFrame,
        target: Optional[pd.Series] = None,
        auto_engineer: bool = True
    ) -> pd.DataFrame:
        """
        Fit and transform features.
        
        Args:
            df: Input DataFrame
            target: Target variable (for supervised feature engineering)
            auto_engineer: Automatically engineer features based on data types
            
        Returns:
            DataFrame with engineered features
        """
        logger.info(f"Engineering features for dataset with shape {df.shape}")
        
        with ErrorContext("feature_engineering", n_features=df.shape[1]):
            # Store original columns
            self.original_columns = df.columns.tolist()
            df_engineered = df.copy()
            
            if auto_engineer:
                # Automatic feature engineering based on data types
                df_engineered = self._auto_engineer_features(df_engineered, target)
            
            # Track engineered features
            self.engineered_features = [
                col for col in df_engineered.columns 
                if col not in self.original_columns
            ]
            
            logger.info(
                f"Feature engineering complete. "
                f"Original: {len(self.original_columns)}, "
                f"Engineered: {len(self.engineered_features)}, "
                f"Total: {len(df_engineered.columns)}"
            )
            
            return df_engineered
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform new data using fitted encoders/scalers.
        
        Args:
            df: New DataFrame to transform
            
        Returns:
            Transformed DataFrame
        """
        if not self.encoders and not self.scalers and not self.transformers:
            raise DataError("FeatureEngineer must be fitted before transform")
        
        df_transformed = df.copy()
        
        # Apply fitted transformations
        for col, encoder in self.encoders.items():
            if col in df.columns:
                df_transformed[col] = encoder.transform(df[[col]])
        
        for col, scaler in self.scalers.items():
            if col in df.columns:
                df_transformed[col] = scaler.transform(df[[col]])
        
        return df_transformed
    
    def _auto_engineer_features(
        self,
        df: pd.DataFrame,
        target: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """Automatically engineer features based on data types"""
        
        # Separate features by type
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Engineer numeric features
        if numeric_cols:
            df = self._engineer_numeric_features(df, numeric_cols)
        
        # Engineer categorical features
        if categorical_cols:
            df = self._engineer_categorical_features(df, categorical_cols, target)
        
        # Engineer datetime features
        if datetime_cols:
            df = self._engineer_datetime_features(df, datetime_cols)
        
        # Engineer interaction features
        if len(numeric_cols) > 1:
            df = self._engineer_interaction_features(df, numeric_cols[:5])  # Limit to avoid explosion
        
        return df
    
    def _engineer_numeric_features(
        self,
        df: pd.DataFrame,
        columns: List[str]
    ) -> pd.DataFrame:
        """Engineer features from numeric columns"""
        
        for col in columns:
            if df[col].nunique() > 10:  # Continuous variable
                # Add polynomial features for important columns
                if df[col].std() > 0:
                    # Square
                    df[f"{col}_squared"] = df[col] ** 2
                    # Square root (for non-negative values)
                    if (df[col] >= 0).all():
                        df[f"{col}_sqrt"] = np.sqrt(df[col])
                    # Log transform (for positive values)
                    if (df[col] > 0).all():
                        df[f"{col}_log"] = np.log(df[col])
                    
                # Binning
                df[f"{col}_binned"] = pd.qcut(
                    df[col], 
                    q=5, 
                    labels=['very_low', 'low', 'medium', 'high', 'very_high'],
                    duplicates='drop'
                )
        
        return df
    
    def _engineer_categorical_features(
        self,
        df: pd.DataFrame,
        columns: List[str],
        target: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """Engineer features from categorical columns"""
        
        for col in columns:
            unique_values = df[col].nunique()
            
            # Frequency encoding
            freq_encoding = df[col].value_counts().to_dict()
            df[f"{col}_frequency"] = df[col].map(freq_encoding)
            
            # One-hot encoding for low cardinality
            if unique_values <= 10:
                # Create dummy variables
                dummies = pd.get_dummies(df[col], prefix=col, dummy_na=True)
                df = pd.concat([df, dummies], axis=1)
                # Drop original column
                df = df.drop(columns=[col])
            
            # Label encoding for medium cardinality
            elif unique_values <= 50:
                encoder = LabelEncoder()
                df[f"{col}_encoded"] = encoder.fit_transform(df[col].fillna('missing'))
                self.encoders[f"{col}_encoded"] = encoder
            
            # Target encoding for high cardinality (if target provided)
            elif target is not None and unique_values > 50:
                target_mean = target.mean()
                target_encoding = df.groupby(col)[target.name].mean().to_dict()
                df[f"{col}_target_encoded"] = df[col].map(target_encoding).fillna(target_mean)
        
        return df
    
    def _engineer_datetime_features(
        self,
        df: pd.DataFrame,
        columns: List[str]
    ) -> pd.DataFrame:
        """Engineer features from datetime columns"""
        
        for col in columns:
            # Extract components
            df[f"{col}_year"] = df[col].dt.year
            df[f"{col}_month"] = df[col].dt.month
            df[f"{col}_day"] = df[col].dt.day
            df[f"{col}_dayofweek"] = df[col].dt.dayofweek
            df[f"{col}_quarter"] = df[col].dt.quarter
            df[f"{col}_weekofyear"] = df[col].dt.isocalendar().week
            
            # Cyclical encoding for periodic features
            df[f"{col}_month_sin"] = np.sin(2 * np.pi * df[col].dt.month / 12)
            df[f"{col}_month_cos"] = np.cos(2 * np.pi * df[col].dt.month / 12)
            df[f"{col}_day_sin"] = np.sin(2 * np.pi * df[col].dt.day / 31)
            df[f"{col}_day_cos"] = np.cos(2 * np.pi * df[col].dt.day / 31)
            
            # Is weekend/holiday
            df[f"{col}_is_weekend"] = (df[col].dt.dayofweek >= 5).astype(int)
            
            # Time since epoch (for trend)
            df[f"{col}_timestamp"] = df[col].astype(np.int64) / 10**9
        
        return df
    
    def _engineer_interaction_features(
        self,
        df: pd.DataFrame,
        columns: List[str],
        max_interactions: int = 10
    ) -> pd.DataFrame:
        """Engineer interaction features between columns"""
        
        interactions_created = 0
        
        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                if interactions_created >= max_interactions:
                    break
                
                col1, col2 = columns[i], columns[j]
                
                # Multiplication
                df[f"{col1}_x_{col2}"] = df[col1] * df[col2]
                
                # Division (avoid division by zero)
                if not (df[col2] == 0).any():
                    df[f"{col1}_div_{col2}"] = df[col1] / df[col2]
                
                interactions_created += 2
        
        return df
    
    def create_polynomial_features(
        self,
        df: pd.DataFrame,
        columns: List[str],
        degree: int = 2,
        include_bias: bool = False
    ) -> pd.DataFrame:
        """
        Create polynomial features.
        
        Args:
            df: Input DataFrame
            columns: Columns to create polynomial features from
            degree: Polynomial degree
            include_bias: Include bias term
            
        Returns:
            DataFrame with polynomial features
        """
        poly = PolynomialFeatures(degree=degree, include_bias=include_bias)
        poly_features = poly.fit_transform(df[columns])
        
        # Get feature names
        feature_names = poly.get_feature_names_out(columns)
        
        # Create DataFrame
        poly_df = pd.DataFrame(poly_features, columns=feature_names, index=df.index)
        
        # Merge with original
        df = pd.concat([df, poly_df.iloc[:, len(columns):]], axis=1)
        
        self.transformers['polynomial'] = poly
        
        return df
    
    def create_text_features(
        self,
        df: pd.DataFrame,
        text_column: str,
        method: str = "tfidf",
        max_features: int = 100
    ) -> pd.DataFrame:
        """
        Create features from text data.
        
        Args:
            df: Input DataFrame
            text_column: Column containing text
            method: 'tfidf' or 'count'
            max_features: Maximum number of features
            
        Returns:
            DataFrame with text features
        """
        if method == "tfidf":
            vectorizer = TfidfVectorizer(max_features=max_features)
        else:
            vectorizer = CountVectorizer(max_features=max_features)
        
        # Fit and transform
        text_features = vectorizer.fit_transform(df[text_column].fillna(''))
        
        # Create DataFrame
        feature_names = [f"{text_column}_{method}_{i}" for i in range(text_features.shape[1])]
        text_df = pd.DataFrame(
            text_features.toarray(),
            columns=feature_names,
            index=df.index
        )
        
        # Merge with original
        df = pd.concat([df, text_df], axis=1)
        
        self.transformers[f'{text_column}_{method}'] = vectorizer
        
        return df
    
    def create_aggregation_features(
        self,
        df: pd.DataFrame,
        group_cols: List[str],
        agg_cols: List[str],
        agg_funcs: List[str] = ['mean', 'std', 'min', 'max']
    ) -> pd.DataFrame:
        """
        Create aggregation features.
        
        Args:
            df: Input DataFrame
            group_cols: Columns to group by
            agg_cols: Columns to aggregate
            agg_funcs: Aggregation functions
            
        Returns:
            DataFrame with aggregation features
        """
        for group_col in group_cols:
            for agg_col in agg_cols:
                for func in agg_funcs:
                    # Calculate aggregation
                    agg_name = f"{agg_col}_{func}_by_{group_col}"
                    agg_values = df.groupby(group_col)[agg_col].transform(func)
                    df[agg_name] = agg_values
        
        return df
    
    def scale_features(
        self,
        df: pd.DataFrame,
        columns: Optional[List[str]] = None,
        strategy: Union[str, ScalingStrategy] = ScalingStrategy.STANDARD
    ) -> pd.DataFrame:
        """
        Scale numeric features.
        
        Args:
            df: Input DataFrame
            columns: Columns to scale (None for all numeric)
            strategy: Scaling strategy
            
        Returns:
            DataFrame with scaled features
        """
        if isinstance(strategy, str):
            strategy = ScalingStrategy(strategy)
        
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
        
        # Select scaler
        if strategy == ScalingStrategy.STANDARD:
            scaler = StandardScaler()
        elif strategy == ScalingStrategy.MINMAX:
            scaler = MinMaxScaler()
        elif strategy == ScalingStrategy.ROBUST:
            scaler = RobustScaler()
        elif strategy == ScalingStrategy.QUANTILE:
            scaler = QuantileTransformer()
        elif strategy == ScalingStrategy.POWER:
            scaler = PowerTransformer()
        else:
            scaler = StandardScaler()
        
        # Fit and transform
        df[columns] = scaler.fit_transform(df[columns])
        
        # Store scaler
        for col in columns:
            self.scalers[col] = scaler
        
        return df
    
    def select_features(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        method: str = "kbest",
        n_features: int = 10,
        task_type: str = "classification"
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Select top features.
        
        Args:
            X: Feature DataFrame
            y: Target variable
            method: Selection method ('kbest', 'rfe', 'model')
            n_features: Number of features to select
            task_type: 'classification' or 'regression'
            
        Returns:
            Selected features DataFrame and feature names
        """
        if method == "kbest":
            if task_type == "classification":
                selector = SelectKBest(f_classif, k=n_features)
            else:
                selector = SelectKBest(f_regression, k=n_features)
        
        elif method == "rfe":
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            if task_type == "classification":
                estimator = RandomForestClassifier(n_estimators=50, random_state=42)
            else:
                estimator = RandomForestRegressor(n_estimators=50, random_state=42)
            selector = RFE(estimator, n_features_to_select=n_features)
        
        elif method == "model":
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            if task_type == "classification":
                estimator = RandomForestClassifier(n_estimators=50, random_state=42)
            else:
                estimator = RandomForestRegressor(n_estimators=50, random_state=42)
            estimator.fit(X, y)
            selector = SelectFromModel(estimator, max_features=n_features)
        
        else:
            raise ValueError(f"Unknown selection method: {method}")
        
        # Fit and transform
        X_selected = selector.fit_transform(X, y)
        
        # Get selected features
        selected_features = X.columns[selector.get_support()].tolist()
        
        # Create DataFrame
        X_selected_df = pd.DataFrame(X_selected, columns=selected_features, index=X.index)
        
        return X_selected_df, selected_features
    
    def reduce_dimensions(
        self,
        df: pd.DataFrame,
        n_components: int = 10,
        method: str = "pca"
    ) -> pd.DataFrame:
        """
        Reduce dimensionality.
        
        Args:
            df: Input DataFrame
            n_components: Number of components
            method: 'pca' or 'svd'
            
        Returns:
            DataFrame with reduced dimensions
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if method == "pca":
            reducer = PCA(n_components=min(n_components, len(numeric_cols)))
        else:
            reducer = TruncatedSVD(n_components=min(n_components, len(numeric_cols)))
        
        # Fit and transform
        components = reducer.fit_transform(df[numeric_cols])
        
        # Create DataFrame
        component_cols = [f"{method}_component_{i}" for i in range(components.shape[1])]
        components_df = pd.DataFrame(components, columns=component_cols, index=df.index)
        
        # Add to original DataFrame
        df = pd.concat([df, components_df], axis=1)
        
        self.transformers[method] = reducer
        
        # Log explained variance
        if hasattr(reducer, 'explained_variance_ratio_'):
            logger.info(f"Explained variance: {reducer.explained_variance_ratio_.sum():.2%}")
        
        return df
    
    def get_feature_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        method: str = "mutual_info",
        task_type: str = "classification"
    ) -> pd.DataFrame:
        """
        Calculate feature importance.
        
        Args:
            X: Feature DataFrame
            y: Target variable
            method: 'mutual_info' or 'model'
            task_type: 'classification' or 'regression'
            
        Returns:
            DataFrame with feature importance scores
        """
        if method == "mutual_info":
            if task_type == "classification":
                scores = mutual_info_classif(X, y)
            else:
                scores = mutual_info_regression(X, y)
        
        elif method == "model":
            from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
            if task_type == "classification":
                model = RandomForestClassifier(n_estimators=100, random_state=42)
            else:
                model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X, y)
            scores = model.feature_importances_
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Create importance DataFrame
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'importance': scores
        }).sort_values('importance', ascending=False)
        
        return importance_df
    
    def get_engineering_summary(self) -> Dict[str, Any]:
        """Get summary of feature engineering performed"""
        return {
            "original_features": len(self.original_columns),
            "engineered_features": len(self.engineered_features),
            "total_features": len(self.original_columns) + len(self.engineered_features),
            "encoders_fitted": list(self.encoders.keys()),
            "scalers_fitted": list(self.scalers.keys()),
            "transformers_fitted": list(self.transformers.keys()),
            "feature_types": {
                "original": self.original_columns,
                "engineered": self.engineered_features
            }
        }


class AutoFeatureEngineer:
    """Automated feature engineering based on data characteristics"""
    
    def __init__(self):
        """Initialize auto feature engineer"""
        self.engineer = FeatureEngineer()
        self.feature_importance = None
        self.selected_features = None
    
    def fit_transform(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None,
        task_type: str = "auto",
        target_feature_count: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Automatically engineer and select features.
        
        Args:
            X: Input features
            y: Target variable
            task_type: 'classification', 'regression', or 'auto'
            target_feature_count: Target number of final features
            
        Returns:
            DataFrame with engineered and selected features
        """
        logger.info("Starting automated feature engineering")
        
        # Detect task type if auto
        if task_type == "auto" and y is not None:
            if y.dtype in ['int64', 'int32'] and y.nunique() < 20:
                task_type = "classification"
            else:
                task_type = "regression"
        
        # Engineer features
        X_engineered = self.engineer.fit_transform(X, y, auto_engineer=True)
        
        # Remove highly correlated features
        X_engineered = self._remove_correlated_features(X_engineered)
        
        # Select features if target specified
        if target_feature_count and y is not None:
            X_engineered, selected = self.engineer.select_features(
                X_engineered,
                y,
                method="kbest",
                n_features=target_feature_count,
                task_type=task_type
            )
            self.selected_features = selected
        
        # Calculate feature importance if target provided
        if y is not None:
            self.feature_importance = self.engineer.get_feature_importance(
                X_engineered,
                y,
                task_type=task_type
            )
        
        logger.info(f"Auto feature engineering complete. Final shape: {X_engineered.shape}")
        
        return X_engineered
    
    def _remove_correlated_features(
        self,
        df: pd.DataFrame,
        threshold: float = 0.95
    ) -> pd.DataFrame:
        """Remove highly correlated features"""
        # Calculate correlation matrix
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        corr_matrix = df[numeric_cols].corr().abs()
        
        # Find features to remove
        upper_triangle = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )
        
        to_drop = [
            column for column in upper_triangle.columns
            if any(upper_triangle[column] > threshold)
        ]
        
        if to_drop:
            logger.info(f"Removing {len(to_drop)} highly correlated features")
            df = df.drop(columns=to_drop)
        
        return df