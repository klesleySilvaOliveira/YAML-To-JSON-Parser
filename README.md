# YAML Key Remover

A small Python command-line tool that removes configured keys from YAML files and exports the removed values to JSON reports.

The tool uses bracket paths such as `[catalog][products][details][name]`. This avoids ambiguity when YAML keys contain dots, slashes, spaces, or other special characters.

## Features

- Removes configured dictionary keys from YAML documents.
- Supports YAML files with one or many documents.
- Traverses lists automatically when no numeric index is provided.
- Supports nested lists.
- Supports explicit list indexes when only one position should be targeted.
- Keeps removed lists as JSON arrays in the report.
- Generates a grouped JSON report with the removed values grouped by source location.
- Optionally generates a compact mapped JSON report where each configured label becomes a key.
- Uses only generic examples and does not depend on any specific YAML platform or schema.

## Getting the project

Clone the repository from GitHub and enter the project directory.

Choose one clone option.

HTTPS:

```bash
git clone https://github.com/klesleySilvaOliveira/YAML-To-JSON-Parser.git
cd YAML-To-JSON-Parser
```

SSH:

```bash
git clone git@github.com:klesleySilvaOliveira/YAML-To-JSON-Parser.git
cd YAML-To-JSON-Parser
```

Use HTTPS when you prefer a simpler clone command or when SSH is not configured on the machine. Use SSH when your GitHub SSH key is already configured.

If the repository is private, make sure the GitHub account configured on the machine has access to it. For SSH, also make sure SSH authentication is properly configured before cloning.

After cloning, build the Docker image:

```bash
docker build -t yaml-key-remover .
```

Then run the example using the command that matches your terminal.

Linux, macOS, WSL, or Git Bash:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd):/work" \
  -w /work \
  yaml-key-remover \
  examples/sample.yaml \
  examples/keys.json \
  examples/output.yaml
```

Windows PowerShell:

```powershell
docker run --rm `
  -v "${PWD}:/work" `
  -w /work `
  yaml-key-remover `
  examples/sample.yaml `
  examples/keys.json `
  examples/output.yaml
```

Windows CMD:

```cmd
docker run --rm ^
  -v "%cd%:/work" ^
  -w /work ^
  yaml-key-remover ^
  examples/sample.yaml ^
  examples/keys.json ^
  examples/output.yaml
```

To use your own files, place them inside the cloned project directory or mount the external folder with Docker. Then update the input YAML path, key configuration path, and output YAML path in the command.

## Requirements for local execution

- Python 3.10+
- PyYAML

## Local installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, the activation command is usually:

```powershell
.venv\Scripts\Activate.ps1
```

## Local usage

```bash
python yaml_key_remover.py input.yaml keys.json output.yaml
```

The command creates:

- `output.yaml`: the YAML file after the configured keys are removed.
- `grouped_removed_values.json`: a JSON report with the removed values grouped by their source location.

## Optional mapped JSON output

The grouped report keeps the full details of each removed value. The mapped report creates a simpler list where each item is a direct `label` to `removedValue` mapping. This removes the repeated `label` and `removedValue` fields and makes the result easier to read.

Grouped report example:

```json
[
  {
    "documentIndex": 0,
    "groupFullPath": "[collection][0]",
    "removedValues": [
      {
        "label": "entryName",
        "removedValue": "Example A"
      },
      {
        "label": "entryStatus",
        "removedValue": "active"
      }
    ]
  }
]
```

Mapped report example:

```json
[
  {
    "entryName": "Example A",
    "entryStatus": "active"
  }
]
```

You can generate the mapped report together with the main remover by passing `--mapped-output`:

```bash
python yaml_key_remover.py input.yaml keys.json output.yaml --mapped-output mapped_removed_values.json
```

You can also enable it in the key configuration file:

```json
{
  "output": {
    "removedValuesFile": "grouped_removed_values.json",
    "mappedValuesFile": "mapped_removed_values.json",
    "groupBy": "firstList",
    "duplicateLabels": "list"
  },
  "keys": {
    "entryName": "[collection][entries][details][name]",
    "entryStatus": "[collection][entries][details][status]"
  }
}
```

The example file `examples/keys_with_mapped_output.json` already enables this behavior.

Run it locally:

```bash
python yaml_key_remover.py examples/sample.yaml examples/keys_with_mapped_output.json examples/output.yaml
```

This creates the cleaned YAML and both JSON reports in the output directory.

## Standalone mapped report generation

The mapped report can also be generated later from an existing grouped report:

```bash
python removed_values_mapper.py grouped_removed_values.json mapped_removed_values.json
```

This is useful when you already have `grouped_removed_values.json` and only want to create the compact label-to-value version.

### Duplicate labels

Duplicate labels can happen when the same configured label is removed more than once inside the same group. By default, duplicates are preserved as a list.

Example output:

```json
[
  {
    "code": [
      "A-01",
      "A-02"
    ]
  }
]
```

Available duplicate label modes:

- `list`: preserve all values as a list. This is the default.
- `last`: keep only the last value found for the repeated label.
- `error`: stop execution when a duplicate label is found in the same group.

Local CLI example:

```bash
python yaml_key_remover.py input.yaml keys.json output.yaml \
  --mapped-output mapped_removed_values.json \
  --duplicate-labels list
