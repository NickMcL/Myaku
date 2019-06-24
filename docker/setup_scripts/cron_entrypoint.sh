#!/bin/bash

# Write all env vars set by docker into an env file for cron to use
declare -p | grep '^declare -x' > $ENV_FILE

cron -f
