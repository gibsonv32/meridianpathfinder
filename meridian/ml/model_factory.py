"""Model Factory for MERIDIAN - Support for multiple ML frameworks"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import joblib
from abc import ABC, abstractmethod

from meridian.logging_config import get_logger
from meridian.utils.exceptions import ErrorContext, MeridianError
from meridian.utils.file_ops import atomic_write, ensure_directory

logger = get_logger("meridian.ml.model_factory")


class BaseModel(ABC):
    """Abstract base class for all ML models"""
    
    def __init__(self, model_type: str, params: Optional[Dict[str, Any]] = None):
        self.model_type = model_type
        self.params = params or {}
        self.model = None
        self.is_fitted = False
        self.metadata = {
            "model_type": model_type,
            "framework": self.get_framework(),
            "params": self.params
        }
    
    @abstractmethod
    def get_framework(self) -> str:
        """Return the framework name"""
        pass
    
    @abstractmethod
    def build(self) -> Any:
        """Build the model instance"""
        pass
    
    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> "BaseModel":
        """Train the model"""
        pass
    
    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        pass
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probabilities (for classifiers)"""
        if hasattr(self.model, 'predict_proba'):
            return self.model.predict_proba(X)
        else:
            # Fallback for models without predict_proba
            predictions = self.predict(X)
            if len(predictions.shape) == 1:
                # Binary classification fallback
                proba = np.zeros((len(predictions), 2))
                proba[:, 1] = predictions
                proba[:, 0] = 1 - predictions
                return proba
            return predictions
    
    def save(self, path: Path) -> Path:
        """Save model to disk"""
        path = Path(path)
        ensure_directory(path.parent)
        
        # Save model
        model_file = path / "model.joblib"
        joblib.dump(self.model, model_file)
        
        # Save metadata
        metadata_file = path / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        logger.info(f"Model saved to {path}")
        return path
    
    @classmethod
    def load(cls, path: Path) -> "BaseModel":
        """Load model from disk"""
        path = Path(path)
        
        # Load metadata
        metadata_file = path / "metadata.json"
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Create instance
        instance = cls(metadata["model_type"], metadata.get("params", {}))
        
        # Load model
        model_file = path / "model.joblib"
        instance.model = joblib.load(model_file)
        instance.is_fitted = True
        instance.metadata = metadata
        
        logger.info(f"Model loaded from {path}")
        return instance


class SklearnModel(BaseModel):
    """Scikit-learn model wrapper"""
    
    def get_framework(self) -> str:
        return "sklearn"
    
    def build(self) -> Any:
        """Build sklearn model based on type"""
        from sklearn.linear_model import LogisticRegression, Ridge, Lasso, ElasticNet
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
        from sklearn.svm import SVC, SVR
        from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
        from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
        from sklearn.naive_bayes import GaussianNB
        from sklearn.neural_network import MLPClassifier, MLPRegressor
        
        model_map = {
            # Classifiers
            "logistic_regression": LogisticRegression,
            "random_forest_classifier": RandomForestClassifier,
            "gradient_boosting_classifier": GradientBoostingClassifier,
            "svc": SVC,
            "knn_classifier": KNeighborsClassifier,
            "decision_tree_classifier": DecisionTreeClassifier,
            "naive_bayes": GaussianNB,
            "mlp_classifier": MLPClassifier,
            
            # Regressors
            "ridge": Ridge,
            "lasso": Lasso,
            "elastic_net": ElasticNet,
            "random_forest_regressor": RandomForestRegressor,
            "gradient_boosting_regressor": GradientBoostingRegressor,
            "svr": SVR,
            "knn_regressor": KNeighborsRegressor,
            "decision_tree_regressor": DecisionTreeRegressor,
            "mlp_regressor": MLPRegressor,
        }
        
        if self.model_type not in model_map:
            raise ValueError(f"Unknown sklearn model type: {self.model_type}")
        
        model_class = model_map[self.model_type]
        self.model = model_class(**self.params)
        return self.model
    
    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs) -> "SklearnModel":
        """Train sklearn model"""
        if self.model is None:
            self.build()
        
        with ErrorContext("sklearn_fit", model_type=self.model_type):
            self.model.fit(X, y, **kwargs)
            self.is_fitted = True
            
            # Update metadata with feature information
            self.metadata["n_features"] = X.shape[1]
            self.metadata["feature_names"] = list(X.columns)
            self.metadata["n_samples_trained"] = len(X)
            
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.is_fitted:
            raise MeridianError("Model must be fitted before prediction")
        return self.model.predict(X)


