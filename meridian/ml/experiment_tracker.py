"""MLflow experiment tracking integration for MERIDIAN"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
import pandas as pd
import numpy as np

from meridian.logging_config import get_logger
from meridian.utils.exceptions import ErrorContext, MeridianError

logger = get_logger("meridian.ml.experiment_tracker")


class ExperimentTracker:
    """MLflow experiment tracking wrapper"""
    
    def __init__(
        self,
        experiment_name: str = "meridian-experiments",
        tracking_uri: Optional[str] = None,
        artifact_location: Optional[str] = None
    ):
        """
        Initialize experiment tracker.
        
        Args:
            experiment_name: Name of MLflow experiment
            tracking_uri: MLflow tracking server URI (default: local)
            artifact_location: Where to store artifacts
        """
        self.experiment_name = experiment_name
        self.mlflow_available = self._check_mlflow()
        
        if self.mlflow_available:
            import mlflow
            
            # Set tracking URI
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            else:
                # Default to local directory
                mlflow.set_tracking_uri(Path.home() / ".meridian" / "mlruns")
            
            # Create or get experiment
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                self.experiment_id = mlflow.create_experiment(
                    experiment_name,
                    artifact_location=artifact_location
                )
            else:
                self.experiment_id = experiment.experiment_id
            
            mlflow.set_experiment(experiment_name)
            logger.info(f"MLflow tracking initialized: {experiment_name}")
        else:
            logger.warning("MLflow not available - tracking disabled")
            self.experiment_id = None
    
    def _check_mlflow(self) -> bool:
        """Check if MLflow is available"""
        try:
            import mlflow
            return True
        except ImportError:
            return False
    
    @contextmanager
    def start_run(
        self,
        run_name: Optional[str] = None,
        mode: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Context manager for MLflow run.
        
        Args:
            run_name: Name for the run
            mode: MERIDIAN mode context
            tags: Additional tags
            
        Example:
            with tracker.start_run("mode_3_training", mode="3"):
                tracker.log_params({"n_estimators": 100})
                model.fit(X, y)
                tracker.log_metrics({"accuracy": 0.95})
        """
        if not self.mlflow_available:
            yield None
            return
        
        import mlflow
        
        with mlflow.start_run(run_name=run_name) as run:
            # Set tags
            if tags is None:
                tags = {}
            
            tags["meridian.mode"] = mode or "unknown"
            tags["meridian.version"] = "0.1.0"
            
            for key, value in tags.items():
                mlflow.set_tag(key, value)
            
            logger.info(f"Started MLflow run: {run.info.run_id}")
            
            try:
                yield run
            finally:
                logger.info(f"Completed MLflow run: {run.info.run_id}")
    
    def log_params(self, params: Dict[str, Any]) -> None:
        """Log parameters to current run"""
        if not self.mlflow_available:
            return
        
        import mlflow
        
        for key, value in params.items():
            # MLflow params must be strings
            mlflow.log_param(key, str(value))
    
    def log_metrics(
        self,
        metrics: Dict[str, float],
        step: Optional[int] = None
    ) -> None:
        """Log metrics to current run"""
        if not self.mlflow_available:
            return
        
        import mlflow
        
        for key, value in metrics.items():
            mlflow.log_metric(key, value, step=step)
    
    def log_model(
        self,
        model: Any,
        artifact_path: str = "model",
        framework: Optional[str] = None
    ) -> None:
        """
        Log model to MLflow.
        
        Args:
            model: Model to log
            artifact_path: Path in artifacts
            framework: Model framework (auto-detected if None)
        """
        if not self.mlflow_available:
            return
        
        import mlflow
        
        # Auto-detect framework
        if framework is None:
            framework = self._detect_framework(model)
        
        with ErrorContext("log_model", framework=framework):
            if framework == "sklearn":
                import mlflow.sklearn
                mlflow.sklearn.log_model(model, artifact_path)
            elif framework == "xgboost":
                import mlflow.xgboost
                mlflow.xgboost.log_model(model, artifact_path)
            elif framework == "lightgbm":
                import mlflow.lightgbm
                mlflow.lightgbm.log_model(model, artifact_path)
            elif framework == "pytorch":
                import mlflow.pytorch
                mlflow.pytorch.log_model(model, artifact_path)
            elif framework == "tensorflow":
                import mlflow.tensorflow
                mlflow.tensorflow.log_model(model, artifact_path)
            else:
                # Fallback to generic Python function
                import mlflow.pyfunc
                mlflow.pyfunc.log_model(artifact_path, python_model=model)
            
            logger.info(f"Logged {framework} model to MLflow")
    
    def log_artifact(self, local_path: Union[str, Path]) -> None:
        """Log file as artifact"""
        if not self.mlflow_available:
            return
        
        import mlflow
        mlflow.log_artifact(str(local_path))
    
    def log_artifacts(self, local_dir: Union[str, Path]) -> None:
        """Log directory of artifacts"""
        if not self.mlflow_available:
            return
        
        import mlflow
        mlflow.log_artifacts(str(local_dir))
    
    def log_figure(self, figure: Any, artifact_file: str) -> None:
        """Log matplotlib figure"""
        if not self.mlflow_available:
            return
        
        import mlflow
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            figure.savefig(f.name)
            mlflow.log_artifact(f.name, artifact_file)
            os.unlink(f.name)
    
    def log_dataset(
        self,
        df: pd.DataFrame,
        name: str = "dataset",
        target_col: Optional[str] = None
    ) -> None:
        """Log dataset information"""
        if not self.mlflow_available:
            return
        
        import mlflow
        
        # Log dataset stats
        stats = {
            f"{name}.n_rows": len(df),
            f"{name}.n_cols": len(df.columns),
            f"{name}.memory_mb": df.memory_usage(deep=True).sum() / 1024 / 1024,
        }
        
        if target_col and target_col in df.columns:
            target = df[target_col]
            if target.dtype in ['int64', 'float64']:
                stats[f"{name}.target_mean"] = target.mean()
                stats[f"{name}.target_std"] = target.std()
            else:
                stats[f"{name}.target_nunique"] = target.nunique()
        
        for key, value in stats.items():
            mlflow.log_metric(key, value)
        
        # Log sample data
        sample = df.head(100)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            sample.to_csv(f.name, index=False)
            mlflow.log_artifact(f.name, f"{name}_sample.csv")
            os.unlink(f.name)
    
    def _detect_framework(self, model: Any) -> str:
        """Auto-detect model framework"""
        model_class = str(type(model))
        
        if "sklearn" in model_class:
            return "sklearn"
        elif "xgboost" in model_class or "XGB" in model_class:
            return "xgboost"
        elif "lightgbm" in model_class or "LGB" in model_class:
            return "lightgbm"
        elif "torch" in model_class:
            return "pytorch"
        elif "tensorflow" in model_class or "keras" in model_class:
            return "tensorflow"
        else:
            return "unknown"
    
    def compare_runs(
        self,
        metric_name: str = "accuracy",
        max_results: int = 10
    ) -> pd.DataFrame:
        """
        Compare experiment runs.
        
        Args:
            metric_name: Metric to compare
            max_results: Maximum number of runs to return
            
        Returns:
            DataFrame with run comparisons
        """
        if not self.mlflow_available:
            return pd.DataFrame()
        
        import mlflow
        
        # Search runs in current experiment
        runs = mlflow.search_runs(
            experiment_ids=[self.experiment_id],
            order_by=[f"metrics.{metric_name} DESC"],
            max_results=max_results
        )
        
        # Select relevant columns
        columns = ["run_id", "start_time", "tags.mlflow.runName"]
        metric_cols = [col for col in runs.columns if col.startswith("metrics.")]
        param_cols = [col for col in runs.columns if col.startswith("params.")]
        
        return runs[columns + metric_cols + param_cols]
    
    def get_best_model(
        self,
        metric_name: str = "accuracy",
        higher_better: bool = True
    ) -> Optional[str]:
        """
        Get best model run ID.
        
        Args:
            metric_name: Metric to optimize
            higher_better: Whether higher metric is better
            
        Returns:
            Run ID of best model
        """
        if not self.mlflow_available:
            return None
        
        import mlflow
        
        order = "DESC" if higher_better else "ASC"
        runs = mlflow.search_runs(
            experiment_ids=[self.experiment_id],
            order_by=[f"metrics.{metric_name} {order}"],
            max_results=1
        )
        
        if len(runs) > 0:
            return runs.iloc[0]["run_id"]
        
        return None
    
    def load_model(self, run_id: str, artifact_path: str = "model") -> Any:
        """
        Load model from MLflow.
        
        Args:
            run_id: MLflow run ID
            artifact_path: Path to model artifact
            
        Returns:
            Loaded model
        """
        if not self.mlflow_available:
            raise MeridianError("MLflow not available")
        
        import mlflow
        
        model_uri = f"runs:/{run_id}/{artifact_path}"
        return mlflow.pyfunc.load_model(model_uri)


