# YAML Key Remover

A small Python command-line tool that removes configured keys from any YAML file and exports the removed values to a grouped JSON report.

The tool uses bracket paths such as `[catalog][products][details][name]`. This avoids ambiguity when YAML keys contain dots, slashes, spaces, or other special characters.

## Requirements

- Python 3.10+
- PyYAML

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Usage

```bash
python yaml_key_remover.py input.yaml keys.json output.yaml
```

The command creates:

- `output.yaml`: the YAML file after the configured keys are removed;
- `grouped_removed_values.json`: a JSON report with the removed values grouped by their source location.

## Key configuration

Example `keys.json`:

```json
{
  "output": {
    "removedValuesFile": "grouped_removed_values.json",
    "groupBy": "firstList"
  },
  "keys": {
    "productName": "[catalog][products][details][name]",
    "binCode": "[catalog][products][locations][bins][code]",
    "tags": "[catalog][products][tags]"
  }
}
```

The `keys` object maps friendly labels to bracket paths.

## Path rules

Use bracket notation for every path segment:

```text
[parent][child][target]
```

If the traversal reaches a list and the path does not provide an index, the tool searches every list element automatically.

Example:

```json
{
  "keys": {
    "binCode": "[catalog][products][locations][bins][code]"
  }
}
```

The path above can traverse several nested lists without requiring explicit indexes.

## Removing a value from a specific list position

Use a numeric index when you want to target one position only:

```json
{
  "keys": {
    "firstProductName": "[catalog][products][0][details][name]"
  }
}
```

## Removed values that contain lists

If the removed YAML value is a list, the JSON report keeps it as a JSON array.

For example, this path:

```json
{
  "keys": {
    "tags": "[catalog][products][tags]"
  }
}
```

Can produce a report entry like this:

```json
{
  "label": "tags",
  "removedKey": "tags",
  "removedValue": [
    "sample",
    "demo"
  ]
}
```

## Grouping modes

The optional `groupBy` setting controls how the JSON report groups removed values:

- `firstList`: group by the first list element found in the removed value path. This is the default.
- `nearestList`: group by the closest list element before the removed key.
- `root`: group all removed values from the same YAML document together.

Example:

```json
{
  "output": {
    "groupBy": "nearestList"
  },
  "keys": {
    "binCode": "[catalog][products][locations][bins][code]"
  }
}
```

## Known limitations

- Comments are not preserved.
- Formatting, indentation, quotes, and scalar style may change in the generated YAML.
- The tool removes dictionary keys. It does not directly remove a standalone scalar list element.
- YAML anchors and aliases may be expanded or reformatted in the generated output.
- Recursive YAML aliases are not supported.
- If a parent key and one of its child keys are configured for removal at the same time, prefer removing only the parent key or only the child keys to avoid redundant report expectations.

## Example

```bash
python yaml_key_remover.py examples/sample.yaml examples/keys.json examples/output.yaml
```
