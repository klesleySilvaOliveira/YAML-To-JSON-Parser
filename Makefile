IMAGE_NAME ?= yaml-key-remover
IMAGE_TAG ?= latest
IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)

.PHONY: build run-example help

build:
	docker build -t $(IMAGE) .

run-example:
	docker run --rm --user "$$(id -u):$$(id -g)" -v "$$(pwd):/work" -w /work $(IMAGE) examples/sample.yaml examples/keys.json examples/output.yaml

help:
	docker run --rm $(IMAGE) --help
