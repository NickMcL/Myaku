#!/bin/bash
# Builds the test prod images for all Myaku docker services.
# Used to set up testing environments like Travis CI.

set -ev

cd "$(dirname "${BASH_SOURCE[0]}")"/../..

# Pull the latest prod images first so that their layers can be used if
# possible instead of rebuilding all of the layers for all images.
sudo docker pull friedrice2/myaku_crawler:latest
sudo docker pull friedrice2/myaku_rescore:latest
sudo docker pull friedrice2/myaku_web:latest
sudo docker pull friedrice2/myaku_nginx.reverseproxy:latest
sudo docker pull friedrice2/myaku_redis.first-page-cache:latest
# sudo docker pull friedrice2/myaku_mongo.crawldb:latest
sudo docker pull friedrice2/myaku_run-tests:latest
sudo docker pull friedrice2/mongobackup:latest

sudo docker build \
    --cache-from friedrice2/myaku_crawler:latest \
    --target prod \
    -f ./docker/myaku_crawler/Dockerfile.crawler \
    -t friedrice2/myaku_crawler:test \
    .
sudo docker build \
    --cache-from friedrice2/myaku_rescore:latest \
    --target prod \
    -f ./docker/myaku_rescore/Dockerfile.rescore \
    -t friedrice2/myaku_rescore:test \
    .
sudo docker build \
    --cache-from friedrice2/myaku_web:latest \
    --target prod \
    -f ./docker/myaku_web/Dockerfile.myakuweb \
    -t friedrice2/myaku_web:test \
    .
sudo docker build \
    --cache-from friedrice2/myaku_nginx.reverseproxy:latest \
    --target prod \
    -f ./docker/myaku_nginx.reverseproxy/Dockerfile.nginx.reverseproxy \
    -t friedrice2/myaku_nginx.reverseproxy:test \
    .
sudo docker build \
    --cache-from friedrice2/myaku_redis.first-page-cache:latest \
    --target prod \
    -f ./docker/myaku_redis.first-page-cache/Dockerfile.redis.first-page-cache \
    -t friedrice2/myaku_redis.first-page-cache:test \
    .
sudo docker build \
    --target prod \
    -f ./docker/myaku_mongo.crawldb/Dockerfile.mongo.crawldb \
    -t friedrice2/myaku_mongo.crawldb:test \
    .
sudo docker build \
    --cache-from friedrice2/mongobackup:latest \
    --target prod \
    -f ./docker/mongobackup/Dockerfile.mongobackup \
    -t friedrice2/mongobackup:test \
    .
sudo docker build \
    --cache-from friedrice2/myaku_run-tests:latest \
    -f ./docker/myaku_run-tests/Dockerfile.run-tests \
    -t friedrice2/myaku_run-tests:dev \
    .
