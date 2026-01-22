# MERIDIAN ML Library Integration Guide

MERIDIAN now includes comprehensive ML library integration supporting multiple frameworks, experiment tracking, and automated model evaluation.

## Features

### 1. Multi-Framework Model Factory
- **Scikit-learn**: 15+ algorithms (LogisticRegression, RandomForest, SVM, etc.)
- **XGBoost**: Gradient boosting for classification/regression
- **LightGBM**: Fast gradient boosting with categorical support
- **PyTorch**: Neural networks with customizable architecture

### 2. MLflow Experiment Tracking
- Automatic experiment logging
- Model versioning
- Metrics comparison
- Artifact storage

### 3. Model Evaluation & Comparison
- Comprehensive metrics calculation
- Cross-validation support
- Model comparison visualizations
- Automatic best model selection

## Quick Start

### Basic Usage

```python
from meridian.ml import create_model, ModelEvaluator, ModelComparator

# Create a model
model = create_model("xgb_classifier", n_estimators=100, learning_rate=0.1)

# Train
model.fit(X_train, y_train)

# Evaluate
evaluator = ModelEvaluator()
result = evaluator.evaluate(model, X_test, y_test, "XGBoost")
print(f"Accuracy: {result.metrics['accuracy']}")

# Compare multiple models
comparator = ModelComparator()
comparator.add_model(model1, X_test, y_test, "Model 1")
comparator.add_model(model2, X_test, y_test, "Model 2")
print(comparator.compare())
```

### With MLflow Tracking

```python
from meridian.ml import AutoMLTracker

# Initialize tracker
tracker = AutoMLTracker(experiment_name="my_experiment")

# Track model training
with tracker.start_run("model_training", mode="3"):
    tracker.log_params({"n_estimators": 100})
    model.fit(X_train, y_train)
    tracker.log_metrics({"accuracy": 0.95})
    tracker.log_model(model, "model")

# Get best model
best_run_id = tracker.get_best_model(metric="accuracy")
best_model = tracker.load_model(best_run_id)
```

## Available Models

### Classification Models

| Framework | Model Type | Key |
|-----------|-----------|------|
| Scikit-learn | Logistic Regression | `logistic_regression` |
| Scikit-learn | Random Forest | `random_forest_classifier` |
| Scikit-learn | Gradient Boosting | `gradient_boosting_classifier` |
| Scikit-learn | SVM | `svc` |
| Scikit-learn | K-Nearest Neighbors | `knn_classifier` |
| Scikit-learn | Decision Tree | `decision_tree_classifier` |
| Scikit-learn | Naive Bayes | `naive_bayes` |
| Scikit-learn | Neural Network | `mlp_classifier` |
| XGBoost | XGB Classifier | `xgb_classifier` |
| LightGBM | LGB Classifier | `lgb_classifier` |
| PyTorch | Neural Network | `neural_network` |

### Regression Models

| Framework | Model Type | Key |
|-----------|-----------|------|
| Scikit-learn | Ridge | `ridge` |
| Scikit-learn | Lasso | `lasso` |
| Scikit-learn | Elastic Net | `elastic_net` |
| Scikit-learn | Random Forest | `random_forest_regressor` |
| Scikit-learn | Gradient Boosting | `gradient_boosting_regressor` |
| Scikit-learn | SVR | `svr` |
| Scikit-learn | K-Nearest Neighbors | `knn_regressor` |
| Scikit-learn | Decision Tree | `decision_tree_regressor` |
| Scikit-learn | Neural Network | `mlp_regressor` |
| XGBoost | XGB Regressor | `xgb_regressor` |
| LightGBM | LGB Regressor | `lgb_regressor` |

## Model Factory

### Creating Models

```python
from meridian.ml import ModelFactory, create_model

# List available models
models = ModelFactory.list_available_models()
print(models)

# Get recommended model
best_model_type = ModelFactory.get_best_model_for_task(
    task_type="classification",
    data_size=10000,
    n_features=50,
    prefer_interpretable=False
)

# Create with parameters
model = create_model(
    "xgb_classifier",
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1
)
```

### Custom Parameters

```python
# XGBoost with early stopping
model = create_model("xgb_classifier")
model.fit(
    X_train, y_train,
    eval_set=[(X_val, y_val)],
    early_stopping_rounds=10
)

# LightGBM with categorical features
model = create_model("lgb_classifier")
model.fit(
    X_train, y_train,
    categorical_features=['cat_col1', 'cat_col2']
)

# PyTorch with custom architecture
model = create_model(
    "neural_network",
    input_size=100,
    hidden_sizes=[256, 128, 64],
    output_size=10,
    task_type="classification"
)
model.fit(X_train, y_train, epochs=100, batch_size=32)
```

## Experiment Tracking

### Setup MLflow

