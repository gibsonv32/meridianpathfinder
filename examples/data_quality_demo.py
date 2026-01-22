#!/usr/bin/env python3
"""
Demo of MERIDIAN Data Quality & Preprocessing Module

This example shows how to:
1. Profile data to understand quality issues
2. Handle missing values with various strategies
3. Detect and treat outliers
4. Engineer features automatically
5. Transform data for ML readiness
6. Use the automated preprocessing pipeline
"""

import pandas as pd
import numpy as np
from sklearn.datasets import make_classification, make_regression
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# MERIDIAN data modules
from meridian.data import (
    DataProfiler,
    MissingValueHandler,
    MissingStrategy,
    OutlierHandler,
    OutlierMethod,
    OutlierTreatment,
    FeatureEngineer,
    AutoFeatureEngineer,
    DataTransformer,
    AutoPreprocessor,
    DataQualityPipeline,
    PreprocessingConfig,
    PreprocessingStrategy
)


def create_messy_data(n_samples=1000):
    """Create a dataset with various quality issues"""
    np.random.seed(42)
    
    # Create base features
    X, y = make_classification(
        n_samples=n_samples,
        n_features=10,
        n_informative=7,
        n_redundant=2,
        n_clusters_per_class=2,
        random_state=42
    )
    
    # Convert to DataFrame
    feature_names = [f"feature_{i}" for i in range(X.shape[1])]
    df = pd.DataFrame(X, columns=feature_names)
    df['target'] = y
    
    # Add missing values
    missing_cols = np.random.choice(feature_names[:5], 3, replace=False)
    for col in missing_cols:
        missing_idx = np.random.choice(n_samples, size=int(n_samples * 0.15), replace=False)
        df.loc[missing_idx, col] = np.nan
    
    # Add outliers
    outlier_cols = np.random.choice(feature_names[5:], 2, replace=False)
    for col in outlier_cols:
        outlier_idx = np.random.choice(n_samples, size=int(n_samples * 0.05), replace=False)
        df.loc[outlier_idx, col] = df[col].mean() + 5 * df[col].std()
    
    # Add categorical column
    df['category'] = np.random.choice(['A', 'B', 'C', 'D'], n_samples)
    
    # Add datetime column
    base_date = datetime.now()
    df['timestamp'] = [base_date - timedelta(days=i) for i in range(n_samples)]
    
    # Add some duplicates
    duplicate_idx = np.random.choice(n_samples, size=20, replace=False)
    df = pd.concat([df, df.iloc[duplicate_idx]], ignore_index=True)
    
    # Add text column
    df['text'] = ['sample text ' + str(i % 10) for i in range(len(df))]
    
    print(f"Created messy dataset with shape: {df.shape}")
    print(f"Missing values: {df.isnull().sum().sum()}")
    print(f"Duplicates: {df.duplicated().sum()}")
    
    return df


def demo_data_profiling(df):
    """Demo data profiling capabilities"""
    print("\n" + "="*60)
    print("DATA PROFILING DEMO")
    print("="*60)
    
    profiler = DataProfiler()
    profile = profiler.profile(df)
    
    print("\nData Profile Summary:")
    print(f"  Shape: {profile.n_rows} rows x {profile.n_columns} columns")
    print(f"  Memory usage: {profile.memory_usage_mb:.2f} MB")
    print(f"  Missing values: {profile.n_missing} ({profile.missing_ratio:.1%})")
    print(f"  Duplicate rows: {profile.n_duplicates} ({profile.duplicate_ratio:.1%})")
    
    print("\nColumn Types:")
    for dtype, count in profile.dtypes_summary.items():
        print(f"  {dtype}: {count}")
    
    # Quality score
    quality_score = profiler.calculate_quality_score(df)
    print(f"\nData Quality Score: {quality_score:.2f}/100")
    
    # Validation
    validator = profiler.create_validator(df)
    validation_result = validator.validate(df)
    
    if validation_result['errors']:
        print("\nValidation Errors:")
        for error in validation_result['errors'][:5]:
            print(f"  - {error}")
    
    return profile