```

Standalone mapper example:

```bash
python removed_values_mapper.py grouped_removed_values.json mapped_removed_values.json --duplicate-labels list
```

### Keeping source-location metadata in the mapped report

By default, the mapped report contains only configured labels and removed values. If you also want the source location of each mapped item, enable group metadata. Metadata is stored under the reserved `_group` key to avoid conflicts with your labels.

```bash
python removed_values_mapper.py grouped_removed_values.json mapped_removed_values.json --include-group-metadata
```

Example output:

```json
[
  {
    "_group": {
      "documentIndex": 0,
      "groupFullPath": "[collection][0]"
    },
    "entryName": "Example A",
    "entryStatus": "active"
  }
]
```

You can also enable this in the JSON configuration file:

```json
{
  "output": {
    "mappedValuesFile": "mapped_removed_values.json",
    "mappedIncludeGroupMetadata": true
  },
  "keys": {
    "entryName": "[collection][entries][details][name]"
  }
}
```

### Single-item lists in mapped output

By default, if a removed YAML value is a list, it stays as a JSON array in the mapped report. This keeps the source data type intact.

For example, this removed value:

```json
{
  "label": "targetNames",
  "removedValue": [
    "alpha"
  ]
}
```

becomes this by default:

```json
[
  {
    "targetNames": [
      "alpha"
    ]
  }
]
```

If a specific label should be easier to read as a scalar when the list has only one item, use `--unwrap-label`:

```bash
python removed_values_mapper.py grouped_removed_values.json mapped_removed_values.json --unwrap-label targetNames
```

Result:

```json
[
  {
    "targetNames": "alpha"
  }
]
```

You can also configure this behavior in `keys.json`:

```json
{
  "output": {
    "mappedValuesFile": "mapped_removed_values.json",
    "unwrapLabels": [
      "targetNames"
    ]
  },
  "keys": {
    "targetNames": "[collection][entries][targets]"
  }
}
```

To unwrap every single-item list, use `--unwrap-single-item-lists` or set `unwrapSingleItemLists` to `true`. Use this carefully because it applies to every label.

## Docker usage

Docker lets you run the tool without installing Python dependencies on your machine.

Build the image:

```bash
docker build -t yaml-key-remover .
```

Run the example files stored in the `examples` directory.

Linux, macOS, WSL, or Git Bash:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd):/work" \
  -w /work \
  yaml-key-remover \
  examples/sample.yaml \
  examples/keys.json \
  examples/output.yaml
```

Windows PowerShell:

```powershell
docker run --rm `
  -v "${PWD}:/work" `
  -w /work `
  yaml-key-remover `
  examples/sample.yaml `
  examples/keys.json `
  examples/output.yaml
```

