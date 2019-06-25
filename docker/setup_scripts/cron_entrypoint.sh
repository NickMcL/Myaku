#!/bin/bash

set -e

# Write all env vars set by docker into an env file for cron to use.
declare -p | grep '^declare -x' > $ENV_FILE
echo "Setting cron environment to:"
cat $ENV_FILE
echo

# Swap in cron job schedules from env vars.
cron_schedule_var_names="$(env | cut -d "=" -f 1 | grep ".*CRON_SCHEDULE")"
if [ ! -n "$cron_schedule_var_names" ]; then
    echo "No environment variables ending with \"CRON_SCHEDULE\" found"
    exit 1
fi

for cron_schedule_var_name in $cron_schedule_var_names; do
    cron_schedule=${!cron_schedule_var_name}

    # Escape strings for use in a sed find replace
    cron_schedule_var_name_escaped="$(sed 's/[^^]/[&]/g' <<< \
        "$cron_schedule_var_name")"
    cron_schedule_escaped="$(sed 's/[\/&]/\\&/g' <<< "$cron_schedule")"

    sed -i -e "s/$cron_schedule_var_name_escaped/$cron_schedule_escaped/g" \
        $CRON_FILE
    echo -n "Successfully swaped \"$cron_schedule_var_name\" for "
    echo "\"$cron_schedule\" in $CRON_FILE"
done

# Cron file must end with an empty line to be valid.
echo >> $CRON_FILE

cron -f
