# YAML Key Remover

A small Python command-line tool that removes configured keys from YAML files and exports the removed values to a grouped JSON report.

The tool uses bracket paths such as `[catalog][products][details][name]`. This avoids ambiguity when YAML keys contain dots, slashes, spaces, or other special characters.

## Features

- Removes configured dictionary keys from YAML documents.
- Supports YAML files with one or many documents.
- Traverses lists automatically when no numeric index is provided.
- Supports nested lists.
- Supports explicit list indexes when only one position should be targeted.
- Keeps removed lists as JSON arrays in the report.
- Groups removed values by source location.
- Uses only generic examples and does not depend on any specific YAML platform or schema.

## Getting the project

Clone the repository from GitHub using SSH and enter the project directory:

```bash
git clone git@github.com:klesleySilvaOliveira/YAML-To-JSON-Parser.git
cd YAML-To-JSON-Parser
```

If the repository is private, make sure the GitHub account configured on the machine has access to it and that SSH authentication is properly configured.

If you are using a fork or a different remote, replace the repository URL with the correct one before running `git clone`.

After cloning, run the example with Docker:

```bash
docker build -t yaml-key-remover .

docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd):/work" \
  -w /work \
  yaml-key-remover \
  examples/sample.yaml \
  examples/keys.json \
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

## Local usage

```bash
python yaml_key_remover.py input.yaml keys.json output.yaml
```

The command creates:

- `output.yaml`: the YAML file after the configured keys are removed.
- `grouped_removed_values.json`: a JSON report with the removed values grouped by their source location.

## Docker usage

Docker lets you run the tool without installing Python dependencies on your machine.

Build the image:

```bash
docker build -t yaml-key-remover .
```

Run the example files stored in the `examples` directory:

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

Run with your own files stored inside the project directory:

```bash
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "$(pwd):/work" \
  -w /work \
  yaml-key-remover \
  input.yaml \
  keys.json \
  output.yaml
```

The `-w /work` option sets the container working directory to `/work`. This allows you to pass relative paths such as `examples/sample.yaml` instead of `/work/examples/sample.yaml`.

The `--user "$(id -u):$(id -g)"` option helps avoid root-owned output files on Linux.

### Docker file path rules

When using Docker, the container can only access files from directories that were mounted with `-v`. In the commands above, this part:

```bash
-v "$(pwd):/work"
```

means that only the current host directory is available inside the container as `/work`.

If your YAML file is outside the project directory, for example in your `Downloads` folder, passing the host path directly will not work unless that folder is also mounted. You have two common options.

Option 1: copy the YAML file into the project directory and run the command normally.

Option 2: mount the external folder too. Example:

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

In this example, the input YAML is read from the mounted `Downloads` folder, while the configuration file and output files remain in the project directory.

## Docker Compose usage

Build the image:

```bash
docker compose build
```

Run the example files stored in the `examples` directory:

```bash
UID=$(id -u) GID=$(id -g) docker compose run --rm yaml-key-remover \
  examples/sample.yaml \
  examples/keys.json \
  examples/output.yaml
```

Run with your own files stored inside the project directory:

```bash
UID=$(id -u) GID=$(id -g) docker compose run --rm yaml-key-remover \
  input.yaml \
  keys.json \
  output.yaml
```

## Makefile shortcuts

Build the image:

```bash
make build
```

Run the example:

```bash
make run-example
```

Show help:

```bash
make help
```

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

If traversal reaches a list and the path does not provide an index, the tool searches every list element automatically.

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

## Repository safety note

Do not commit real private YAML files, generated reports, credentials, tokens, environment-specific names, or internal configuration values to a public repository. Keep public examples generic.
