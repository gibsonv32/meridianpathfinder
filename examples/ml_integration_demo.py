#!/usr/bin/env python3
"""
Demo of MERIDIAN ML Library Integration

This example shows how to:
1. Use the model factory to create different models
2. Track experiments with MLflow
3. Evaluate and compare models
4. Select the best model automatically
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.datasets import make_classification, make_regression
from pathlib import Path

# MERIDIAN ML modules
from meridian.ml import (
    ModelFactory,
    create_model,
    ExperimentTracker,
    AutoMLTracker,
    ModelEvaluator,
    ModelComparator
)


def demo_classification():
    """Demo classification workflow with multiple models"""
    print("\n" + "="*60)
    print("CLASSIFICATION DEMO")
    print("="*60)
    
    # Generate synthetic data
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=15,
        n_redundant=5,
        random_state=42
    )
    
    # Convert to DataFrame for feature names
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    X = pd.DataFrame(X, columns=feature_names)
    y = pd.Series(y, name="target")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=42, stratify=y_train
    )
    
    print(f"Data shape: {X.shape}")
    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")
    
    # Initialize experiment tracking
    tracker = AutoMLTracker(experiment_name="meridian_classification_demo")
    
    # Initialize model comparator
    comparator = ModelComparator()
    
    # Define models to test
    models_to_test = [
        ("logistic_regression", {}),
        ("random_forest_classifier", {"n_estimators": 100, "max_depth": 10}),
        ("xgb_classifier", {"n_estimators": 100, "learning_rate": 0.1}),
    ]
    
    # Try to test LightGBM if available
    try:
        import lightgbm
        models_to_test.append(("lgb_classifier", {"n_estimators": 100, "num_leaves": 31}))
    except ImportError:
        print("LightGBM not available, skipping")
    
    print(f"\nTesting {len(models_to_test)} models...")
    
    # Train and evaluate each model
    best_model = None
    best_score = 0
    
    for model_type, params in models_to_test:
        print(f"\n--- {model_type} ---")
        
        try:
            # Create model
            model = create_model(model_type, **params)
            
            # Track training with MLflow
            if tracker.mlflow_available:
                result = tracker.track_model_training(
                    model_type=model_type,
                    model=model,
                    X_train=X_train,
                    y_train=y_train,
                    X_val=X_val,
                    y_val=y_val,
                    params=params
                )
                print(f"MLflow Run ID: {result['run_id']}")
                print(f"Validation Accuracy: {result['val_metrics'].get('val_accuracy', 0):.4f}")
            else:
                # Train without tracking
                model.fit(X_train, y_train)
            
            # Evaluate on test set
            eval_result = comparator.add_model(model, X_test, y_test, model_type)
            
            print(f"Test Metrics:")
            for metric, value in eval_result.metrics.items():
                if value is not None:
                    print(f"  {metric}: {value:.4f}")
            
            # Track best model
            if eval_result.metrics["accuracy"] > best_score:
                best_score = eval_result.metrics["accuracy"]
                best_model = (model_type, model)
                
        except Exception as e:
            print(f"Failed to train {model_type}: {e}")
    
    # Show comparison
    print("\n" + "="*40)
    print("MODEL COMPARISON")
    print("="*40)
    comparison_df = comparator.compare(metric="accuracy")
    print(comparison_df.to_string())
    
    # Get best model
    best_model_name = comparator.get_best_model(metric="accuracy")
    print(f"\nBest model: {best_model_name} (accuracy: {best_score:.4f})")
    
    # Save results
    output_dir = Path("ml_demo_results")
    comparator.save_results(output_dir)
    print(f"\nResults saved to {output_dir}/")
    
    # Show MLflow leaderboard if available
    if tracker.mlflow_available:
        print("\n" + "="*40)
        print("MLFLOW LEADERBOARD")
        print("="*40)
        leaderboard = tracker.get_leaderboard(metric="val_accuracy")
        print(leaderboard[["model_type", "val_accuracy", "train_time"]].to_string())
    
    return best_model


def demo_regression():
    """Demo regression workflow"""
    print("\n" + "="*60)
    print("REGRESSION DEMO")
    print("="*60)
    
    # Generate synthetic data
    X, y = make_regression(
        n_samples=1000,
        n_features=20,
        n_informative=15,
        noise=10,
        random_state=42
    )
    
    # Convert to DataFrame
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    X = pd.DataFrame(X, columns=feature_names)
    y = pd.Series(y, name="target")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    print(f"Data shape: {X.shape}")
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")
    
    # Initialize evaluator
    evaluator = ModelEvaluator(task_type="regression")
    
    # Define models
    models = [
        ("ridge", {"alpha": 1.0}),
        ("random_forest_regressor", {"n_estimators": 100}),
        ("xgb_regressor", {"n_estimators": 100}),
    ]
    
    print(f"\nTesting {len(models)} models...")
    
    results = []
    for model_type, params in models:
        print(f"\n--- {model_type} ---")
        
        try:
            # Create and train model
            model = create_model(model_type, **params)
            model.fit(X_train, y_train)
            
            # Evaluate
            result = evaluator.evaluate(model, X_test, y_test, model_type)
            results.append(result)
            
            print(f"Test Metrics:")
            for metric, value in result.metrics.items():
                if value is not None:
                    print(f"  {metric}: {value:.4f}")
                    
        except Exception as e:
            print(f"Failed to train {model_type}: {e}")
    
    # Compare results
    if results:
        best_r2 = max(results, key=lambda r: r.metrics.get("r2", 0))
        print(f"\nBest model by R²: {best_r2.model_name} (R² = {best_r2.metrics['r2']:.4f})")


def demo_automl():
    """Demo AutoML with automatic model selection"""
    print("\n" + "="*60)
    print("AUTO-ML DEMO")
    print("="*60)
    
    # Generate data
    X, y = make_classification(
        n_samples=500,
        n_features=10,
        n_informative=8,
        random_state=42
    )
    
    X = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
    y = pd.Series(y, name="target")
    
    # Get recommended model
    recommended_model = ModelFactory.get_best_model_for_task(
        task_type="classification",
        data_size=len(X),
        n_features=X.shape[1],
        prefer_interpretable=False
    )
    
    print(f"Recommended model for this dataset: {recommended_model}")
    
    # List all available models
    print("\nAvailable models by framework:")
    for framework, models in ModelFactory.list_available_models().items():
        print(f"  {framework}: {', '.join(models)}")


def demo_cross_validation():
    """Demo cross-validation"""
    print("\n" + "="*60)
    print("CROSS-VALIDATION DEMO")
    print("="*60)
    
    # Generate data
    X, y = make_classification(n_samples=500, n_features=20, random_state=42)
    X = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
    y = pd.Series(y)
    
    # Create model
    model = create_model("random_forest_classifier", n_estimators=50)
    
    # Perform cross-validation
    evaluator = ModelEvaluator()
    cv_scores = evaluator.cross_validate(model, X, y, cv=5)
    
    print("Cross-validation results:")
    for metric, scores in cv_scores.items():
        if "test_" in metric:
            mean_score = np.mean(scores)
            std_score = np.std(scores)
            print(f"  {metric}: {mean_score:.4f} (+/- {std_score:.4f})")


def demo_neural_network():
    """Demo PyTorch neural network"""
    print("\n" + "="*60)
    print("NEURAL NETWORK DEMO")
    print("="*60)
    
    try:
        import torch
        
        # Generate data
        X, y = make_classification(
            n_samples=1000,
            n_features=20,
            n_classes=2,
            random_state=42
        )
        
        X = pd.DataFrame(X, columns=[f"feature_{i}" for i in range(X.shape[1])])
        y = pd.Series(y)
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Create neural network
        model = create_model(
            "neural_network",
            input_size=20,
            hidden_sizes=[64, 32, 16],
            output_size=1,
            task_type="classification"
        )
        
        print("Neural Network Architecture:")
        print(f"  Input: {20} features")
        print(f"  Hidden: [64, 32, 16] neurons")
        print(f"  Output: 1 (binary classification)")
        
        # Train
        print("\nTraining neural network...")
        model.fit(X_train, y_train, epochs=50, batch_size=32)
        
        # Evaluate
        evaluator = ModelEvaluator()
        result = evaluator.evaluate(model, X_test, y_test, "neural_network")
        
        print("\nTest Metrics:")
        for metric, value in result.metrics.items():
            if value is not None:
                print(f"  {metric}: {value:.4f}")
                
    except ImportError:
        print("PyTorch not installed. Run: pip install torch")


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print(" MERIDIAN ML LIBRARY INTEGRATION DEMO")
    print("="*80)
    
    # Run demos
    demo_classification()
    demo_regression()
    demo_automl()
    demo_cross_validation()
    demo_neural_network()
    
    print("\n" + "="*80)
    print(" DEMO COMPLETE")
    print("="*80)
    print("\nTo use these features in MERIDIAN modes:")
    print("1. The model factory is now available for Mode 3 (Strategy)")
    print("2. MLflow tracking integrates with Mode 5 (Code Generation)")
    print("3. Model evaluation enhances Mode 6 (Execution)")
    print("4. Results feed into Mode 7 (Delivery)")


if __name__ == "__main__":
    main()