#!/usr/bin/env python3

import json
from pathlib import Path


def reorder_node(node):
    """Reorder arrays in nodes recursively"""

    if isinstance(node, list):
        # Check if all elements are strings to sort them
        if all(isinstance(x, str) for x in node):
            node.sort()
        else:
            for sub_node in node:
                reorder_node(sub_node)
    elif isinstance(node, dict):
        # Recurse through dictionary values
        for sub_node in node.values():
            reorder_node(sub_node)


def main():
    root_path = Path(__file__).resolve().parent.parent
    json_path = root_path / "l10n"
    for file_path in json_path.rglob("*.json"):
        with open(file_path, encoding="utf-8") as f:
            json_data = json.load(f)

        reorder_node(json_data)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, sort_keys=True)
            f.write("\n")


if __name__ == "__main__":
    main()
