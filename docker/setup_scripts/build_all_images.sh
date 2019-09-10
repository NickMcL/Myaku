#!/bin/bash
# Builds the base layers for all Myaku docker images.

set -ev

cd "$(dirname "${BASH_SOURCE[0]}")"/../..

./build_image.sh crawler dev
./build_image.sh rescore dev
./build_image.sh web dev
./build_image.sh nginx.reverseproxy dev
./build_image.sh redis.first-page-cache dev
./build_image.sh mongo.crawldb dev
./build_image.sh mongobackup dev
./build_image.sh run-tests dev
