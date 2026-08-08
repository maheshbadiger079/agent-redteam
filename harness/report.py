"""Prints (and can export) the aggregated trust report from local storage."""

import json
from harness import storage


def print_report():
    stats = storage.summary_stats()
    print("\n=== Aggregated Trust Report ===")
    for k, v in stats.items():
        label = k.replace("_", " ").title()
        print(f"{label}: {v}")
    print()


def export_json(path="trust_report.json"):
    stats = storage.summary_stats()
    with open(path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Exported to {path}")


def main():
    print_report()
    export_json()


if __name__ == "__main__":
    main()