Windows CMD:

```cmd
docker run --rm ^
  -v "%cd%:/work" ^
  -w /work ^
  yaml-key-remover ^
  examples/sample.yaml ^
  examples/keys.json ^
  examples/output.yaml
```

Run the example with mapped output enabled.

Linux, macOS, WSL, or Git Bash:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd):/work" \
  -w /work \
  yaml-key-remover \
  examples/sample.yaml \
  examples/keys_with_mapped_output.json \
  examples/output.yaml
```

Windows PowerShell:

```powershell
docker run --rm `
  -v "${PWD}:/work" `
  -w /work `
  yaml-key-remover `
  examples/sample.yaml `
  examples/keys_with_mapped_output.json `
  examples/output.yaml
```

Windows CMD:

```cmd
docker run --rm ^
  -v "%cd%:/work" ^
  -w /work ^
  yaml-key-remover ^
  examples/sample.yaml ^
  examples/keys_with_mapped_output.json ^
  examples/output.yaml
```

Run with your own files stored inside the project directory.

Linux, macOS, WSL, or Git Bash:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd):/work" \
  -w /work \
  yaml-key-remover \
  input.yaml \
  keys.json \
  output.yaml \
  --mapped-output mapped_removed_values.json
```

Windows PowerShell:

```powershell
docker run --rm `
  -v "${PWD}:/work" `
  -w /work `
  yaml-key-remover `
  input.yaml `
  keys.json `
  output.yaml `
  --mapped-output mapped_removed_values.json
```

Windows CMD:

```cmd
docker run --rm ^
  -v "%cd%:/work" ^
  -w /work ^
  yaml-key-remover ^
  input.yaml ^
  keys.json ^
  output.yaml ^
  --mapped-output mapped_removed_values.json
```

The `-w /work` option sets the container working directory to `/work`. This allows you to pass relative paths such as `examples/sample.yaml` instead of `/work/examples/sample.yaml`.

The `--user "$(id -u):$(id -g)"` option helps avoid root-owned output files on Linux. On native Windows terminals, you can usually omit this option.

Line continuation characters depend on the terminal. Use `\` in Linux-style shells, the backtick character in PowerShell, and `^` in CMD. In PowerShell, the backtick must be the last character on the line, with no spaces after it.

### Docker standalone mapper usage

You can also run only the mapped report converter inside the same Docker image.

Linux, macOS, WSL, or Git Bash:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd):/work" \
  -w /work \
  --entrypoint python \
  yaml-key-remover \
  /app/removed_values_mapper.py \
  grouped_removed_values.json \
  mapped_removed_values.json
```

Windows PowerShell:

```powershell
docker run --rm `
  -v "${PWD}:/work" `
  -w /work `
  --entrypoint python `
  yaml-key-remover `
  /app/removed_values_mapper.py `
  grouped_removed_values.json `
  mapped_removed_values.json
```

Windows CMD:

```cmd
docker run --rm ^
  -v "%cd%:/work" ^
  -w /work ^
  --entrypoint python ^
  yaml-key-remover ^
  /app/removed_values_mapper.py ^
  grouped_removed_values.json ^
  mapped_removed_values.json
```

### Docker file path rules

When using Docker, the container can only access files from directories that were mounted with `-v`. In the commands above, this part:

```bash
-v "$(pwd):/work"
```

means that only the current host directory is available inside the container as `/work`.

If your YAML file is outside the project directory, for example in your `Downloads` folder, passing the host path directly will not work unless that folder is also mounted. You have two common options.

Option 1: copy the YAML file into the project directory and run the command normally.

Option 2: mount the external folder too.

Linux, macOS, WSL, or Git Bash example:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd):/work" \
  -v "$HOME/Downloads:/input:ro" \
  -w /work \
  yaml-key-remover \
  /input/my-file.yaml \
  examples/keys.json \
  output.yaml
```

Windows PowerShell example:

