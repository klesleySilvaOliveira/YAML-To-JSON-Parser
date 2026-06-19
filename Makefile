IMAGE_NAME ?= yaml-key-remover
IMAGE_TAG ?= latest
IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: build run-example run-example-mapped map-example help

build:
	docker build -t $(IMAGE) .

run-example:
	docker run --rm --user "$$(id -u):$$(id -g)" -v "$$(pwd):/work" -w /work $(IMAGE) examples/sample.yaml examples/keys.json examples/output.yaml

run-example-mapped:
	docker run --rm --user "$$(id -u):$$(id -g)" -v "$$(pwd):/work" -w /work $(IMAGE) examples/sample.yaml examples/keys_with_mapped_output.json examples/output.yaml

map-example:
	docker run --rm --user "$$(id -u):$$(id -g)" -v "$$(pwd):/work" -w /work --entrypoint python $(IMAGE) /app/removed_values_mapper.py examples/grouped_removed_values.json examples/mapped_removed_values_standalone.json

help:
	docker run --rm $(IMAGE) --help
