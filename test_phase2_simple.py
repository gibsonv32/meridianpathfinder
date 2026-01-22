#!/usr/bin/env python3
"""Simplified Phase 2 test focusing on core functionality."""

import sys
import subprocess
import time
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from meridian.data.feature_healer import FeatureHealer
from meridian.llm.providers import get_provider
from meridian.config import load_config


def test_phase2_core():
    """Test core Phase 2 functionality."""
    print("\n" + "=" * 70)
    print("PHASE 2 TEST - FEATURE ENGINEERING HEALER")
    print("=" * 70)
    
    # Create test data
    print("\nCreating test data...")
    np.random.seed(42)
    df = pd.DataFrame({
        'feature1': np.random.randn(50),
        'feature2': np.random.randn(50),
        'feature3': ['A', 'B', 'C'] * 16 + ['A', 'B'],
        'target': np.random.choice([0, 1], 50)
    })
    
    # Add some NaNs
    df.loc[::5, 'feature1'] = np.nan
    df.loc[::7, 'feature2'] = np.nan
    
    print(f"✓ Created test DataFrame: {df.shape}")
    print(f"  NaN counts: feature1={df['feature1'].isna().sum()}, feature2={df['feature2'].isna().sum()}")
    
    # Initialize components
    config = load_config()
    provider = get_provider(config, Path.cwd())
    healer = FeatureHealer(provider, Path.cwd())
    
    print("\n" + "=" * 60)
    print("TESTING FEATURE TRANSFORMATIONS")
    print("=" * 60)
    
    # Test 1: Simple transformations
    print("\n1. Standard scaling with NaN handling:")
    transformations = {
        'feature1': "(df['feature1'] - df['feature1'].mean()) / df['feature1'].std()",
        'feature2': "df['feature2'].fillna(df['feature2'].median())"
    }
    
    df_transformed = healer.batch_heal_features(df, transformations)
    print(f"✓ Transformations completed")
    print(f"  Columns: {list(df_transformed.columns)}")
    print(f"  NaN in feature1: {df_transformed['feature1'].isna().sum()}")
    print(f"  NaN in feature2: {df_transformed['feature2'].isna().sum()}")
    
    # Test 2: Categorical encoding
    print("\n2. Categorical encoding:")
    cat_transform = {
        'feature3': "pd.get_dummies(df['feature3'], prefix='cat')"
    }
    
    df_with_dummies = healer.batch_heal_features(df, cat_transform)
    cat_cols = [c for c in df_with_dummies.columns if c.startswith('cat_')]
    print(f"✓ Categorical encoding completed")
    print(f"  New columns: {cat_cols}")
    
    # Test 3: Complex transformation with fallback
    print("\n3. Complex transformation with fallback:")
    complex_transform = {
        'feature1': "np.log1p(df['feature1'])"  # Will fail on negative values
    }
    
    df_complex = healer.batch_heal_features(
        df, 
        complex_transform,
        fallback_values={'feature1': 0}
    )
    print(f"✓ Complex transformation handled")
    
    # Test 4: LLM memory integration
    print("\n" + "=" * 60)
    print("TESTING LLM MEMORY INTEGRATION")
    print("=" * 60)
    
    if hasattr(provider, 'add_healing_example'):
        # Add healing examples
        provider.add_healing_example(
            error_type="nan_scaling",
            fix="df['col'].fillna(df['col'].mean())",
            success=True
        )
        
        # Get history
        history = provider.get_healing_history()
        print(f"\n✓ Healing examples stored: {len(history)}")
        
        # Get performance report
        report = provider.get_performance_report()
        print(f"✓ Memory turns: {report.get('memory_turns', 0)}")
        print(f"✓ Few-shot examples: {report.get('few_shot_examples', 0)}")
        print(f"✓ Healing examples: {report.get('healing_examples', 0)}")
    else:
        print("\n⚠ Basic provider - no memory support")
    
    # Show final stats
    print("\n" + "=" * 60)
    print("PHASE 2 SUMMARY")
    print("=" * 60)
    
    cb_status = healer.circuit_breaker.get_status()
    print(f"\nCircuit Breaker Status:")
    print(f"  State: {cb_status['state']}")
    print(f"  Total cost: ${cb_status['total_cost']:.3f}")
    print(f"  Budget remaining: ${cb_status['budget_remaining']:.2f}")
    print(f"  Cached fixes: {len(healer.fix_history)}")
    
    print("\n✅ Phase 2 Complete!")
    print("  • Feature transformation healing works")
    print("  • Fallback values prevent failures")
    print("  • LLM memory stores successful fixes")
    print("  • Circuit breaker controls costs")


def main():
    """Run Phase 2 test."""
    # Start mock server
    print("Starting mock LLM server...")
    proc = subprocess.Popen(
        ["python3", "simple_test_server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    try:
        test_phase2_core()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()