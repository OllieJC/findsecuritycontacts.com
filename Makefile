SHELL := /usr/bin/env bash
DEFAULT_GOAL := test
PHONY = clean
# ONESHELL:

test:
	echo "Not implemented"

build-lambda:
	mkdir -p .build/
	mkdir -p .target/assets/
	mkdir -p .target/templates/

	cp -r ./assets .target/
	cp -r ./templates .target/
	cp ./*.py .target/

	cd .target/ && zip -FSqr ../.build/lambda.zip .

build-lambda-full: build-dependencies build-lambda

build-dependencies:
	python3.8 -m pip install -r requirements.txt -t .target/ --upgrade

clean:
	rm -rf .build || echo ".build doesn't exist"
	rm -rf .target || echo ".target doesn't exist"
