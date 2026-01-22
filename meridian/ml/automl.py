"""AutoML Module for MERIDIAN - Hyperparameter Tuning with Optuna"""

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score, 
    mean_squared_error, mean_absolute_error, r2_score
)

try:
    import optuna
    from optuna import Trial
    from optuna.samplers import TPESampler
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    # Create dummy Trial class to avoid NameError
    class Trial:
        pass
    logging.warning("Optuna not installed. Install with: pip install optuna")

logger = logging.getLogger(__name__)


@dataclass 
class AutoMLResult:
    """Results from AutoML optimization"""
    
    best_params: Dict[str, Any]
    best_score: float
    best_model: Any
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    feature_importance: Optional[Dict[str, float]] = None
    cross_val_scores: Optional[List[float]] = None
    test_score: Optional[float] = None
    training_time: float = 0.0
    n_trials: int = 0
    algorithm: str = ""
    metric: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "algorithm": self.algorithm,
            "metric": self.metric,
            "n_trials": self.n_trials,
            "training_time": self.training_time,
            "cross_val_scores": self.cross_val_scores,
            "test_score": self.test_score,
            "feature_importance": self.feature_importance,
            "optimization_history": self.optimization_history
        }
    
    def save(self, path: Path):
        """Save results and model"""
        path.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(path / "automl_results.json", "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        
        # Save model
        with open(path / "best_model.pkl", "wb") as f:
            pickle.dump(self.best_model, f)
        
        logger.info(f"AutoML results saved to {path}")


class AutoMLTuner:
    """Automated hyperparameter tuning with Optuna"""
    
    ALGORITHMS = {
        # Classification
        "logistic": "LogisticRegression",
        "random_forest_classifier": "RandomForestClassifier", 
        "xgboost_classifier": "XGBClassifier",
        "lightgbm_classifier": "LGBMClassifier",
        "svm_classifier": "SVC",
        "neural_net_classifier": "MLPClassifier",
        
        # Regression
        "linear": "LinearRegression",
        "random_forest_regressor": "RandomForestRegressor",
        "xgboost_regressor": "XGBRegressor", 
        "lightgbm_regressor": "LGBMRegressor",
        "svm_regressor": "SVR",
        "neural_net_regressor": "MLPRegressor"
    }
    
    def __init__(self, 
                 task_type: str = "classification",
                 metric: Optional[str] = None,
                 n_trials: int = 100,
                 cv_folds: int = 5,
                 random_state: int = 42):
        """
        Initialize AutoML tuner
        
        Args:
            task_type: 'classification' or 'regression'
            metric: Metric to optimize (default: accuracy for classification, r2 for regression)
            n_trials: Number of Optuna trials
            cv_folds: Number of cross-validation folds
            random_state: Random seed
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError("Optuna is required for AutoML. Install with: pip install optuna")
        
        self.task_type = task_type
        self.metric = metric or ("accuracy" if task_type == "classification" else "r2")
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.random_state = random_state
        
        # Set up cross-validation
        if task_type == "classification":
            self.cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
        else:
            self.cv = KFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    
    def optimize(self,
                X_train: Union[pd.DataFrame, np.ndarray],
                y_train: Union[pd.Series, np.ndarray],
                algorithm: str = "auto",
                X_test: Optional[Union[pd.DataFrame, np.ndarray]] = None,
                y_test: Optional[Union[pd.Series, np.ndarray]] = None) -> AutoMLResult:
        """
        Run hyperparameter optimization
        
        Args:
            X_train: Training features
            y_train: Training target
            algorithm: Algorithm to use ('auto', 'logistic', 'random_forest', etc.)
            X_test: Optional test features
            y_test: Optional test target
            
        Returns:
            AutoMLResult with best model and parameters
        """
        import time
        start_time = time.time()
        
        # Convert to numpy if needed
        if isinstance(X_train, pd.DataFrame):
            X_train = X_train.values
        if isinstance(y_train, pd.Series):
            y_train = y_train.values
        
        # Select algorithm
        if algorithm == "auto":
            algorithm = self._select_best_algorithm(X_train, y_train)
        
        logger.info(f"Starting AutoML optimization with {algorithm} for {self.n_trials} trials")
        
        # Create objective function
        objective = self._create_objective(algorithm, X_train, y_train)
        
        # Run optimization
        study = optuna.create_study(
            direction="maximize" if self.metric in ["accuracy", "f1", "r2"] else "minimize",
            sampler=TPESampler(seed=self.random_state)
        )
        
        # Add callback to track progress
        optimization_history = []
        def callback(study, trial):
            optimization_history.append({
                "trial": trial.number,
                "value": trial.value,
                "params": trial.params,
                "datetime": datetime.now().isoformat()
            })
        
        study.optimize(objective, n_trials=self.n_trials, callbacks=[callback])
        
        # Get best model
        best_params = study.best_params
        best_model = self._train_final_model(algorithm, best_params, X_train, y_train)
        
        # Calculate cross-validation scores
        cv_scores = cross_val_score(
            best_model, X_train, y_train, 
            cv=self.cv, 
            scoring=self._get_sklearn_scorer()
        )
        
        # Test score if test set provided
        test_score = None
        if X_test is not None and y_test is not None:
            if isinstance(X_test, pd.DataFrame):
                X_test = X_test.values
            if isinstance(y_test, pd.Series):
                y_test = y_test.values
            
            y_pred = best_model.predict(X_test)
            test_score = self._calculate_metric(y_test, y_pred)
        
        # Feature importance
        feature_importance = self._get_feature_importance(best_model, X_train.shape[1])
        
        # Create result
        result = AutoMLResult(
            best_params=best_params,
            best_score=study.best_value,
            best_model=best_model,
            optimization_history=optimization_history,
            feature_importance=feature_importance,
            cross_val_scores=cv_scores.tolist(),
            test_score=test_score,
            training_time=time.time() - start_time,
            n_trials=self.n_trials,
            algorithm=algorithm,
            metric=self.metric
        )
        
        logger.info(f"Optimization complete. Best {self.metric}: {study.best_value:.4f}")
        
        return result
    
    def _select_best_algorithm(self, X: np.ndarray, y: np.ndarray) -> str:
        """Auto-select best algorithm based on quick evaluation"""
        n_samples, n_features = X.shape
        
        # Heuristics for algorithm selection
        if self.task_type == "classification":
            if n_samples < 1000:
                return "random_forest_classifier"
            elif n_features > 100:
                return "lightgbm_classifier"
            else:
                return "xgboost_classifier"
        else:
            if n_samples < 1000:
                return "random_forest_regressor"
            elif n_features > 100:
                return "lightgbm_regressor"
            else:
                return "xgboost_regressor"
    
    def _create_objective(self, algorithm: str, X: np.ndarray, y: np.ndarray) -> Callable:
        """Create Optuna objective function for the algorithm"""
        
        def objective(trial: Trial) -> float:
            # Get hyperparameters for algorithm
            params = self._suggest_hyperparams(trial, algorithm)
            
            # Create model
            model = self._create_model(algorithm, params)
            
            # Cross-validation
            try:
                scores = cross_val_score(
                    model, X, y,
                    cv=self.cv,
                    scoring=self._get_sklearn_scorer(),
                    n_jobs=-1
                )
                return scores.mean()
            except Exception as e:
                logger.warning(f"Trial failed: {e}")
                return float('-inf') if self.metric in ["accuracy", "f1", "r2"] else float('inf')
        
        return objective
    
    def _suggest_hyperparams(self, trial: Trial, algorithm: str) -> Dict[str, Any]:
        """Suggest hyperparameters for the algorithm"""
        
        if algorithm == "logistic":
            return {
                'C': trial.suggest_float('C', 1e-3, 100, log=True),
                'penalty': trial.suggest_categorical('penalty', ['l1', 'l2']),
                'solver': 'liblinear',
                'random_state': self.random_state,
                'max_iter': 1000
            }
        
        elif algorithm in ["random_forest_classifier", "random_forest_regressor"]:
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                'max_depth': trial.suggest_int('max_depth', 3, 20),
                'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
                'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
                'random_state': self.random_state,
                'n_jobs': -1
            }
        
        elif algorithm in ["xgboost_classifier", "xgboost_regressor"]:
            use_gpu = False  # Set to True if GPU available
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 1.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 1.0, log=True),
                'random_state': self.random_state,
                'n_jobs': -1,
                'verbosity': 0
            }
            if use_gpu:
                params['tree_method'] = 'gpu_hist'
                params['gpu_id'] = 0
            return params
        
        elif algorithm in ["lightgbm_classifier", "lightgbm_regressor"]:
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 300),
                'max_depth': trial.suggest_int('max_depth', 3, 15),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 20, 300),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
                'random_state': self.random_state,
                'n_jobs': -1,
                'verbosity': -1
            }
        
        elif algorithm in ["svm_classifier", "svm_regressor"]:
            return {
                'C': trial.suggest_float('C', 1e-3, 100, log=True),
                'kernel': trial.suggest_categorical('kernel', ['rbf', 'poly', 'sigmoid']),
                'gamma': trial.suggest_categorical('gamma', ['scale', 'auto']),
                'random_state': self.random_state
            }
        
        elif algorithm in ["neural_net_classifier", "neural_net_regressor"]:
            n_layers = trial.suggest_int('n_layers', 1, 3)
            layers = []
            for i in range(n_layers):
                layers.append(trial.suggest_int(f'n_units_l{i}', 10, 200))
            
            return {
                'hidden_layer_sizes': tuple(layers),
                'activation': trial.suggest_categorical('activation', ['relu', 'tanh']),
                'solver': trial.suggest_categorical('solver', ['adam', 'sgd']),
                'alpha': trial.suggest_float('alpha', 1e-5, 1e-1, log=True),
                'learning_rate_init': trial.suggest_float('learning_rate_init', 1e-4, 1e-1, log=True),
                'max_iter': 1000,
                'random_state': self.random_state,
                'early_stopping': True,
                'validation_fraction': 0.1
            }
        
        else:
            return {'random_state': self.random_state}
    
    def _create_model(self, algorithm: str, params: Dict[str, Any]):
        """Create model instance with parameters"""
        
        if algorithm == "logistic":
            from sklearn.linear_model import LogisticRegression
            return LogisticRegression(**params)
        
        elif algorithm == "linear":
            from sklearn.linear_model import LinearRegression
            return LinearRegression()
        
        elif algorithm == "random_forest_classifier":
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(**params)
        
        elif algorithm == "random_forest_regressor":
            from sklearn.ensemble import RandomForestRegressor
            return RandomForestRegressor(**params)
        
        elif algorithm in ["xgboost_classifier", "xgboost_regressor"]:
            try:
                import xgboost as xgb
                if algorithm == "xgboost_classifier":
                    return xgb.XGBClassifier(**params)
                else:
                    return xgb.XGBRegressor(**params)
            except ImportError:
                logger.warning("XGBoost not installed, falling back to RandomForest")
                if algorithm == "xgboost_classifier":
                    from sklearn.ensemble import RandomForestClassifier
                    return RandomForestClassifier(random_state=self.random_state)
                else:
                    from sklearn.ensemble import RandomForestRegressor
                    return RandomForestRegressor(random_state=self.random_state)
        
        elif algorithm in ["lightgbm_classifier", "lightgbm_regressor"]:
            try:
                import lightgbm as lgb
                if algorithm == "lightgbm_classifier":
                    return lgb.LGBMClassifier(**params)
                else:
                    return lgb.LGBMRegressor(**params)
            except ImportError:
                logger.warning("LightGBM not installed, falling back to RandomForest")
                if algorithm == "lightgbm_classifier":
                    from sklearn.ensemble import RandomForestClassifier
                    return RandomForestClassifier(random_state=self.random_state)
                else:
                    from sklearn.ensemble import RandomForestRegressor
                    return RandomForestRegressor(random_state=self.random_state)
        
        elif algorithm == "svm_classifier":
            from sklearn.svm import SVC
            return SVC(**params)
        
        elif algorithm == "svm_regressor":
            from sklearn.svm import SVR
            return SVR(**params)
        
        elif algorithm == "neural_net_classifier":
            from sklearn.neural_network import MLPClassifier
            return MLPClassifier(**params)
        
        elif algorithm == "neural_net_regressor":
            from sklearn.neural_network import MLPRegressor
            return MLPRegressor(**params)
        
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
    
    def _train_final_model(self, algorithm: str, params: Dict[str, Any], X: np.ndarray, y: np.ndarray):
        """Train final model with best parameters"""
        model = self._create_model(algorithm, params)
        model.fit(X, y)
        return model
    
    def _get_sklearn_scorer(self) -> str:
        """Get sklearn scoring function name"""
        scorer_map = {
            'accuracy': 'accuracy',
            'f1': 'f1_weighted',
            'precision': 'precision_weighted',
            'recall': 'recall_weighted',
            'r2': 'r2',
            'mse': 'neg_mean_squared_error',
            'mae': 'neg_mean_absolute_error'
        }
        return scorer_map.get(self.metric, 'accuracy')
    
    def _calculate_metric(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate metric value"""
        if self.metric == 'accuracy':
            return accuracy_score(y_true, y_pred)
        elif self.metric == 'f1':
            return f1_score(y_true, y_pred, average='weighted')
        elif self.metric == 'precision':
            return precision_score(y_true, y_pred, average='weighted')
        elif self.metric == 'recall':
            return recall_score(y_true, y_pred, average='weighted')
        elif self.metric == 'r2':
            return r2_score(y_true, y_pred)
        elif self.metric == 'mse':
            return mean_squared_error(y_true, y_pred)
        elif self.metric == 'mae':
            return mean_absolute_error(y_true, y_pred)
        else:
            return 0.0
    
    def _get_feature_importance(self, model, n_features: int) -> Optional[Dict[str, float]]:
        """Extract feature importance from model"""
        try:
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
            elif hasattr(model, 'coef_'):
                importances = np.abs(model.coef_).mean(axis=0) if model.coef_.ndim > 1 else np.abs(model.coef_)
            else:
                return None
            
            # Create feature names if not available
            feature_names = [f"feature_{i}" for i in range(n_features)]
            
            # Sort by importance
            importance_dict = dict(zip(feature_names, importances))
            return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
        
        except Exception as e:
            logger.warning(f"Could not extract feature importance: {e}")
            return None


class AutoMLPipeline:
    """Complete AutoML pipeline with preprocessing"""
    
    def __init__(self, task_type: str = "auto"):
        """
        Initialize AutoML pipeline
        
        Args:
            task_type: 'classification', 'regression', or 'auto'
        """
        self.task_type = task_type
        self.preprocessor = None
        self.tuner = None
        self.result = None
    
    def fit(self,
           X: pd.DataFrame,
           y: pd.Series,
           preprocess: bool = True,
           algorithm: str = "auto",
           n_trials: int = 100,
           test_size: float = 0.2) -> AutoMLResult:
        """
        Complete AutoML pipeline
        
        Args:
            X: Features DataFrame
            y: Target Series
            preprocess: Whether to apply automatic preprocessing
            algorithm: Algorithm to use
            n_trials: Number of optimization trials
            test_size: Proportion for test set
            
        Returns:
            AutoMLResult with optimized model
        """
        from sklearn.model_selection import train_test_split
        
        # Auto-detect task type if needed
        if self.task_type == "auto":
            self.task_type = "classification" if y.nunique() <= 20 else "regression"
            logger.info(f"Auto-detected task type: {self.task_type}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42,
            stratify=y if self.task_type == "classification" else None
        )
        
        # Preprocess if requested
        if preprocess:
            from meridian.data.quality import DataPreprocessor
            self.preprocessor = DataPreprocessor()
            
            # Clean training data
            X_train_clean = self.preprocessor.auto_clean(
                X_train,
                handle_missing="smart",
                handle_outliers="clip",
                scale_numeric="standard"
            )
            
            # Apply same preprocessing to test
            X_test_clean = self.preprocessor.auto_clean(
                X_test,
                handle_missing="smart",
                handle_outliers="clip",
                scale_numeric="standard"
            )
        else:
            X_train_clean = X_train
            X_test_clean = X_test
        
        # Run AutoML optimization
        self.tuner = AutoMLTuner(
            task_type=self.task_type,
            n_trials=n_trials
        )
        
        self.result = self.tuner.optimize(
            X_train_clean, y_train,
            algorithm=algorithm,
            X_test=X_test_clean,
            y_test=y_test
        )
        
        return self.result
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions with optimized model"""
        if not self.result:
            raise ValueError("Model not trained. Call fit() first.")
        
        # Preprocess if we have a preprocessor
        if self.preprocessor:
            X_clean = self.preprocessor.auto_clean(
                X,
                handle_missing="smart",
                handle_outliers="clip",
                scale_numeric="standard"
            )
        else:
            X_clean = X
        
        return self.result.best_model.predict(X_clean)