def demo_missing_values(df):
    """Demo missing value handling"""
    print("\n" + "="*60)
    print("MISSING VALUE HANDLING DEMO")
    print("="*60)
    
    strategies = [
        MissingStrategy.MEAN,
        MissingStrategy.MEDIAN,
        MissingStrategy.KNN,
        MissingStrategy.SMART
    ]
    
    for strategy in strategies:
        print(f"\n--- {strategy.value.upper()} Strategy ---")
        
        handler = MissingValueHandler(strategy=strategy)
        df_imputed = handler.fit_transform(df.select_dtypes(include=[np.number]))
        
        missing_before = df.select_dtypes(include=[np.number]).isnull().sum().sum()
        missing_after = df_imputed.isnull().sum().sum()
        
        print(f"Missing before: {missing_before}")
        print(f"Missing after: {missing_after}")
        
        if hasattr(handler, 'strategies_per_column') and handler.strategies_per_column:
            print("Strategies per column:")
            for col, strat in list(handler.strategies_per_column.items())[:3]:
                print(f"  {col}: {strat.value}")


def demo_outlier_detection(df):
    """Demo outlier detection and treatment"""
    print("\n" + "="*60)
    print("OUTLIER DETECTION DEMO")
    print("="*60)
    
    numeric_df = df.select_dtypes(include=[np.number])
    
    methods = [
        (OutlierMethod.IQR, OutlierTreatment.CAP),
        (OutlierMethod.ZSCORE, OutlierTreatment.REMOVE),
        (OutlierMethod.ISOLATION_FOREST, OutlierTreatment.FLAG)
    ]
    
    for method, treatment in methods:
        print(f"\n--- {method.value} + {treatment.value} ---")
        
        handler = OutlierHandler(method=method, treatment=treatment)
        outliers = handler.fit_detect(numeric_df)
        df_treated = handler.treat(numeric_df, outliers)
        
        summary = handler.get_outlier_summary(numeric_df, outliers)
        print(f"Total outliers: {summary['total_outliers']}")
        print(f"Outlier percentage: {summary['outlier_percentage']:.2f}%")
        print(f"Shape after treatment: {df_treated.shape}")


def demo_feature_engineering(df):
    """Demo feature engineering"""
    print("\n" + "="*60)
    print("FEATURE ENGINEERING DEMO")
    print("="*60)
    
    # Separate features and target
    target_col = 'target'
    y = df[target_col] if target_col in df.columns else None
    X = df.drop(columns=[target_col]) if y is not None else df
    
    # Manual feature engineering
    print("\n--- Manual Feature Engineering ---")
    engineer = FeatureEngineer()
    
    # Engineer features
    X_engineered = engineer.fit_transform(X, y, auto_engineer=False)
    
    # Create polynomial features
    numeric_cols = X.select_dtypes(include=[np.number]).columns[:3].tolist()
    if numeric_cols:
        X_engineered = engineer.create_polynomial_features(X_engineered, numeric_cols, degree=2)
    
    # Create text features if text column exists
    if 'text' in X.columns:
        X_engineered = engineer.create_text_features(X_engineered, 'text', method='tfidf', max_features=10)
    
    summary = engineer.get_engineering_summary()
    print(f"Original features: {summary['original_features']}")
    print(f"Engineered features: {summary['engineered_features']}")
    print(f"Total features: {summary['total_features']}")
    
    # Automatic feature engineering
    print("\n--- Automatic Feature Engineering ---")
    auto_engineer = AutoFeatureEngineer()
    X_auto = auto_engineer.fit_transform(X, y, target_feature_count=50)
    
    print(f"Final shape after auto engineering: {X_auto.shape}")
    
    if auto_engineer.feature_importance is not None:
        print("\nTop 5 Important Features:")
        for _, row in auto_engineer.feature_importance.head(5).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")


def demo_transformations(df):
    """Demo data transformations"""
    print("\n" + "="*60)
    print("DATA TRANSFORMATION DEMO")
    print("="*60)
    
    transformer = DataTransformer()
    numeric_df = df.select_dtypes(include=[np.number])
    
    # Apply auto transformations
    print("\n--- Automatic Transformations ---")
    df_transformed = transformer.auto_transform(numeric_df)
    
    summary = transformer.get_transformation_summary()
    print(f"Transformations applied: {summary['n_transformations']}")
    
    for col, info in list(summary['transformations'].items())[:3]:
        print(f"  {col}: {info['type']}")
    
    # Manual transformations
    print("\n--- Manual Transformations ---")
    
    if 'feature_0' in numeric_df.columns:
        # Apply specific transformation
        from meridian.data.transformer import TransformationType
        
        series = numeric_df['feature_0']
        if (series > 0).all():
            transformed = transformer.transform_column(series, TransformationType.LOG)
            print(f"Applied log transform to feature_0")
            print(f"  Skewness before: {series.skew():.2f}")
            print(f"  Skewness after: {transformed.skew():.2f}")