```bash
# Install MLflow
pip install mlflow

# Start MLflow UI (optional)
mlflow ui --port 5000
```

### Track Experiments

```python
from meridian.ml import ExperimentTracker

tracker = ExperimentTracker(
    experiment_name="meridian_experiments",
    tracking_uri="http://localhost:5000"  # Optional
)

# Track a run
with tracker.start_run("experiment_1", mode="3"):
    # Log parameters
    tracker.log_params({
        "model_type": "random_forest",
        "n_estimators": 100,
        "max_depth": 10
    })
    
    # Train model
    model.fit(X_train, y_train)
    
    # Log metrics
    tracker.log_metrics({
        "train_accuracy": 0.95,
        "val_accuracy": 0.92,
        "train_time": 45.2
    })
    
    # Log model
    tracker.log_model(model, "model")
    
    # Log artifacts
    tracker.log_artifact("feature_importance.png")
    
    # Log dataset info
    tracker.log_dataset(X_train, "training_data", target_col="target")
```

### AutoML Tracking

```python
from meridian.ml import AutoMLTracker

tracker = AutoMLTracker()

# Automatically track multiple models
models = ["logistic_regression", "random_forest", "xgb_classifier"]

for model_type in models:
    model = create_model(model_type)
    
    # This tracks everything automatically
    result = tracker.track_model_training(
        model_type=model_type,
        model=model,
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        params={"n_estimators": 100}
    )
    
    print(f"{model_type}: {result['val_metrics']}")

# Get leaderboard
leaderboard = tracker.get_leaderboard(metric="val_accuracy")
print(leaderboard)
```

## Model Evaluation

### Single Model Evaluation

```python
from meridian.ml import ModelEvaluator

evaluator = ModelEvaluator(task_type="auto")  # Auto-detects classification/regression

# Evaluate model
result = evaluator.evaluate(
    model=trained_model,
    X_test=X_test,
    y_test=y_test,
    model_name="My Model"
)

# Access metrics
print(f"Accuracy: {result.metrics['accuracy']}")
print(f"Precision: {result.metrics['precision']}")
print(f"Recall: {result.metrics['recall']}")
print(f"F1: {result.metrics['f1']}")

# Save results
result.save("evaluation_results.json")
```

### Model Comparison

```python
from meridian.ml import ModelComparator

comparator = ModelComparator()

# Add models to compare
models = {
    "Logistic Regression": lr_model,
    "Random Forest": rf_model,
    "XGBoost": xgb_model
}

for name, model in models.items():
    comparator.add_model(model, X_test, y_test, name)

# Get comparison table
comparison = comparator.compare(metric="accuracy")
print(comparison)

# Get best model
best = comparator.get_best_model(metric="f1")
print(f"Best model: {best}")

# Visualizations
fig = comparator.plot_comparison(metrics=["accuracy", "precision", "recall"])
fig.savefig("model_comparison.png")

fig = comparator.plot_confusion_matrices()
fig.savefig("confusion_matrices.png")

fig = comparator.plot_roc_curves(X_test, y_test, models.values(), models.keys())
fig.savefig("roc_curves.png")

# Save all results
comparator.save_results("comparison_results/")
```

### Cross-Validation

```python
evaluator = ModelEvaluator()

# Perform cross-validation
cv_scores = evaluator.cross_validate(
    model=model,
    X=X,
    y=y,
    cv=5,
    scoring=["accuracy", "f1_weighted"]
)

# Print results
for metric, scores in cv_scores.items():
    print(f"{metric}: {scores.mean():.4f} (+/- {scores.std():.4f})")
```

## Integration with MERIDIAN Modes

### Mode 3: Strategy

The model factory is automatically used in Mode 3 to recommend and test models:

```python
# In Mode 3 executor
from meridian.ml import ModelFactory

# Get recommendation based on data characteristics
recommended = ModelFactory.get_best_model_for_task(
    task_type="classification",
    data_size=len(df),
    n_features=df.shape[1],
    prefer_interpretable=feasibility_report.interpretability_required
)
```

### Mode 5: Code Generation

Generated code now uses the ML libraries:

```python
# Generated PROJECT/src/pipeline.py
from meridian.ml import create_model, ModelEvaluator

def train():
    # Load data
    X, y = load_data()
    
    # Create model using factory
    model = create_model(
        model_recommendations.primary_model,
        **model_recommendations.hyperparameters
    )
    
    # Train with MLflow tracking
    with tracker.start_run():
        model.fit(X_train, y_train)
        tracker.log_model(model, "model")
    
    return model
```

### Mode 6: Execution

Evaluation is integrated into execution validation:

```python
# In Mode 6 executor
from meridian.ml import ModelComparator

comparator = ModelComparator()

# Test multiple models
for model_config in code_plan.models:
    model = train_model(model_config)
    comparator.add_model(model, X_test, y_test, model_config.name)

# Select best for production
best_model = comparator.get_best_model(metric="f1")
```

