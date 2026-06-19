import argparse
import json
import os
import re
from copy import deepcopy
from datetime import date, datetime
from collections import OrderedDict
from typing import Any

import yaml


DEFAULT_RESULT_FILE = "grouped_removed_values.json"
DEFAULT_GROUP_BY = "firstList"
VALID_GROUP_BY_MODES = {"firstList", "nearestList", "root"}


def parse_path(path: str) -> list[str]:
    """
    Convert a bracket path into a list of path segments.

    Example:
        [collection][entries][details][name]

    Becomes:
        ["collection", "entries", "details", "name"]

    The bracket format avoids conflicts with YAML keys that contain dots,
    slashes, spaces, or other special characters.
    """
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"Invalid path: {path}")

    parts = re.findall(r"\[([^\]]+)\]", path.strip())

    if not parts:
        raise ValueError(
            f"Invalid path: {path}. Use bracket notation, for example: [collection][entries][name]"
        )

    return parts


def format_path(location: list[Any]) -> str:
    """Convert a location list into bracket notation."""
    if not location:
        return "$root"

    return "".join(f"[{part}]" for part in location)


def to_json_safe(value: Any) -> Any:
    """
    Convert values loaded from YAML into JSON-safe structures.

    Strings, numbers, booleans, dictionaries, lists, and null values are already
    safe. Date-like and uncommon objects are converted to strings.
    """
    if isinstance(value, dict):
        return {str(key): to_json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [to_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [to_json_safe(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    if isinstance(value, (date, datetime)):
        return value.isoformat()

    return str(value)


def clone_yaml_data(value: Any) -> Any:
    """
    Create a plain recursive copy of YAML data.

    This avoids unexpected shared-object changes when the source YAML contains
    anchors and aliases. Comments and formatting are not preserved by PyYAML.
    """
    if isinstance(value, dict):
        return {clone_yaml_data(key): clone_yaml_data(item) for key, item in value.items()}

    if isinstance(value, list):
        return [clone_yaml_data(item) for item in value]

    if isinstance(value, tuple):
        return tuple(clone_yaml_data(item) for item in value)

    return deepcopy(value)


def is_list_index(part: str) -> bool:
    return part.isdigit()


def resolve_mapping_key(mapping: dict, requested_key: str) -> tuple[bool, Any]:
    """
    Resolve a path segment against a mapping key.

    Exact matches are preferred. If there is no exact match, the function tries
    a unique string representation match. This helps with YAML mappings that use
    numeric or boolean keys.
    """
    if requested_key in mapping:
        return True, requested_key

    string_matches = [key for key in mapping.keys() if str(key) == requested_key]

    if len(string_matches) == 1:
        return True, string_matches[0]

    return False, None


def find_removal_matches(data: Any, path_parts: list[str], label: str, original_path: str) -> list[dict]:
    """
    Find all dictionary keys that match the requested path.

    Rules:
    - If traversal reaches a list and the path does not provide a numeric index,
      traversal continues through every list element.
    - If traversal reaches a list and the path provides a numeric index,
      only that list position is visited.
    - Nested lists are handled recursively.
    - The removal target is always a dictionary key. If that key contains a list,
      the whole list is captured as the removed value.
    """
    matches = []

    def walk(current_data: Any, remaining_parts: list[str], location: list[Any]) -> None:
        if current_data is None or not remaining_parts:
            return

        if isinstance(current_data, list):
            current_part = remaining_parts[0]

            if is_list_index(current_part):
                index = int(current_part)
                if 0 <= index < len(current_data):
                    walk(current_data[index], remaining_parts[1:], location + [index])
                return

            for index, element in enumerate(current_data):
                walk(element, remaining_parts, location + [index])
            return

        if not isinstance(current_data, dict):
            return

        current_key = remaining_parts[0]
        found, actual_key = resolve_mapping_key(current_data, current_key)

        if not found:
            return

        if len(remaining_parts) == 1:
            matches.append({
                "label": label,
                "path": original_path,
                "parent": current_data,
                "actualKey": actual_key,
                "removedKey": str(actual_key),
                "removedPathParts": location + [actual_key],
                "removedValue": deepcopy(current_data[actual_key]),
            })
            return

        walk(current_data[actual_key], remaining_parts[1:], location + [actual_key])

    walk(data, path_parts, [])
    return matches


def derive_group_info(removed_path_parts: list[Any], group_by: str) -> dict:
    """
    Decide where a removed value should be grouped in the result JSON.

    Available modes:
    - firstList: group by the first list element found in the removed path.
    - nearestList: group by the nearest list element before the removed key.
    - root: place all removed values from the same YAML document in one group.
    """
    if group_by == "root":
        return {
            "groupPath": "$root",
            "elementIndex": None,
            "groupFullPath": "$root",
            "groupSortParts": [],
        }

    list_indexes = [index for index, part in enumerate(removed_path_parts) if isinstance(part, int)]

    if not list_indexes:
        return {
            "groupPath": "$root",
            "elementIndex": None,
            "groupFullPath": "$root",
            "groupSortParts": [],
        }

    selected_index = list_indexes[0] if group_by == "firstList" else list_indexes[-1]
    group_path_parts = removed_path_parts[:selected_index]
    group_full_path_parts = removed_path_parts[:selected_index + 1]

    return {
        "groupPath": format_path(group_path_parts),
        "elementIndex": removed_path_parts[selected_index],
        "groupFullPath": format_path(group_full_path_parts),
        "groupSortParts": group_full_path_parts,
    }


def sort_token(token: Any) -> tuple[int, Any]:
    """Create a stable sort token for mixed mapping keys and list indexes."""
    if isinstance(token, int):
        return (1, token)

    return (0, str(token))


def sort_location(location: list[Any]) -> list[tuple[int, Any]]:
    return [sort_token(token) for token in location]


def make_path_identity(location: list[Any]) -> tuple[tuple[str, str | int], ...]:
    """Create a comparable identity for a YAML location path."""
    identity = []

    for part in location:
        if isinstance(part, int):
            identity.append(("index", part))
        else:
            identity.append(("key", str(part)))

    return tuple(identity)


def has_removed_ancestor(
    path_identity: tuple[tuple[str, str | int], ...],
    removed_path_identities: set[tuple[tuple[str, str | int], ...]],
) -> bool:
    """Return True when an ancestor path was already removed."""
    for ancestor in removed_path_identities:
        if len(ancestor) < len(path_identity) and path_identity[:len(ancestor)] == ancestor:
            return True

    return False


def build_grouped_removed_values(documents: list[Any], parsed_keys: list[dict], group_by: str) -> list[dict]:
    """
    Find, group, and remove matching values from the loaded YAML documents.

    Inside each group, values follow the order defined in the JSON configuration.
    """
    all_matches = []

    for document_index, document in enumerate(documents):
        for key_order, key_config in enumerate(parsed_keys):
            matches = find_removal_matches(
                data=document,
                path_parts=key_config["parts"],
                label=key_config["label"],
                original_path=key_config["path"],
            )

            for match_order, match in enumerate(matches):
                group_info = derive_group_info(match["removedPathParts"], group_by)
                all_matches.append({
                    "documentIndex": document_index,
                    "keyOrder": key_order,
                    "matchOrder": match_order,
                    **group_info,
                    **match,
                })

    grouped = OrderedDict()
    removed_parent_keys = set()
    removed_path_identities_by_document = {}

    all_matches.sort(
        key=lambda entry: (
            entry["documentIndex"],
            sort_location(entry["groupSortParts"]),
            entry["keyOrder"],
            sort_location(entry["removedPathParts"]),
            entry["matchOrder"],
        )
    )

    for entry in all_matches:
        document_removed_paths = removed_path_identities_by_document.setdefault(entry["documentIndex"], set())
        current_path_identity = make_path_identity(entry["removedPathParts"])

        if has_removed_ancestor(current_path_identity, document_removed_paths):
            continue

        parent_key = (id(entry["parent"]), entry["actualKey"])

        if parent_key in removed_parent_keys:
            continue

        if entry["actualKey"] not in entry["parent"]:
            continue

        del entry["parent"][entry["actualKey"]]
        removed_parent_keys.add(parent_key)
        document_removed_paths.add(current_path_identity)

        group_key = (
            entry["documentIndex"],
            tuple(entry["groupSortParts"]),
        )

        if group_key not in grouped:
            grouped[group_key] = {
                "documentIndex": entry["documentIndex"],
                "groupPath": entry["groupPath"],
                "elementIndex": entry["elementIndex"],
                "groupFullPath": entry["groupFullPath"],
                "removedValues": [],
            }

        grouped[group_key]["removedValues"].append({
            "label": entry["label"],
            "path": entry["path"],
            "removedKey": entry["removedKey"],
            "removedPath": format_path(entry["removedPathParts"]),
            "removedValue": to_json_safe(entry["removedValue"]),
        })

    return list(grouped.values())


def read_keys_config(json_keys_file: str) -> tuple[list[dict], str, str]:
    with open(json_keys_file, "r", encoding="utf-8") as file:
        config = json.load(file)

    keys = config.get("keys", {})

    if not isinstance(keys, dict) or not keys:
        raise ValueError("The JSON configuration must contain a non-empty 'keys' object.")

    parsed_keys = []

    for label, path in keys.items():
        parsed_keys.append({
            "label": str(label),
            "path": path,
            "parts": parse_path(path),
        })

    output_config = config.get("output", {})
    if not isinstance(output_config, dict):
        output_config = {}

    result_file = output_config.get("removedValuesFile", config.get("resultFile", DEFAULT_RESULT_FILE))
    if not isinstance(result_file, str) or not result_file.strip():
        result_file = DEFAULT_RESULT_FILE

    group_by = output_config.get("groupBy", config.get("groupBy", DEFAULT_GROUP_BY))
    if group_by not in VALID_GROUP_BY_MODES:
        valid_modes = ", ".join(sorted(VALID_GROUP_BY_MODES))
        raise ValueError(f"Invalid group mode: {group_by}. Valid modes: {valid_modes}")

    return parsed_keys, result_file, group_by


def read_yaml_documents(yaml_input_file: str) -> list[Any]:
    with open(yaml_input_file, "r", encoding="utf-8") as file:
        loaded_documents = list(yaml.safe_load_all(file))

    return [clone_yaml_data(document) for document in loaded_documents]


def write_yaml_documents(documents: list[Any], output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8") as file:
        if len(documents) > 1:
            yaml.safe_dump_all(
                documents,
                file,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )
        else:
            yaml.safe_dump(
                documents[0] if documents else None,
                file,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            )


def write_removed_values(result_output_file: str, grouped_removed_values: list[dict]) -> None:
    with open(result_output_file, "w", encoding="utf-8") as file:
        json.dump(
            grouped_removed_values,
            file,
            ensure_ascii=False,
            indent=2,
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove configured keys from a YAML file and export grouped removed values as JSON."
    )
    parser.add_argument("input_yaml", help="Source YAML file.")
    parser.add_argument("keys_json", help="JSON file containing the key paths to remove.")
    parser.add_argument("output_yaml", help="Output YAML file after removals.")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    output_dir = os.path.dirname(os.path.abspath(args.output_yaml)) or "."

    documents = read_yaml_documents(args.input_yaml)
    parsed_keys, result_file_name, group_by = read_keys_config(args.keys_json)

    grouped_removed_values = build_grouped_removed_values(documents, parsed_keys, group_by)

    write_yaml_documents(documents, args.output_yaml)

    result_output_file = os.path.join(output_dir, result_file_name)
    write_removed_values(result_output_file, grouped_removed_values)

    total_removals = sum(len(group["removedValues"]) for group in grouped_removed_values)

    print(f"YAML output: {args.output_yaml}")
    print(f"Grouped removed values: {result_output_file}")
    print(f"Group mode: {group_by}")
    print(f"Total groups: {len(grouped_removed_values)}")
    print(f"Total removals: {total_removals}")


if __name__ == "__main__":
    main()
