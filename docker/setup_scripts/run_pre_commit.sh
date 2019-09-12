#!/bin/bash

set -ev

# Set pythonpath so that both the myaku and myakuweb packages can be found by
# the django-stubs plugin for the mypy pre-commit checker.
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
export PYTHONPATH="$PYTHONPATH:$(pwd):$(pwd)/myakuweb"

pre-commit run --all-files