class AutoMLTracker(ExperimentTracker):
    """Extended tracker with AutoML capabilities"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results = []
    
    def track_model_training(
        self,
        model_type: str,
        model: Any,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Track full model training process.
        
        Returns:
            Dictionary with results and run ID
        """
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
        run_name = f"{model_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self.start_run(run_name=run_name, tags={"model_type": model_type}):
            # Log parameters
            self.log_params(params)
            self.log_params({
                "model_type": model_type,
                "n_train_samples": len(X_train),
                "n_val_samples": len(X_val),
                "n_features": X_train.shape[1]
            })
            
            # Train model
            import time
            start_time = time.time()
            model.fit(X_train, y_train)
            train_time = time.time() - start_time
            
            # Make predictions
            y_pred_train = model.predict(X_train)
            y_pred_val = model.predict(X_val)
            
            # Calculate metrics based on task type
            is_classification = len(np.unique(y_train)) < 20  # Simple heuristic
            
            if is_classification:
                train_metrics = {
                    "train_accuracy": accuracy_score(y_train, y_pred_train),
                    "train_precision": precision_score(y_train, y_pred_train, average='weighted'),
                    "train_recall": recall_score(y_train, y_pred_train, average='weighted'),
                    "train_f1": f1_score(y_train, y_pred_train, average='weighted'),
                }
                
                val_metrics = {
                    "val_accuracy": accuracy_score(y_val, y_pred_val),
                    "val_precision": precision_score(y_val, y_pred_val, average='weighted'),
                    "val_recall": recall_score(y_val, y_pred_val, average='weighted'),
                    "val_f1": f1_score(y_val, y_pred_val, average='weighted'),
                }
                
                # Try to get probabilities for AUC
                if hasattr(model, 'predict_proba'):
                    y_prob_val = model.predict_proba(X_val)
                    if len(np.unique(y_val)) == 2:  # Binary classification
                        val_metrics["val_auc"] = roc_auc_score(y_val, y_prob_val[:, 1])
            else:
                train_metrics = {
                    "train_mse": mean_squared_error(y_train, y_pred_train),
                    "train_mae": mean_absolute_error(y_train, y_pred_train),
                    "train_r2": r2_score(y_train, y_pred_train),
                }
                
                val_metrics = {
                    "val_mse": mean_squared_error(y_val, y_pred_val),
                    "val_mae": mean_absolute_error(y_val, y_pred_val),
                    "val_r2": r2_score(y_val, y_pred_val),
                }
            
            # Log all metrics
            self.log_metrics({**train_metrics, **val_metrics, "train_time_seconds": train_time})
            
            # Log model
            self.log_model(model, "model")
            
            # Store results
            result = {
                "model_type": model_type,
                "run_id": mlflow.active_run().info.run_id if self.mlflow_available else None,
                "params": params,
                "train_metrics": train_metrics,
                "val_metrics": val_metrics,
                "train_time": train_time
            }
            
            self.results.append(result)
            
            return result
    
    def get_leaderboard(self, metric: str = "val_accuracy") -> pd.DataFrame:
        """Get leaderboard of all tracked models"""
        if not self.results:
            return pd.DataFrame()
        
        # Create dataframe from results
        rows = []
        for result in self.results:
            row = {
                "model_type": result["model_type"],
                "run_id": result["run_id"],
                "train_time": result["train_time"],
            }
            
            # Add metrics
            for key, value in result["train_metrics"].items():
                row[key] = value
            for key, value in result["val_metrics"].items():
                row[key] = value
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Sort by metric
        if metric in df.columns:
            df = df.sort_values(metric, ascending=False)
        
        return df