class XGBoostModel(BaseModel):
    """XGBoost model wrapper"""
    
    def get_framework(self) -> str:
        return "xgboost"
    
    def build(self) -> Any:
        """Build XGBoost model"""
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("XGBoost not installed. Run: pip install xgboost")
        
        model_map = {
            "xgb_classifier": xgb.XGBClassifier,
            "xgb_regressor": xgb.XGBRegressor,
            "xgb_ranker": xgb.XGBRanker,
        }
        
        if self.model_type not in model_map:
            raise ValueError(f"Unknown XGBoost model type: {self.model_type}")
        
        model_class = model_map[self.model_type]
        
        # Set default params for better performance
        default_params = {
            "n_estimators": 100,
            "learning_rate": 0.1,
            "max_depth": 6,
            "objective": "binary:logistic" if "classifier" in self.model_type else "reg:squarederror",
            "n_jobs": -1,
            "random_state": 42
        }
        
        # Merge with user params
        final_params = {**default_params, **self.params}
        
        self.model = model_class(**final_params)
        return self.model
    
    def fit(self, X: pd.DataFrame, y: pd.Series, eval_set=None, **kwargs) -> "XGBoostModel":
        """Train XGBoost model with optional validation"""
        if self.model is None:
            self.build()
        
        with ErrorContext("xgboost_fit", model_type=self.model_type):
            # XGBoost handles eval_set for early stopping
            fit_params = kwargs.copy()
            if eval_set:
                fit_params['eval_set'] = eval_set
                fit_params.setdefault('early_stopping_rounds', 10)
                fit_params.setdefault('verbose', False)
            
            self.model.fit(X, y, **fit_params)
            self.is_fitted = True
            
            # Store feature importance
            self.metadata["feature_importance"] = dict(zip(
                X.columns,
                self.model.feature_importances_.tolist()
            ))
            self.metadata["n_features"] = X.shape[1]
            self.metadata["feature_names"] = list(X.columns)
            
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.is_fitted:
            raise MeridianError("Model must be fitted before prediction")
        return self.model.predict(X)


class LightGBMModel(BaseModel):
    """LightGBM model wrapper"""
    
    def get_framework(self) -> str:
        return "lightgbm"
    
    def build(self) -> Any:
        """Build LightGBM model"""
        try:
            import lightgbm as lgb
        except ImportError:
            raise ImportError("LightGBM not installed. Run: pip install lightgbm")
        
        model_map = {
            "lgb_classifier": lgb.LGBMClassifier,
            "lgb_regressor": lgb.LGBMRegressor,
            "lgb_ranker": lgb.LGBMRanker,
        }
        
        if self.model_type not in model_map:
            raise ValueError(f"Unknown LightGBM model type: {self.model_type}")
        
        model_class = model_map[self.model_type]
        
        # Set default params optimized for performance
        default_params = {
            "n_estimators": 100,
            "learning_rate": 0.1,
            "num_leaves": 31,
            "objective": "binary" if "classifier" in self.model_type else "regression",
            "n_jobs": -1,
            "random_state": 42,
            "verbosity": -1
        }
        
        # Merge with user params
        final_params = {**default_params, **self.params}
        
        self.model = model_class(**final_params)
        return self.model
    
    def fit(self, X: pd.DataFrame, y: pd.Series, categorical_features=None, **kwargs) -> "LightGBMModel":
        """Train LightGBM model with categorical feature support"""
        if self.model is None:
            self.build()
        
        with ErrorContext("lightgbm_fit", model_type=self.model_type):
            # LightGBM can handle categorical features directly
            fit_params = kwargs.copy()
            if categorical_features:
                fit_params['categorical_feature'] = categorical_features
            
            self.model.fit(X, y, **fit_params)
            self.is_fitted = True
            
            # Store feature importance
            self.metadata["feature_importance"] = dict(zip(
                X.columns,
                self.model.feature_importances_.tolist()
            ))
            self.metadata["n_features"] = X.shape[1]
            self.metadata["feature_names"] = list(X.columns)
            
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.is_fitted:
            raise MeridianError("Model must be fitted before prediction")
        return self.model.predict(X)


