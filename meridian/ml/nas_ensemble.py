"""Neural Architecture Search and Ensemble Creation Module for MERIDIAN

Provides:
- Neural Architecture Search (NAS) for optimal network design
- Automated ensemble creation (voting, stacking, blending)
- Model combination strategies
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, KFold, StratifiedKFold
from sklearn.metrics import accuracy_score, r2_score
from sklearn.ensemble import VotingClassifier, VotingRegressor, StackingClassifier, StackingRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.linear_model import LogisticRegression, LinearRegression

logger = logging.getLogger(__name__)


@dataclass
class NASResult:
    """Results from Neural Architecture Search"""
    
    best_architecture: Dict[str, Any]
    best_score: float
    search_history: List[Dict[str, Any]]
    best_model: Any
    n_parameters: int
    training_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "best_architecture": self.best_architecture,
            "best_score": self.best_score,
            "n_parameters": self.n_parameters,
            "training_time": self.training_time,
            "search_iterations": len(self.search_history)
        }


@dataclass
class EnsembleResult:
    """Results from ensemble creation"""
    
    ensemble_type: str
    base_models: List[str]
    ensemble_score: float
    individual_scores: Dict[str, float]
    ensemble_model: Any
    weights: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "ensemble_type": self.ensemble_type,
            "base_models": self.base_models,
            "ensemble_score": self.ensemble_score,
            "individual_scores": self.individual_scores,
            "weights": self.weights,
            "improvement": self.ensemble_score - max(self.individual_scores.values())
        }


class NeuralArchitectureSearch:
    """Neural Architecture Search for optimal network design"""
    
    def __init__(self,
                 task_type: str = "classification",
                 max_layers: int = 5,
                 max_neurons: int = 512,
                 search_iterations: int = 50):
        """
        Initialize NAS
        
        Args:
            task_type: 'classification' or 'regression'
            max_layers: Maximum number of hidden layers
            max_neurons: Maximum neurons per layer
            search_iterations: Number of architectures to try
        """
        self.task_type = task_type
        self.max_layers = max_layers
        self.max_neurons = max_neurons
        self.search_iterations = search_iterations
        
        # Define search space
        self.activation_functions = ['relu', 'tanh', 'logistic']
        self.solvers = ['adam', 'sgd', 'lbfgs']
        self.learning_rates = ['constant', 'invscaling', 'adaptive']
    
    def search(self, 
              X_train: np.ndarray,
              y_train: np.ndarray,
              X_val: Optional[np.ndarray] = None,
              y_val: Optional[np.ndarray] = None) -> NASResult:
        """
        Perform neural architecture search
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            
        Returns:
            NASResult with best architecture
        """
        import time
        import random
        
        start_time = time.time()
        search_history = []
        best_score = -np.inf
        best_architecture = None
        best_model = None
        
        # Use cross-validation if no validation set
        if X_val is None or y_val is None:
            use_cv = True
            if self.task_type == "classification":
                cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
            else:
                cv = KFold(n_splits=3, shuffle=True, random_state=42)
        else:
            use_cv = False
        
        for iteration in range(self.search_iterations):
            # Sample architecture
            architecture = self._sample_architecture()
            
            try:
                # Create model
                model = self._create_model(architecture)
                
                # Evaluate
                if use_cv:
                    scores = cross_val_score(
                        model, X_train, y_train, cv=cv,
                        scoring='accuracy' if self.task_type == 'classification' else 'r2'
                    )
                    score = scores.mean()
                else:
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_val)
                    if self.task_type == "classification":
                        score = accuracy_score(y_val, y_pred)
                    else:
                        score = r2_score(y_val, y_pred)
                
                # Record result
                search_history.append({
                    "iteration": iteration,
                    "architecture": architecture,
                    "score": score
                })
                
                # Update best
                if score > best_score:
                    best_score = score
                    best_architecture = architecture
                    best_model = model
                    
                    logger.info(f"NAS iteration {iteration}: New best score {score:.4f}")
                
            except Exception as e:
                logger.warning(f"NAS iteration {iteration} failed: {e}")
                continue
        
        # Train final model with best architecture on full data
        if best_architecture:
            best_model = self._create_model(best_architecture)
            best_model.fit(X_train, y_train)
            
            # Calculate number of parameters
            n_parameters = self._count_parameters(best_architecture)
        else:
            n_parameters = 0
        
        training_time = time.time() - start_time
        
        return NASResult(
            best_architecture=best_architecture,
            best_score=best_score,
            search_history=search_history,
            best_model=best_model,
            n_parameters=n_parameters,
            training_time=training_time
        )
    
    def _sample_architecture(self) -> Dict[str, Any]:
        """Sample a random architecture from search space"""
        import random
        
        # Sample number of layers
        n_layers = random.randint(1, self.max_layers)
        
        # Sample layer sizes (decreasing trend)
        layers = []
        prev_size = self.max_neurons
        for i in range(n_layers):
            # Ensure decreasing or stable size
            max_size = min(prev_size, self.max_neurons // (i + 1))
            layer_size = random.randint(10, max_size)
            layers.append(layer_size)
            prev_size = layer_size
        
        # Sample hyperparameters
        architecture = {
            "hidden_layer_sizes": tuple(layers),
            "activation": random.choice(self.activation_functions),
            "solver": random.choice(self.solvers),
            "learning_rate": random.choice(self.learning_rates),
            "alpha": 10 ** random.uniform(-5, -1),  # L2 penalty
            "learning_rate_init": 10 ** random.uniform(-4, -1),
            "max_iter": random.choice([200, 500, 1000]),
            "early_stopping": True,
            "validation_fraction": 0.1,
            "n_iter_no_change": 20,
            "random_state": 42
        }
        
        # Adjust for solver constraints
        if architecture["solver"] == "lbfgs":
            architecture["learning_rate"] = "constant"
            architecture["max_iter"] = 200  # LBFGS converges faster
        
        return architecture
    
    def _create_model(self, architecture: Dict[str, Any]):
        """Create neural network model from architecture"""
        if self.task_type == "classification":
            return MLPClassifier(**architecture)
        else:
            return MLPRegressor(**architecture)
    
    def _count_parameters(self, architecture: Dict[str, Any]) -> int:
        """Count number of parameters in architecture"""
        layers = architecture["hidden_layer_sizes"]
        n_params = 0
        
        # Simplified calculation (actual depends on input/output dims)
        prev_size = 10  # Assume 10 input features
        for layer_size in layers:
            n_params += prev_size * layer_size + layer_size  # weights + bias
            prev_size = layer_size
        
        # Output layer
        n_params += prev_size * 1 + 1  # Assume 1 output
        
        return n_params


class AutoEnsemble:
    """Automated ensemble creation with multiple strategies"""
    
    def __init__(self,
                 task_type: str = "classification",
                 ensemble_size: int = 5,
                 ensemble_strategy: str = "auto"):
        """
        Initialize auto ensemble
        
        Args:
            task_type: 'classification' or 'regression'
            ensemble_size: Number of base models
            ensemble_strategy: 'voting', 'stacking', 'blending', 'auto'
        """
        self.task_type = task_type
        self.ensemble_size = ensemble_size
        self.ensemble_strategy = ensemble_strategy
    
    def create_ensemble(self,
                       X_train: np.ndarray,
                       y_train: np.ndarray,
                       X_val: Optional[np.ndarray] = None,
                       y_val: Optional[np.ndarray] = None,
                       base_models: Optional[List] = None) -> EnsembleResult:
        """
        Create optimized ensemble
        
        Args:
            X_train: Training features
            y_train: Training target
            X_val: Validation features
            y_val: Validation target
            base_models: Optional list of pre-trained models
            
        Returns:
            EnsembleResult with ensemble model
        """
        # Create or use provided base models
        if base_models is None:
            base_models, model_names = self._create_diverse_models()
        else:
            model_names = [f"model_{i}" for i in range(len(base_models))]
        
        # Train base models and evaluate
        trained_models = []
        individual_scores = {}
        
        for model, name in zip(base_models, model_names):
            # Clone model to avoid modifying original
            import copy
            model_copy = copy.deepcopy(model)
            
            # Train
            model_copy.fit(X_train, y_train)
            trained_models.append((name, model_copy))
            
            # Evaluate
            if X_val is not None and y_val is not None:
                y_pred = model_copy.predict(X_val)
                if self.task_type == "classification":
                    score = accuracy_score(y_val, y_pred)
                else:
                    score = r2_score(y_val, y_pred)
            else:
                # Use cross-validation
                if self.task_type == "classification":
                    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
                    scores = cross_val_score(model_copy, X_train, y_train, cv=cv, scoring='accuracy')
                else:
                    cv = KFold(n_splits=3, shuffle=True, random_state=42)
                    scores = cross_val_score(model_copy, X_train, y_train, cv=cv, scoring='r2')
                score = scores.mean()
            
            individual_scores[name] = score
        
        # Select ensemble strategy
        if self.ensemble_strategy == "auto":
            # Choose based on performance variance
            score_std = np.std(list(individual_scores.values()))
            if score_std > 0.05:
                strategy = "stacking"  # High variance, use meta-learner
            else:
                strategy = "voting"  # Similar performance, simple voting
        else:
            strategy = self.ensemble_strategy
        
        # Create ensemble
        if strategy == "voting":
            ensemble_model, weights = self._create_voting_ensemble(
                trained_models, X_train, y_train, X_val, y_val
            )
        elif strategy == "stacking":
            ensemble_model, weights = self._create_stacking_ensemble(
                trained_models, X_train, y_train
            )
        elif strategy == "blending":
            ensemble_model, weights = self._create_blending_ensemble(
                trained_models, X_train, y_train, X_val, y_val
            )
        else:
            raise ValueError(f"Unknown ensemble strategy: {strategy}")
        
        # Evaluate ensemble
        if X_val is not None and y_val is not None:
            ensemble_model.fit(X_train, y_train)
            y_pred = ensemble_model.predict(X_val)
            if self.task_type == "classification":
                ensemble_score = accuracy_score(y_val, y_pred)
            else:
                ensemble_score = r2_score(y_val, y_pred)
        else:
            # Cross-validation
            if self.task_type == "classification":
                cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
                scores = cross_val_score(ensemble_model, X_train, y_train, cv=cv, scoring='accuracy')
            else:
                cv = KFold(n_splits=3, shuffle=True, random_state=42)
                scores = cross_val_score(ensemble_model, X_train, y_train, cv=cv, scoring='r2')
            ensemble_score = scores.mean()
        
        return EnsembleResult(
            ensemble_type=strategy,
            base_models=model_names,
            ensemble_score=ensemble_score,
            individual_scores=individual_scores,
            ensemble_model=ensemble_model,
            weights=weights
        )
    
    def _create_diverse_models(self) -> Tuple[List, List[str]]:
        """Create diverse set of base models"""
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
        from sklearn.svm import SVC, SVR
        from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
        from sklearn.linear_model import LogisticRegression, Ridge
        
        if self.task_type == "classification":
            models = [
                RandomForestClassifier(n_estimators=100, random_state=42),
                GradientBoostingClassifier(n_estimators=100, random_state=42),
                SVC(probability=True, random_state=42),
                KNeighborsClassifier(n_neighbors=5),
                LogisticRegression(random_state=42, max_iter=1000)
            ]
            names = ["rf", "gb", "svm", "knn", "lr"]
        else:
            models = [
                RandomForestRegressor(n_estimators=100, random_state=42),
                GradientBoostingRegressor(n_estimators=100, random_state=42),
                SVR(),
                KNeighborsRegressor(n_neighbors=5),
                Ridge(random_state=42)
            ]
            names = ["rf", "gb", "svm", "knn", "ridge"]
        
        # Limit to ensemble_size
        models = models[:self.ensemble_size]
        names = names[:self.ensemble_size]
        
        return models, names
    
    def _create_voting_ensemble(self, models: List[Tuple[str, Any]], 
                               X_train: np.ndarray, y_train: np.ndarray,
                               X_val: Optional[np.ndarray], y_val: Optional[np.ndarray]) -> Tuple[Any, List[float]]:
        """Create voting ensemble"""
        if self.task_type == "classification":
            # Try soft voting if all models support predict_proba
            try:
                ensemble = VotingClassifier(estimators=models, voting='soft')
            except:
                ensemble = VotingClassifier(estimators=models, voting='hard')
        else:
            ensemble = VotingRegressor(estimators=models)
        
        # Optimize weights if validation set available
        weights = None
        if X_val is not None and y_val is not None:
            weights = self._optimize_weights(models, X_train, y_train, X_val, y_val)
            if self.task_type == "classification":
                ensemble = VotingClassifier(estimators=models, voting='soft', weights=weights)
            else:
                ensemble = VotingRegressor(estimators=models, weights=weights)
        
        return ensemble, weights
    
    def _create_stacking_ensemble(self, models: List[Tuple[str, Any]],
                                 X_train: np.ndarray, y_train: np.ndarray) -> Tuple[Any, None]:
        """Create stacking ensemble with meta-learner"""
        if self.task_type == "classification":
            meta_learner = LogisticRegression(random_state=42, max_iter=1000)
            ensemble = StackingClassifier(
                estimators=models,
                final_estimator=meta_learner,
                cv=3  # Use cross-validation for training meta-learner
            )
        else:
            meta_learner = LinearRegression()
            ensemble = StackingRegressor(
                estimators=models,
                final_estimator=meta_learner,
                cv=3
            )
        
        return ensemble, None
    
    def _create_blending_ensemble(self, models: List[Tuple[str, Any]],
                                 X_train: np.ndarray, y_train: np.ndarray,
                                 X_val: Optional[np.ndarray], y_val: Optional[np.ndarray]) -> Tuple[Any, List[float]]:
        """Create blending ensemble (similar to voting with optimized weights)"""
        # For simplicity, use voting with optimized weights
        return self._create_voting_ensemble(models, X_train, y_train, X_val, y_val)
    
    def _optimize_weights(self, models: List[Tuple[str, Any]],
                         X_train: np.ndarray, y_train: np.ndarray,
                         X_val: np.ndarray, y_val: np.ndarray) -> List[float]:
        """Optimize ensemble weights using validation set"""
        from scipy.optimize import minimize
        
        # Get predictions from each model
        predictions = []
        for name, model in models:
            if hasattr(model, 'predict_proba') and self.task_type == "classification":
                pred = model.predict_proba(X_val)[:, 1]  # Use probability for class 1
            else:
                pred = model.predict(X_val)
            predictions.append(pred)
        
        predictions = np.array(predictions).T
        
        # Objective function
        def ensemble_score(weights):
            weighted_pred = np.dot(predictions, weights)
            if self.task_type == "classification":
                # Convert to binary predictions
                weighted_pred_binary = (weighted_pred > 0.5).astype(int)
                return -accuracy_score(y_val, weighted_pred_binary)
            else:
                return -r2_score(y_val, weighted_pred)
        
        # Constraints: weights sum to 1, all non-negative
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0, 1) for _ in range(len(models))]
        
        # Initial guess: equal weights
        initial_weights = np.ones(len(models)) / len(models)
        
        # Optimize
        result = minimize(
            ensemble_score,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            return result.x.tolist()
        else:
            # Fall back to equal weights
            return initial_weights.tolist()


class CompleteAutoML:
    """Complete AutoML pipeline with all features"""
    
    def __init__(self, task_type: str = "auto"):
        """
        Initialize complete AutoML
        
        Args:
            task_type: 'classification', 'regression', or 'auto'
        """
        self.task_type = task_type
    
    def fit_predict(self,
                   X_train: pd.DataFrame,
                   y_train: pd.Series,
                   X_test: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Complete AutoML pipeline
        
        Args:
            X_train: Training features
            y_train: Training target
            X_test: Test features for prediction
            
        Returns:
            Dictionary with results and predictions
        """
        from meridian.ml.feature_engineering import AutoFeatureEngineer
        from meridian.ml.automl import AutoMLTuner
        from sklearn.model_selection import train_test_split
        
        # Auto-detect task type
        if self.task_type == "auto":
            self.task_type = "classification" if y_train.nunique() <= 20 else "regression"
        
        # Split validation set
        X_tr, X_val, y_tr, y_val = train_test_split(
            X_train, y_train, test_size=0.2, random_state=42,
            stratify=y_train if self.task_type == "classification" else None
        )
        
        results = {}
        
        # 1. Feature Engineering
        logger.info("Starting feature engineering...")
        fe = AutoFeatureEngineer(task_type=self.task_type)
        X_tr_eng, fe_result = fe.engineer_features(X_tr, y_tr)
        X_val_eng, _ = fe.engineer_features(X_val)
        results["feature_engineering"] = fe_result.to_dict()
        
        # 2. Neural Architecture Search
        logger.info("Starting neural architecture search...")
        nas = NeuralArchitectureSearch(task_type=self.task_type, search_iterations=20)
        nas_result = nas.search(X_tr_eng.values, y_tr.values, X_val_eng.values, y_val.values)
        results["nas"] = nas_result.to_dict()
        
        # 3. Traditional AutoML with Optuna
        logger.info("Optimizing traditional models...")
        automl = AutoMLTuner(task_type=self.task_type, n_trials=30)
        automl_result = automl.optimize(X_tr_eng, y_tr, X_test=X_val_eng, y_test=y_val)
        results["automl"] = automl_result.to_dict()
        
        # 4. Ensemble Creation
        logger.info("Creating ensemble...")
        ensemble = AutoEnsemble(task_type=self.task_type)
        
        # Use best models from NAS and AutoML
        base_models = [nas_result.best_model, automl_result.best_model]
        ensemble_result = ensemble.create_ensemble(
            X_tr_eng.values, y_tr.values,
            X_val_eng.values, y_val.values,
            base_models=base_models
        )
        results["ensemble"] = ensemble_result.to_dict()
        
        # 5. Make predictions if test set provided
        if X_test is not None:
            X_test_eng, _ = fe.engineer_features(X_test)
            
            # Train final ensemble on full training data
            X_train_eng, _ = fe.engineer_features(X_train, y_train)
            ensemble_result.ensemble_model.fit(X_train_eng, y_train)
            
            predictions = ensemble_result.ensemble_model.predict(X_test_eng)
            results["predictions"] = predictions
        
        results["best_score"] = ensemble_result.ensemble_score
        results["task_type"] = self.task_type
        
        return results