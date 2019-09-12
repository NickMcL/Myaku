#!/bin/bash

set -ev

pip install pre-commit==1.18.3

# Set pythonpath so that both the myaku and myakuweb packages can be found by
# the django-stubs plugin for the mypy pre-commit checker.
project_root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PYTHONPATH="$PYTHONPATH:$project_root_dir:$project_root_dir/myakuweb"