class PyTorchModel(BaseModel):
    """PyTorch neural network wrapper"""
    
    def get_framework(self) -> str:
        return "pytorch"
    
    def build(self) -> Any:
        """Build PyTorch model"""
        try:
            import torch
            import torch.nn as nn
        except ImportError:
            raise ImportError("PyTorch not installed. Run: pip install torch")
        
        # Define a simple feedforward network
        class SimpleNN(nn.Module):
            def __init__(self, input_size, hidden_sizes, output_size, task_type="classification"):
                super(SimpleNN, self).__init__()
                self.task_type = task_type
                
                layers = []
                prev_size = input_size
                
                for hidden_size in hidden_sizes:
                    layers.append(nn.Linear(prev_size, hidden_size))
                    layers.append(nn.ReLU())
                    layers.append(nn.Dropout(0.2))
                    prev_size = hidden_size
                
                layers.append(nn.Linear(prev_size, output_size))
                
                if task_type == "classification":
                    layers.append(nn.Sigmoid() if output_size == 1 else nn.Softmax(dim=1))
                
                self.model = nn.Sequential(*layers)
            
            def forward(self, x):
                return self.model(x)
        
        # Get params
        input_size = self.params.get("input_size", 10)
        hidden_sizes = self.params.get("hidden_sizes", [128, 64, 32])
        output_size = self.params.get("output_size", 1)
        task_type = self.params.get("task_type", "classification")
        
        self.model = SimpleNN(input_size, hidden_sizes, output_size, task_type)
        self.metadata["architecture"] = {
            "input_size": input_size,
            "hidden_sizes": hidden_sizes,
            "output_size": output_size,
            "task_type": task_type
        }
        
        return self.model
    
    def fit(self, X: pd.DataFrame, y: pd.Series, epochs=100, batch_size=32, **kwargs) -> "PyTorchModel":
        """Train PyTorch model"""
        try:
            import torch
            import torch.nn as nn
            import torch.optim as optim
            from torch.utils.data import DataLoader, TensorDataset
        except ImportError:
            raise ImportError("PyTorch not installed")
        
        if self.model is None:
            # Update input size based on data
            self.params["input_size"] = X.shape[1]
            self.build()
        
        with ErrorContext("pytorch_fit", model_type=self.model_type):
            # Convert to tensors
            X_tensor = torch.FloatTensor(X.values)
            y_tensor = torch.FloatTensor(y.values.reshape(-1, 1))
            
            # Create dataset and dataloader
            dataset = TensorDataset(X_tensor, y_tensor)
            dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
            
            # Setup optimizer and loss
            optimizer = optim.Adam(self.model.parameters(), lr=self.params.get("learning_rate", 0.001))
            
            task_type = self.params.get("task_type", "classification")
            if task_type == "classification":
                criterion = nn.BCELoss() if self.params.get("output_size", 1) == 1 else nn.CrossEntropyLoss()
            else:
                criterion = nn.MSELoss()
            
            # Training loop
            self.model.train()
            for epoch in range(epochs):
                total_loss = 0
                for batch_X, batch_y in dataloader:
                    optimizer.zero_grad()
                    outputs = self.model(batch_X)
                    loss = criterion(outputs, batch_y)
                    loss.backward()
                    optimizer.step()
                    total_loss += loss.item()
                
                if epoch % 10 == 0:
                    logger.debug(f"Epoch {epoch}, Loss: {total_loss/len(dataloader):.4f}")
            
            self.is_fitted = True
            self.metadata["n_epochs"] = epochs
            self.metadata["batch_size"] = batch_size
            self.metadata["n_features"] = X.shape[1]
            self.metadata["feature_names"] = list(X.columns)
            
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.is_fitted:
            raise MeridianError("Model must be fitted before prediction")
        
        try:
            import torch
        except ImportError:
            raise ImportError("PyTorch not installed")
        
        self.model.eval()
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X.values)
            outputs = self.model(X_tensor)
            
            task_type = self.params.get("task_type", "classification")
            if task_type == "classification":
                # Convert probabilities to class predictions
                if outputs.shape[1] == 1:
                    predictions = (outputs.numpy() > 0.5).astype(int).flatten()
                else:
                    predictions = outputs.numpy().argmax(axis=1)
            else:
                predictions = outputs.numpy().flatten()
        
        return predictions


