"""
quickstart.py — Minimal usage example

Run:
    python quickstart.py
"""
import sys
from pathlib import Path

# Make the local package importable without installation
sys.path.insert(0, str(Path(__file__).parent))

from ozone_hotspot import diagnose


def main():
    # Replace with your own CSV path
    csv_path = "examples/my_measurement.csv"

    if not Path(csv_path).exists():
        print(f"Please place your CSV at: {csv_path}")
        print("Or edit csv_path in this script.")
        return

    print("Running diagnosis...")
    result = diagnose(csv_path)

    print("\n" + result.summary())

    print("\nSaving results...")
    paths = result.save_all("output/")

    print("\nOutput files:")
    for name, path in paths.items():
        print(f"  {name:20s}  -> {path}")


if __name__ == "__main__":
    main()
