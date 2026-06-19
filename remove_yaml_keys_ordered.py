import sys
import json
import re
import os
import yaml
from copy import deepcopy


def parse_path(path: str) -> list[str]:
    """
    Converte caminhos no formato:
    [items][spec][http][match][uri][prefix]

    Em:
    ["items", "spec", "http", "match", "uri", "prefix"]

    Mantém chaves com ponto no nome, por exemplo:
    [meta.helm.sh/release-name]
    """
    parts = re.findall(r"\[([^\]]+)\]", path)

    if not parts:
        raise ValueError(f"Caminho inválido: {path}")

    return parts


def remove_by_path(data, path_parts: list[str], label: str, original_path: str) -> list[dict]:
    """
    Remove uma chave de uma estrutura YAML carregada em Python.

    Se encontrar uma lista no meio do caminho, aplica a remoção em todos os itens
    daquela lista. Retorna os valores removidos na ordem em que foram encontrados.
    """
    removed_values = []

    def walk(current_data, remaining_parts: list[str]):
        if current_data is None:
            return

        if isinstance(current_data, list):
            for item in current_data:
                walk(item, remaining_parts)
            return

        if not isinstance(current_data, dict):
            return

        current_key = remaining_parts[0]

        if len(remaining_parts) == 1:
            if current_key in current_data:
                removed_values.append({
                    "label": label,
                    "path": original_path,
                    "removedKey": current_key,
                    "removedValue": deepcopy(current_data[current_key])
                })
                del current_data[current_key]
            return

        if current_key in current_data:
            walk(current_data[current_key], remaining_parts[1:])

    walk(data, path_parts)
    return removed_values


def build_grouped_output(documents: list, parsed_keys: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Gera duas saídas:

    1) flat_removed_values:
       lista simples, mas agora na ordem do item do YAML.
       Exemplo: item 0 -> name, prefix; item 1 -> name, prefix.

    2) grouped_removed_values:
       lista agrupada por item da lista principal, por exemplo items[0], items[1].
    """
    flat_removed_values = []
    grouped_removed_values = []

    for document_index, document in enumerate(documents):
        if not isinstance(document, dict):
            continue

        processed_list_roots = set()

        for key_config in parsed_keys:
            parts = key_config["parts"]
            root_key = parts[0]

            is_path_inside_root_list = (
                len(parts) > 1
                and isinstance(document.get(root_key), list)
            )

            if is_path_inside_root_list:
                if root_key in processed_list_roots:
                    continue

                processed_list_roots.add(root_key)

                same_root_keys = [
                    item for item in parsed_keys
                    if len(item["parts"]) > 1 and item["parts"][0] == root_key
                ]

                for item_index, item_data in enumerate(document[root_key]):
                    group_removed_values = []

                    for same_root_key in same_root_keys:
                        relative_parts = same_root_key["parts"][1:]

                        removed_items = remove_by_path(
                            item_data,
                            relative_parts,
                            same_root_key["label"],
                            same_root_key["path"]
                        )

                        for removed_item in removed_items:
                            ordered_removed_item = {
                                "documentIndex": document_index,
                                "groupPath": f"[{root_key}]",
                                "itemIndex": item_index,
                                **removed_item
                            }
                            flat_removed_values.append(ordered_removed_item)
                            group_removed_values.append(removed_item)

                    if group_removed_values:
                        grouped_removed_values.append({
                            "documentIndex": document_index,
                            "groupPath": f"[{root_key}]",
                            "itemIndex": item_index,
                            "removedValues": group_removed_values
                        })

            else:
                removed_items = remove_by_path(
                    document,
                    parts,
                    key_config["label"],
                    key_config["path"]
                )

                for removed_item in removed_items:
                    ordered_removed_item = {
                        "documentIndex": document_index,
                        "groupPath": None,
                        "itemIndex": None,
                        **removed_item
                    }
                    flat_removed_values.append(ordered_removed_item)
                    grouped_removed_values.append(ordered_removed_item)

    return flat_removed_values, grouped_removed_values


def main():
    if len(sys.argv) < 4:
        print("Uso:")
        print("python remove_yaml_keys_ordered.py entrada.yaml chaves.json saida.yaml")
        sys.exit(1)

    yaml_input_file = sys.argv[1]
    json_keys_file = sys.argv[2]
    yaml_output_file = sys.argv[3]

    output_dir = os.path.dirname(os.path.abspath(yaml_output_file)) or "."
    ordered_removed_values_output_file = os.path.join(output_dir, "valores_removidos_ordenado.json")
    grouped_removed_values_output_file = os.path.join(output_dir, "valores_removidos_agrupado.json")

    with open(yaml_input_file, "r", encoding="utf-8") as file:
        documents = list(yaml.safe_load_all(file))

    with open(json_keys_file, "r", encoding="utf-8") as file:
        config = json.load(file)

    keys = config.get("keys", {})

    if not keys:
        raise ValueError("O arquivo JSON não possui a propriedade 'keys' ou ela está vazia.")

    parsed_keys = []

    for label, path in keys.items():
        parsed_keys.append({
            "label": label,
            "path": path,
            "parts": parse_path(path)
        })

    flat_removed_values, grouped_removed_values = build_grouped_output(documents, parsed_keys)

    with open(yaml_output_file, "w", encoding="utf-8") as file:
        if len(documents) > 1:
            yaml.safe_dump_all(
                documents,
                file,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False
            )
        else:
            yaml.safe_dump(
                documents[0],
                file,
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False
            )

    with open(ordered_removed_values_output_file, "w", encoding="utf-8") as file:
        json.dump(
            flat_removed_values,
            file,
            ensure_ascii=False,
            indent=2
        )

    with open(grouped_removed_values_output_file, "w", encoding="utf-8") as file:
        json.dump(
            grouped_removed_values,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"YAML gerado: {yaml_output_file}")
    print(f"Valores removidos ordenados: {ordered_removed_values_output_file}")
    print(f"Valores removidos agrupados: {grouped_removed_values_output_file}")
    print(f"Total de remoções: {len(flat_removed_values)}")


if __name__ == "__main__":
    main()
