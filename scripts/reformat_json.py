#!/usr/bin/env python3

import glob
import json
import os


def reorder_node(node):
    """Reorder arrays in nodes recursively"""

    if isinstance(node, list):
        if len([x for x in node if not isinstance(x, str)]) == 0:
            # Only strings in the list, reorder it
            node = node.sort()
        else:
            for sub_node in node:
                reorder_node(sub_node)

    if isinstance(node, dict):
        for key, sub_node in node.items():
            reorder_node(node[key])


def main():
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))

    file_list = glob.glob(os.path.join(root_path, "**/*.json"), recursive=True)
    for filename in file_list:
        print(filename)
        with open(filename, "r") as f:
            json_data = json.load(f)

        reorder_node(json_data)

        with open(filename, "w") as f:
            json.dump(json_data, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