class ModelFactory:
    """Factory for creating and managing ML models"""
    
    # Framework mappings
    FRAMEWORK_MAP = {
        "sklearn": SklearnModel,
        "xgboost": XGBoostModel,
        "lightgbm": LightGBMModel,
        "pytorch": PyTorchModel,
    }
    
    # Model type to framework mapping
    MODEL_FRAMEWORK_MAP = {
        # Sklearn models
        "logistic_regression": "sklearn",
        "random_forest_classifier": "sklearn",
        "random_forest_regressor": "sklearn",
        "gradient_boosting_classifier": "sklearn",
        "gradient_boosting_regressor": "sklearn",
        "svc": "sklearn",
        "svr": "sklearn",
        "ridge": "sklearn",
        "lasso": "sklearn",
        "elastic_net": "sklearn",
        
        # XGBoost models
        "xgb_classifier": "xgboost",
        "xgb_regressor": "xgboost",
        
        # LightGBM models
        "lgb_classifier": "lightgbm",
        "lgb_regressor": "lightgbm",
        
        # PyTorch models
        "neural_network": "pytorch",
        "deep_neural_network": "pytorch",
    }
    
    @classmethod
    def create_model(cls, model_type: str, params: Optional[Dict[str, Any]] = None) -> BaseModel:
        """
        Create a model instance.
        
        Args:
            model_type: Type of model to create
            params: Model parameters
            
        Returns:
            Model instance
        """
        if model_type not in cls.MODEL_FRAMEWORK_MAP:
            raise ValueError(f"Unknown model type: {model_type}. Available: {list(cls.MODEL_FRAMEWORK_MAP.keys())}")
        
        framework = cls.MODEL_FRAMEWORK_MAP[model_type]
        model_class = cls.FRAMEWORK_MAP[framework]
        
        logger.info(f"Creating {model_type} model with {framework} framework")
        return model_class(model_type, params)
    
    @classmethod
    def list_available_models(cls) -> Dict[str, List[str]]:
        """List all available models grouped by framework"""
        models_by_framework = {}
        
        for model_type, framework in cls.MODEL_FRAMEWORK_MAP.items():
            if framework not in models_by_framework:
                models_by_framework[framework] = []
            models_by_framework[framework].append(model_type)
        
        return models_by_framework
    
    @classmethod
    def get_best_model_for_task(
        cls,
        task_type: str,
        data_size: int,
        n_features: int,
        prefer_interpretable: bool = False
    ) -> str:
        """
        Recommend best model for a given task.
        
        Args:
            task_type: "classification" or "regression"
            data_size: Number of samples
            n_features: Number of features
            prefer_interpretable: Prefer interpretable models
            
        Returns:
            Recommended model type
        """
        if task_type == "classification":
            if prefer_interpretable:
                return "logistic_regression" if data_size < 10000 else "decision_tree_classifier"
            elif data_size < 1000:
                return "random_forest_classifier"
            elif data_size < 10000:
                return "xgb_classifier"
            elif data_size < 100000:
                return "lgb_classifier"
            else:
                return "neural_network"
        
        elif task_type == "regression":
            if prefer_interpretable:
                return "ridge" if n_features > 10 else "lasso"
            elif data_size < 1000:
                return "random_forest_regressor"
            elif data_size < 10000:
                return "xgb_regressor"
            elif data_size < 100000:
                return "lgb_regressor"
            else:
                return "neural_network"
        
        else:
            raise ValueError(f"Unknown task type: {task_type}")


# Convenience functions
def create_model(model_type: str, **params) -> BaseModel:
    """Create a model with the factory"""
    return ModelFactory.create_model(model_type, params)


def train_model(
    model_type: str,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: Optional[pd.DataFrame] = None,
    y_val: Optional[pd.Series] = None,
    **params
) -> BaseModel:
    """Train a model with optional validation"""
    model = create_model(model_type, **params)
    
    # Prepare validation set if provided
    eval_set = None
    if X_val is not None and y_val is not None:
        if model.get_framework() in ["xgboost", "lightgbm"]:
            eval_set = [(X_val, y_val)]
    
    # Train model
    model.fit(X_train, y_train, eval_set=eval_set)
    
    return model