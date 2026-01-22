#!/usr/bin/env python3
"""Test the self-healing CSV loader."""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from meridian.data.healer import DataHealer
from meridian.llm.providers import get_provider
from meridian.config import load_config

# Create test CSVs with problems
def create_test_files():
    """Create problematic CSV files for testing."""
    
    # 1. Wrong delimiter (semicolon instead of comma)
    with open("test_semicolon.csv", "w") as f:
        f.write("name;age;city\n")
        f.write("Alice;30;NYC\n")
        f.write("Bob;25;LA\n")
    
    # 2. Tab-delimited
    with open("test_tabs.tsv", "w") as f:
        f.write("name\tage\tcity\n")
        f.write("Charlie\t35\tChicago\n")
        f.write("Diana\t28\tBoston\n")
    
    # 3. Pipe-delimited with weird encoding
    with open("test_pipes.csv", "w", encoding="latin-1") as f:
        f.write("name|age|city\n")
        f.write("Élise|40|París\n")
        f.write("José|33|São Paulo\n")
    
    print("✓ Created 3 problematic CSV files")

def test_healing():
    """Test self-healing on problematic CSVs."""
    print("\n" + "=" * 60)
    print("SELF-HEALING CSV LOADER TEST")
    print("=" * 60)
    
    # Load config and get provider
    config = load_config()
    provider = get_provider(config, Path.cwd())
    
    # Initialize healer
    healer = DataHealer(provider, Path.cwd())
    
    test_files = [
        ("test_semicolon.csv", "Semicolon delimiter"),
        ("test_tabs.tsv", "Tab delimiter"),
        ("test_pipes.csv", "Pipe delimiter + encoding")
    ]
    
    for filename, description in test_files:
        print(f"\nTesting: {description}")
        print("-" * 40)
        
        try:
            # Try normal pandas first (will fail)
            df_normal = pd.read_csv(filename)
            print(f"  Normal pandas: {df_normal.shape}")
        except Exception as e:
            print(f"  ❌ Normal pandas failed: {str(e)[:50]}...")
        
        try:
            # Try with healer
            df_healed = healer.resilient_read_csv(Path(filename))
            print(f"  ✅ Healed successfully! Shape: {df_healed.shape}")
            print(f"     Columns: {list(df_healed.columns)}")
            print(f"     First row: {df_healed.iloc[0].to_dict()}")
        except Exception as e:
            print(f"  ❌ Healing failed: {e}")
    
    print("\n" + "=" * 60)
    print(f"Healing attempts: {healer.healing_count}")
    print(f"Estimated cost: ${healer.healing_count * 0.01:.2f}")
    print(f"Cached fixes: {len(healer.fix_history)}")

if __name__ == "__main__":
    create_test_files()
    
    # Start mock server for testing
    import subprocess
    import time
    
    proc = subprocess.Popen(
        ["python3", "simple_test_server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(2)
    
    try:
        test_healing()
    finally:
        proc.terminate()
        # Clean up test files
        for f in ["test_semicolon.csv", "test_tabs.tsv", "test_pipes.csv"]:
            Path(f).unlink(missing_ok=True)