```powershell
docker run --rm `
  -v "${PWD}:/work" `
  -v "$HOME/Downloads:/input:ro" `
  -w /work `
  yaml-key-remover `
  /input/my-file.yaml `
  examples/keys.json `
  output.yaml
```

In these examples, the input YAML is read from the mounted `Downloads` folder, while the configuration file and output files remain in the project directory.

## Docker Compose usage

Build the image:

```bash
docker compose build
```

Run the default example:

```bash
UID=$(id -u) GID=$(id -g) docker compose run --rm yaml-key-remover \
  examples/sample.yaml \
  examples/keys.json \
  examples/output.yaml
```

Run the mapped output example:

```bash
UID=$(id -u) GID=$(id -g) docker compose run --rm yaml-key-remover \
  examples/sample.yaml \
  examples/keys_with_mapped_output.json \
  examples/output.yaml
```

On native Windows terminals, you may need to set `UID` and `GID` differently or remove the `user` line from `compose.yaml` if your Docker environment does not support Linux user IDs.

## Makefile usage

Build the image:

```bash
make build
```

Run the default example:

```bash
make run-example
```

Run the example with mapped output enabled:

```bash
make run-example-mapped
```

Generate a mapped report from an existing grouped report:

```bash
make map-example
```

Show help for the main remover command:

```bash
make help
```

## Key configuration file

The JSON configuration file must contain a `keys` object. Each property name inside `keys` is the output label, and each value is the YAML path to remove.

The `output` object is optional. It controls report file names, report paths, grouping behavior, and mapped-output behavior.

Example:

```json
{
  "output": {
    "removedValuesFile": "results/grouped_removed_values.json",
    "mappedValuesFile": "results/mapped_removed_values.json",
    "groupBy": "firstList",
    "duplicateLabels": "list",
    "mappedIncludeGroupMetadata": false,
    "unwrapLabels": [
      "targetNames"
    ],
    "unwrapSingleItemLists": false
  },
  "keys": {
    "productName": "[catalog][products][details][name]",
    "binCode": "[catalog][products][locations][bins][code]",
    "tags": "[catalog][products][tags]"
  }
}
```

### `output` options

#### `removedValuesFile`

Optional. Defines the file name or file path for the grouped JSON report.

Default value:

```text
grouped_removed_values.json
```

This file contains the detailed report with source-location metadata and a `removedValues` list for each group.

You can provide only a file name:

```json
{
  "output": {
    "removedValuesFile": "grouped_removed_values.json"
  }
}
```

You can also provide a relative folder path:

```json
{
  "output": {
    "removedValuesFile": "results/grouped_removed_values.json"
  }
}
```

Relative report paths are resolved from the directory of the output YAML file. For example, if the command writes the YAML output to `examples/output.yaml` and `removedValuesFile` is `results/grouped_removed_values.json`, the grouped report will be written to:

```text
examples/results/grouped_removed_values.json
```

The tool creates missing output folders automatically when it has permission to do so.

Absolute paths are also accepted, but they must be valid inside the runtime environment. With Docker, prefer paths inside the mounted working directory, such as:

```json
{
  "output": {
    "removedValuesFile": "/work/results/grouped_removed_values.json"
  }
}
```

A path such as `/results/grouped_removed_values.json` only works if `/results` exists inside the container or is mounted as a Docker volume and the container user has write permission. For most Docker usage, `results/grouped_removed_values.json` is more portable.

#### `mappedValuesFile`

Optional. Defines the file name or file path for the compact mapped JSON report.

If omitted, the mapped report is not generated unless `--mapped-output` is passed in the command line.

Example:

```json
{
  "output": {
    "mappedValuesFile": "results/mapped_removed_values.json"
  }
}
```

The mapped report transforms this detailed structure:

```json
{
  "removedValues": [
    {
      "label": "entryName",
      "removedValue": "Example A"
    },
    {
      "label": "entryStatus",
      "removedValue": "active"
    }
  ]
}
```

Into this compact structure:

```json
{
  "entryName": "Example A",
  "entryStatus": "active"
}
```

#### `groupBy`

Optional. Controls how the grouped JSON report groups removed values.

Available values:

- `firstList`: group by the first list element found in the removed value path. This is the default.
- `nearestList`: group by the closest list element before the removed key.
- `root`: group all removed values from the same YAML document together.

Example:

```json
{
  "output": {
    "groupBy": "firstList"
  }
}
```

#### `duplicateLabels`

Optional. Controls how repeated labels are handled in the mapped JSON report when the same label appears more than once inside the same group.

Available values:

- `list`: preserve all repeated values as a JSON array. This is the default.
- `last`: keep only the last value found for the repeated label.
- `error`: stop execution when a repeated label is found in the same group.

Example:

```json
{
  "output": {
    "duplicateLabels": "list"
  }
}
```

#### `mappedIncludeGroupMetadata`

Optional. Adds source-location metadata to each mapped item under the reserved `_group` key.

Default value:

```json
false
```

Example:

```json
{
  "output": {
    "mappedIncludeGroupMetadata": true
  }
}
```

Example mapped output with metadata:

```json
[
  {
    "_group": {
      "documentIndex": 0,
      "groupFullPath": "[collection][0]"
    },
    "entryName": "Example A"
  }
]
```

#### `unwrapLabels`

Optional. Defines specific labels that should convert single-item lists into scalar values in the mapped report.

Default behavior preserves YAML lists as JSON arrays. This option is useful when a field is technically a list in YAML but usually contains only one value and is easier to read as a scalar.

Example:

```json
{
  "output": {
    "unwrapLabels": [
      "targetNames"
    ]
  }
}
```

A removed value like this:

```json
{
  "label": "targetNames",
  "removedValue": [
    "alpha"
  ]
}
```

Becomes this in the mapped report:

```json
{
  "targetNames": "alpha"
}
```

#### `unwrapSingleItemLists`

Optional. Converts every single-item list into its single scalar value in the mapped report.

Default value:

```json
false
```

Use this carefully because it applies to every label. If you only want this behavior for specific labels, prefer `unwrapLabels`.

Example:

```json
{
  "output": {
    "unwrapSingleItemLists": true
  }
}
```

### `keys` options

Each property inside `keys` maps an output label to a YAML path. The label is the name that will appear in the JSON reports, and the path tells the tool which YAML key should be removed.

Example:

```json
{
  "keys": {
    "entryName": "[collection][entries][details][name]",
    "entryStatus": "[collection][entries][details][status]"
  }
}
```

If the grouped report finds these values in the same group, the mapped report can produce:

```json
[
  {
    "entryName": "Example A",
    "entryStatus": "active"
  }
]
```

If `mappedValuesFile` is omitted, only the grouped report is created.

## Path rules

Use bracket notation for every path segment:

```text
[catalog][products][details][name]
```

Do not use dot notation. Some YAML keys may contain dots as part of the key name.

If a path reaches a list and no numeric index is provided, the tool searches every item in the list.

Example:

```text
[catalog][products][details][name]
```

If `products` is a list, the tool checks all products.

To target a specific list item, use a numeric index:

```text
[catalog][products][0][details][name]
```

## Output files

Main YAML output:

```text
output.yaml
```

Grouped JSON report default name:

```text
grouped_removed_values.json
```

Mapped JSON report default suggested name, when enabled:

```text
mapped_removed_values.json
```

The grouped and mapped JSON report file names can be customized with `output.removedValuesFile` and `output.mappedValuesFile`. These fields can contain only a file name or a relative path such as `results/grouped_removed_values.json`.

## Grouping modes

The optional `groupBy` setting controls how the grouped JSON report groups removed values:

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
    "code": "[collection][entries][locations][bins][code]"
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

## Repository safety note

Do not commit real private YAML files, generated reports, credentials, tokens, environment-specific names, or internal configuration values to a public repository. Keep public examples generic.
