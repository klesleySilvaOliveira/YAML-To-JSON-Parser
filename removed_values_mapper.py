import argparse
import json
import os
from typing import Any


DEFAULT_DUPLICATE_LABEL_MODE = "list"
VALID_DUPLICATE_LABEL_MODES = {"list", "last", "error"}
GROUP_METADATA_KEYS = ("documentIndex", "groupPath", "elementIndex", "groupFullPath")


def normalize_mapped_value(
    label: str,
    value: Any,
    unwrap_single_item_lists: bool,
    unwrap_labels: set[str],
) -> Any:
    """
    Optionally unwrap single-item lists in the compact mapped output.

    By default, YAML lists are preserved as JSON arrays. This is the safest
    behavior because it keeps the source data type intact. A label can be
    explicitly configured for unwrapping when a single-item list should be
    easier to read as a scalar value in the mapped report.
    """
    should_unwrap = unwrap_single_item_lists or label in unwrap_labels

    if should_unwrap and isinstance(value, list) and len(value) == 1:
        return value[0]

    return value


def add_mapped_value(
    target: dict[str, Any],
    duplicate_labels: set[str],
    label: str,
    value: Any,
    duplicate_label_mode: str,
) -> None:
    """
    Add a removed value to the target mapping using its label as the JSON key.

    Duplicate labels can happen when more than one removed value with the same
    label belongs to the same group. The default behavior preserves all values
    by converting duplicates into a list.
    """
    if label not in target:
        target[label] = value
        return

    if duplicate_label_mode == "last":
        target[label] = value
        return

    if duplicate_label_mode == "error":
        raise ValueError(f"Duplicate label found in the same group: {label}")

    if duplicate_label_mode != "list":
        valid_modes = ", ".join(sorted(VALID_DUPLICATE_LABEL_MODES))
        raise ValueError(f"Invalid duplicate label mode: {duplicate_label_mode}. Valid modes: {valid_modes}")

    if label not in duplicate_labels:
        target[label] = [target[label]]
        duplicate_labels.add(label)

    target[label].append(value)


def build_group_metadata(group: dict[str, Any]) -> dict[str, Any]:
    """Return source-location metadata for one mapped group."""
    return {key: group.get(key) for key in GROUP_METADATA_KEYS if key in group}


def map_grouped_removed_values(
    grouped_removed_values: list[dict[str, Any]],
    duplicate_label_mode: str = DEFAULT_DUPLICATE_LABEL_MODE,
    include_group_metadata: bool = False,
    unwrap_single_item_lists: bool = False,
    unwrap_labels: set[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Convert grouped removed values into one compact label-to-value object per group.

    Input format:
        [
          {
            "groupFullPath": "[collection][0]",
            "removedValues": [
              {"label": "name", "removedValue": "Example"},
              {"label": "status", "removedValue": "active"}
            ]
          }
        ]

    Default output format:
        [
          {
            "name": "Example",
            "status": "active"
          }
        ]

    When include_group_metadata is enabled, source-location details are stored
    under the reserved "_group" key to avoid conflicts with user labels.
    """
    if duplicate_label_mode not in VALID_DUPLICATE_LABEL_MODES:
        valid_modes = ", ".join(sorted(VALID_DUPLICATE_LABEL_MODES))
        raise ValueError(f"Invalid duplicate label mode: {duplicate_label_mode}. Valid modes: {valid_modes}")

    if not isinstance(grouped_removed_values, list):
        raise ValueError("The grouped removed values JSON must be a list.")

    if unwrap_labels is None:
        unwrap_labels = set()

    mapped_groups = []

    for group_index, group in enumerate(grouped_removed_values):
        if not isinstance(group, dict):
            raise ValueError(f"Invalid group at index {group_index}. Each group must be an object.")

        removed_values = group.get("removedValues", [])

        if not isinstance(removed_values, list):
            raise ValueError(f"Invalid removedValues at group index {group_index}. It must be a list.")

        mapped_group: dict[str, Any] = {}

        if include_group_metadata:
            mapped_group["_group"] = build_group_metadata(group)

        duplicate_labels = set()

        for item_index, item in enumerate(removed_values):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Invalid removed value at group index {group_index}, item index {item_index}. "
                    "Each removed value must be an object."
                )

            if "label" not in item:
                raise ValueError(f"Missing label at group index {group_index}, item index {item_index}.")

            if "removedValue" not in item:
                raise ValueError(f"Missing removedValue at group index {group_index}, item index {item_index}.")

            label = str(item["label"])
            value = normalize_mapped_value(
                label=label,
                value=item["removedValue"],
                unwrap_single_item_lists=unwrap_single_item_lists,
                unwrap_labels=unwrap_labels,
            )

            add_mapped_value(
                mapped_group,
                duplicate_labels,
                label,
                value,
                duplicate_label_mode,
            )

        mapped_groups.append(mapped_group)

    return mapped_groups


def read_grouped_removed_values(input_json: str) -> list[dict[str, Any]]:
    with open(input_json, "r", encoding="utf-8") as file:
        return json.load(file)


def ensure_parent_directory(file_path: str) -> None:
    parent_directory = os.path.dirname(os.path.abspath(file_path))
    if parent_directory:
        os.makedirs(parent_directory, exist_ok=True)


def write_mapped_values(output_json: str, mapped_values: list[dict[str, Any]]) -> None:
    ensure_parent_directory(output_json)
    with open(output_json, "w", encoding="utf-8") as file:
        json.dump(mapped_values, file, ensure_ascii=False, indent=2)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert grouped removed values into a compact label-to-value JSON report."
    )
    parser.add_argument("input_json", help="Grouped removed values JSON file.")
    parser.add_argument("output_json", help="Output mapped JSON file.")
    parser.add_argument(
        "--duplicate-labels",
        choices=sorted(VALID_DUPLICATE_LABEL_MODES),
        default=DEFAULT_DUPLICATE_LABEL_MODE,
        help="How to handle repeated labels inside the same group. Default: list.",
    )
    parser.add_argument(
        "--include-group-metadata",
        action="store_true",
        help="Include source-location metadata under the reserved _group key.",
    )
    parser.add_argument(
        "--unwrap-single-item-lists",
        action="store_true",
        help="Convert every single-item list into its single value in the mapped output.",
    )
    parser.add_argument(
        "--unwrap-label",
        action="append",
        default=[],
        help="Convert a single-item list into a scalar only for this label. Can be used more than once.",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    grouped_removed_values = read_grouped_removed_values(args.input_json)
    mapped_values = map_grouped_removed_values(
        grouped_removed_values=grouped_removed_values,
        duplicate_label_mode=args.duplicate_labels,
        include_group_metadata=args.include_group_metadata,
        unwrap_single_item_lists=args.unwrap_single_item_lists,
        unwrap_labels=set(args.unwrap_label or []),
    )
    write_mapped_values(args.output_json, mapped_values)

    print(f"Mapped removed values: {args.output_json}")
    print(f"Total groups: {len(mapped_values)}")


if __name__ == "__main__":
    main()
