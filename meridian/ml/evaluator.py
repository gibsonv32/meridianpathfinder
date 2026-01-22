"""Model evaluation and comparison utilities for MERIDIAN"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass

from sklearn.metrics import (
    # Classification metrics
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, confusion_matrix, classification_report,
    precision_recall_curve, average_precision_score,
    
    # Regression metrics
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error, explained_variance_score
)
from sklearn.model_selection import cross_val_score, cross_validate

from meridian.logging_config import get_logger
from meridian.utils.exceptions import ErrorContext, DataError

logger = get_logger("meridian.ml.evaluator")


@dataclass
class EvaluationResult:
    """Container for model evaluation results"""
    model_name: str
    metrics: Dict[str, float]
    confusion_matrix: Optional[np.ndarray] = None
    classification_report: Optional[Dict] = None
    feature_importance: Optional[Dict[str, float]] = None
    predictions: Optional[np.ndarray] = None
    probabilities: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "model_name": self.model_name,
            "metrics": self.metrics,
            "confusion_matrix": self.confusion_matrix.tolist() if self.confusion_matrix is not None else None,
            "classification_report": self.classification_report,
            "feature_importance": self.feature_importance
        }
    
    def save(self, path: Path) -> None:
        """Save evaluation results to JSON"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "EvaluationResult":
        """Load evaluation results from JSON"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Convert lists back to numpy arrays
        if data.get("confusion_matrix"):
            data["confusion_matrix"] = np.array(data["confusion_matrix"])
        
        return cls(**data)


class ModelEvaluator:
    """Comprehensive model evaluation"""
    
    def __init__(self, task_type: str = "auto"):
        """
        Initialize evaluator.
        
        Args:
            task_type: "classification", "regression", or "auto" (auto-detect)
        """
        self.task_type = task_type
    
    def evaluate(
        self,
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_name: str = "model",
        feature_names: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        Evaluate model on test set.
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels
            model_name: Name for the model
            feature_names: Feature names for importance
            
        Returns:
            EvaluationResult object
        """
        # Auto-detect task type if needed
        if self.task_type == "auto":
            self.task_type = self._detect_task_type(y_test)
        
        logger.info(f"Evaluating {model_name} ({self.task_type} task)")
        
        with ErrorContext("model_evaluation", model=model_name):
            # Make predictions
            y_pred = model.predict(X_test)
            
            # Get probabilities if available
            y_prob = None
            if hasattr(model, 'predict_proba'):
                y_prob = model.predict_proba(X_test)
            
            # Calculate metrics
            if self.task_type == "classification":
                metrics = self._evaluate_classification(y_test, y_pred, y_prob)
                cm = confusion_matrix(y_test, y_pred)
                cr = classification_report(y_test, y_pred, output_dict=True)
            else:
                metrics = self._evaluate_regression(y_test, y_pred)
                cm = None
                cr = None
            
            # Get feature importance if available
            feature_importance = self._get_feature_importance(model, feature_names or list(X_test.columns))
            
            return EvaluationResult(
                model_name=model_name,
                metrics=metrics,
                confusion_matrix=cm,
                classification_report=cr,
                feature_importance=feature_importance,
                predictions=y_pred,
                probabilities=y_prob
            )
    
    def _detect_task_type(self, y: pd.Series) -> str:
        """Auto-detect task type from target variable"""
        unique_values = y.nunique()
        
        # Heuristic: if < 20 unique values and integers, likely classification
        if unique_values < 20 and y.dtype in ['int64', 'int32']:
            return "classification"
        else:
            return "regression"
    
    def _evaluate_classification(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None
    ) -> Dict[str, float]:
        """Evaluate classification model"""
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, average='weighted', zero_division=0),
            "recall": recall_score(y_true, y_pred, average='weighted', zero_division=0),
            "f1": f1_score(y_true, y_pred, average='weighted', zero_division=0),
        }
        
        # Add AUC if probabilities available
        if y_prob is not None:
            try:
                if len(np.unique(y_true)) == 2:  # Binary classification
                    metrics["auc"] = roc_auc_score(y_true, y_prob[:, 1])
                else:  # Multi-class
                    metrics["auc"] = roc_auc_score(y_true, y_prob, multi_class='ovr', average='weighted')
            except:
                pass
        
        return metrics
    
    def _evaluate_regression(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, float]:
        """Evaluate regression model"""
        return {
            "mse": mean_squared_error(y_true, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
            "mae": mean_absolute_error(y_true, y_pred),
            "r2": r2_score(y_true, y_pred),
            "explained_variance": explained_variance_score(y_true, y_pred),
            "mape": mean_absolute_percentage_error(y_true, y_pred) if not (y_true == 0).any() else None
        }
    
    def _get_feature_importance(
        self,
        model: Any,
        feature_names: List[str]
    ) -> Optional[Dict[str, float]]:
        """Extract feature importance from model"""
        importance = None
        
        # Try different attributes
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
        elif hasattr(model, 'coef_'):
            importance = np.abs(model.coef_).flatten()
        elif hasattr(model, 'get_feature_importance'):
            importance = model.get_feature_importance()
        
        if importance is not None:
            # Ensure proper shape
            if len(importance) == len(feature_names):
                return dict(zip(feature_names, importance))
        
        return None
    
    def cross_validate(
        self,
        model: Any,
        X: pd.DataFrame,
        y: pd.Series,
        cv: int = 5,
        scoring: Optional[Union[str, List[str]]] = None
    ) -> Dict[str, np.ndarray]:
        """
        Perform cross-validation.
        
        Args:
            model: Model to evaluate
            X: Features
            y: Target
            cv: Number of folds
            scoring: Scoring metrics
            
        Returns:
            Dictionary of scores
        """
        if scoring is None:
            scoring = ['accuracy', 'f1_weighted'] if self.task_type == "classification" else ['r2', 'neg_mean_squared_error']
        
        logger.info(f"Running {cv}-fold cross-validation")
        
        scores = cross_validate(
            model, X, y,
            cv=cv,
            scoring=scoring,
            return_train_score=True
        )
        
        return scores


class ModelComparator:
    """Compare multiple models"""
    
    def __init__(self):
        self.results: List[EvaluationResult] = []
        self.evaluator = ModelEvaluator()
    
    def add_model(
        self,
        model: Any,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        model_name: str
    ) -> EvaluationResult:
        """
        Add model to comparison.
        
        Args:
            model: Trained model
            X_test: Test features
            y_test: Test labels
            model_name: Model name
            
        Returns:
            Evaluation result
        """
        result = self.evaluator.evaluate(model, X_test, y_test, model_name)
        self.results.append(result)
        return result
    
    def compare(self, metric: str = "accuracy") -> pd.DataFrame:
        """
        Compare models by metrics.
        
        Args:
            metric: Metric to sort by
            
        Returns:
            Comparison dataframe
        """
        if not self.results:
            return pd.DataFrame()
        
        # Build comparison dataframe
        rows = []
        for result in self.results:
            row = {"model": result.model_name}
            row.update(result.metrics)
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Sort by metric if available
        if metric in df.columns:
            df = df.sort_values(metric, ascending=False)
        
        return df
    
    def plot_comparison(
        self,
        metrics: Optional[List[str]] = None,
        figsize: Tuple[int, int] = (12, 6)
    ) -> plt.Figure:
        """
        Plot model comparison.
        
        Args:
            metrics: Metrics to plot (default: all)
            figsize: Figure size
            
        Returns:
            Matplotlib figure
        """
        df = self.compare()
        
        if df.empty:
            return None
        
        if metrics is None:
            metrics = [col for col in df.columns if col != "model"]
        
        # Create subplots
        n_metrics = len(metrics)
        fig, axes = plt.subplots(1, n_metrics, figsize=figsize)
        
        if n_metrics == 1:
            axes = [axes]
        
        for ax, metric in zip(axes, metrics):
            df.plot(x="model", y=metric, kind="bar", ax=ax, legend=False)
            ax.set_title(metric.replace("_", " ").title())
            ax.set_xlabel("")
            ax.set_ylabel(metric)
            ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        return fig
    
    def get_best_model(self, metric: str = "accuracy") -> str:
        """
        Get name of best model by metric.
        
        Args:
            metric: Metric to optimize
            
        Returns:
            Best model name
        """
        df = self.compare(metric)
        
        if df.empty:
            return None
        
        return df.iloc[0]["model"]
    
    def plot_confusion_matrices(
        self,
        figsize: Tuple[int, int] = (15, 5)
    ) -> plt.Figure:
        """Plot confusion matrices for classification models"""
        # Filter classification results
        classification_results = [r for r in self.results if r.confusion_matrix is not None]
        
        if not classification_results:
            return None
        
        n_models = len(classification_results)
        fig, axes = plt.subplots(1, n_models, figsize=figsize)
        
        if n_models == 1:
            axes = [axes]
        
        for ax, result in zip(axes, classification_results):
            sns.heatmap(
                result.confusion_matrix,
                annot=True,
                fmt='d',
                cmap='Blues',
                ax=ax
            )
            ax.set_title(f"{result.model_name}\nAccuracy: {result.metrics.get('accuracy', 0):.3f}")
            ax.set_xlabel("Predicted")
            ax.set_ylabel("Actual")
        
        plt.tight_layout()
        return fig
    
    def plot_roc_curves(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        models: List[Any],
        model_names: List[str],
        figsize: Tuple[int, int] = (8, 6)
    ) -> plt.Figure:
        """Plot ROC curves for binary classification"""
        fig, ax = plt.subplots(figsize=figsize)
        
        for model, name in zip(models, model_names):
            if hasattr(model, 'predict_proba'):
                y_prob = model.predict_proba(X_test)[:, 1]
                fpr, tpr, _ = roc_curve(y_test, y_prob)
                auc = roc_auc_score(y_test, y_prob)
                
                ax.plot(fpr, tpr, label=f'{name} (AUC = {auc:.3f})')
        
        ax.plot([0, 1], [0, 1], 'k--', label='Random')
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('ROC Curves')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def save_results(self, directory: Path) -> None:
        """Save all results to directory"""
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        
        # Save individual results
        for result in self.results:
            result.save(directory / f"{result.model_name}_evaluation.json")
        
        # Save comparison
        comparison = self.compare()
        comparison.to_csv(directory / "model_comparison.csv", index=False)
        
        # Save plots
        fig = self.plot_comparison()
        if fig:
            fig.savefig(directory / "model_comparison.png")
            plt.close(fig)
        
        fig = self.plot_confusion_matrices()
        if fig:
            fig.savefig(directory / "confusion_matrices.png")
            plt.close(fig)
        
        logger.info(f"Results saved to {directory}")