## Advanced Features

### Custom Model Wrapper

```python
from meridian.ml import BaseModel

class CustomModel(BaseModel):
    def get_framework(self) -> str:
        return "custom"
    
    def build(self) -> Any:
        # Build your custom model
        self.model = MyCustomAlgorithm(**self.params)
        return self.model
    
    def fit(self, X, y, **kwargs):
        self.model.train(X, y)
        self.is_fitted = True
        return self
    
    def predict(self, X):
        return self.model.predict(X)

# Register with factory
ModelFactory.FRAMEWORK_MAP["custom"] = CustomModel
ModelFactory.MODEL_FRAMEWORK_MAP["my_custom_model"] = "custom"

# Use it
model = create_model("my_custom_model", custom_param=42)
```

### Ensemble Models

```python
from sklearn.ensemble import VotingClassifier

# Create base models
rf = create_model("random_forest_classifier").model
xgb = create_model("xgb_classifier").model
lgb = create_model("lgb_classifier").model

# Create ensemble
ensemble = VotingClassifier(
    estimators=[('rf', rf), ('xgb', xgb), ('lgb', lgb)],
    voting='soft'
)

ensemble.fit(X_train, y_train)
```

### Hyperparameter Tuning

```python
from sklearn.model_selection import GridSearchCV

# Create base model
base_model = create_model("xgb_classifier").model

# Define parameter grid
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.01, 0.1, 0.3]
}

# Grid search
grid = GridSearchCV(base_model, param_grid, cv=5, scoring='accuracy')
grid.fit(X_train, y_train)

print(f"Best params: {grid.best_params_}")
print(f"Best score: {grid.best_score_}")
```

## Installation

### Required Dependencies

```bash
# Core ML libraries
pip install scikit-learn

# Optional but recommended
pip install xgboost lightgbm

# For neural networks
pip install torch

# For experiment tracking
pip install mlflow

# For visualization
pip install matplotlib seaborn
```

### GPU Support

For GPU acceleration:

```bash
# XGBoost GPU
pip install xgboost[gpu]

# PyTorch GPU (CUDA 11.8)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## Performance Tips

1. **Use LightGBM for large datasets** - It's typically fastest
2. **Enable early stopping** for XGBoost/LightGBM to prevent overfitting
3. **Use categorical features directly** with LightGBM instead of one-hot encoding
4. **Parallelize training** - Most models support `n_jobs=-1`
5. **Cache preprocessed data** to avoid repeated computation
6. **Use MLflow** to track and compare experiments systematically

## Troubleshooting

### ImportError for ML libraries

```bash
# Install missing library
pip install xgboost lightgbm torch mlflow
```

### MLflow connection issues

```python
# Use local file storage instead of server
tracker = ExperimentTracker(
    tracking_uri="file:///home/user/mlruns"
)
```

### Out of memory with large datasets

```python
# Use incremental learning
from sklearn.linear_model import SGDClassifier

model = SGDClassifier()
for chunk in pd.read_csv('large_file.csv', chunksize=1000):
    model.partial_fit(chunk)
```

### Slow training

```python
# Enable parallel processing
model = create_model(
    "random_forest_classifier",
    n_jobs=-1,  # Use all CPU cores
    n_estimators=100
)
```

## Example: Complete ML Pipeline

```python
from meridian.ml import (
    ModelFactory,
    AutoMLTracker,
    ModelComparator,
    create_model
)
from sklearn.model_selection import train_test_split

# Load data
X, y = load_your_data()
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Initialize tracking
tracker = AutoMLTracker(experiment_name="my_project")

# Initialize comparison
comparator = ModelComparator()

# Get recommended model
recommended = ModelFactory.get_best_model_for_task(
    task_type="classification",
    data_size=len(X),
    n_features=X.shape[1]
)

# Test multiple models
models_to_test = [
    recommended,
    "xgb_classifier",
    "lgb_classifier",
    "random_forest_classifier"
]

best_model = None
best_score = 0

for model_type in models_to_test:
    # Create and train model
    model = create_model(model_type)
    
    # Track with MLflow
    with tracker.start_run(f"train_{model_type}"):
        model.fit(X_train, y_train)
        
        # Evaluate
        result = comparator.add_model(
            model, X_test, y_test, model_type
        )
        
        # Track metrics
        tracker.log_metrics(result.metrics)
        tracker.log_model(model, "model")
        
        # Update best
        if result.metrics["accuracy"] > best_score:
            best_score = result.metrics["accuracy"]
            best_model = model

# Show results
print(comparator.compare())
print(f"Best model accuracy: {best_score:.4f}")

# Save everything
comparator.save_results("results/")
best_model.save("models/best_model/")
```

This ML integration makes MERIDIAN a complete end-to-end ML platform!