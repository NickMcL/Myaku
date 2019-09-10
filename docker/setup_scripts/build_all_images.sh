#!/bin/bash
# Builds the base layers for all Myaku docker images.

set -ev

cd "$(dirname "${BASH_SOURCE[0]}")"/../..

# Pull the latest prod images first so that their layers can be used if
# possible instead of rebuilding all of the layers for all images.
sudo docker pull friedrice2/myaku_crawler:latest
sudo docker pull friedrice2/myaku_rescore:latest
sudo docker pull friedrice2/myaku_web:latest
sudo docker pull friedrice2/myaku_nginx.reverseproxy:latest
sudo docker pull friedrice2/myaku_redis.first-page-cache:latest
sudo docker pull friedrice2/myaku_mongo.crawldb:latest
sudo docker pull friedrice2/mongobackup:latest

./build_image.sh crawler dev
./build_image.sh rescore dev
./build_image.sh web dev
./build_image.sh nginx.reverseproxy dev
./build_image.sh redis.first-page-cache dev
./build_image.sh mongo.crawldb dev
./build_image.sh mongobackup dev
./build_image.sh run-tests dev