def demo_auto_preprocessing(df):
    """Demo automated preprocessing pipeline"""
    print("\n" + "="*60)
    print("AUTOMATED PREPROCESSING PIPELINE DEMO")
    print("="*60)
    
    strategies = [
        PreprocessingStrategy.MINIMAL,
        PreprocessingStrategy.STANDARD,
        PreprocessingStrategy.ADVANCED
    ]
    
    target_col = 'target'
    y = df[target_col] if target_col in df.columns else None
    X = df.drop(columns=[target_col]) if y is not None else df
    
    for strategy in strategies:
        print(f"\n--- {strategy.value.upper()} Strategy ---")
        
        config = PreprocessingConfig(strategy=strategy)
        preprocessor = AutoPreprocessor(config)
        
        X_processed, result = preprocessor.fit_transform(X, y)
        
        print(f"Original shape: {result.original_shape}")
        print(f"Final shape: {result.final_shape}")
        print(f"Missing imputed: {result.n_missing_imputed}")
        print(f"Outliers treated: {result.n_outliers_treated}")
        print(f"Features engineered: {result.n_features_engineered}")
        print(f"Processing time: {result.processing_time:.2f}s")
        print(f"Steps performed: {', '.join(result.steps_performed)}")


def demo_quality_pipeline(df):
    """Demo complete data quality pipeline"""
    print("\n" + "="*60)
    print("COMPLETE DATA QUALITY PIPELINE DEMO")
    print("="*60)
    
    pipeline = DataQualityPipeline()
    
    # Process with advanced strategy
    config = PreprocessingConfig(
        strategy=PreprocessingStrategy.ADVANCED,
        missing_strategy=MissingStrategy.SMART,
        outlier_method=OutlierMethod.IQR,
        outlier_treatment=OutlierTreatment.CAP,
        auto_engineer=True,
        scale_features=True
    )
    
    X_processed, y, quality_report = pipeline.process(
        df,
        target_col='target',
        config=config
    )
    
    print("\nProcessing Results:")
    print(f"Final shape: {X_processed.shape}")
    
    print("\nQuality Improvements:")
    for metric, values in quality_report['quality_improvement'].items():
        print(f"  {metric}:")
        print(f"    Before: {values['before']:.3f}")
        print(f"    After: {values['after']:.3f}")
        print(f"    Improvement: {values['improvement']:.3f}")
    
    print("\nFeature Changes:")
    for key, value in quality_report['feature_changes'].items():
        print(f"  {key}: {value}")
    
    if quality_report['warnings']:
        print("\nWarnings:")
        for warning in quality_report['warnings']:
            print(f"  - {warning}")
    
    return X_processed, y


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print(" MERIDIAN DATA QUALITY & PREPROCESSING DEMO")
    print("="*80)
    
    # Create messy data
    df = create_messy_data(1000)
    
    # Run demos
    profile = demo_data_profiling(df)
    demo_missing_values(df)
    demo_outlier_detection(df)
    demo_feature_engineering(df)
    demo_transformations(df)
    demo_auto_preprocessing(df)
    X_final, y_final = demo_quality_pipeline(df)
    
    print("\n" + "="*80)
    print(" DEMO COMPLETE")
    print("="*80)
    print("\nThe Data Quality module provides:")
    print("1. Comprehensive data profiling and validation")
    print("2. Flexible missing value handling strategies")
    print("3. Multiple outlier detection and treatment methods")
    print("4. Automated feature engineering")
    print("5. Data transformation utilities")
    print("6. Complete preprocessing pipelines")
    print("\nThis integrates with MERIDIAN modes:")
    print("- Mode 1 (Feasibility): Data quality assessment")
    print("- Mode 2 (Visualization): Profile visualizations")
    print("- Mode 3 (Strategy): Preprocessing recommendations")
    print("- Mode 5 (Code Gen): Generate preprocessing code")
    print("- Mode 6 (Execution): Apply to production data")


if __name__ == "__main__":
    main()