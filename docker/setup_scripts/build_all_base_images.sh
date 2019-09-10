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

sudo docker build \
    --cache-from friedrice2/myaku_crawler:latest \
    --target base \
    -f ./docker/myaku_crawler/Dockerfile.crawler \
    -t friedrice2/myaku_crawler:base \
    .
sudo docker build \
    --cache-from friedrice2/myaku_rescore:latest \
    --target base \
    -f ./docker/myaku_rescore/Dockerfile.rescore \
    -t friedrice2/myaku_rescore:base \
    .
sudo docker build \
    --cache-from friedrice2/myaku_web:latest \
    --target base \
    -f ./docker/myaku_web/Dockerfile.myakuweb \
    -t friedrice2/myaku_rescore:base \
    .
sudo docker build \
    --cache-from friedrice2/myaku_nginx.reverseproxy:latest \
    --target base \
    -f ./docker/myaku_nginx.reverseproxy/Dockerfile.nginx.reverseproxy \
    -t friedrice2/myaku_nginx.reverseproxy:base \
    .
sudo docker build \
    --cache-from friedrice2/myaku_redis.first-page-cache:latest \
    --target base \
    -f ./docker/myaku_redis.first-page-cache/Dockerfile.redis.first-page-cache \
    -t friedrice2/myaku_redis.first-page-cache:base \
    .
sudo docker build \
    --cache-from friedrice2/myaku_mongo.crawldb:latest \
    --target base \
    -f ./docker/myaku_mongo.crawldb/Dockerfile.mongo.crawldb \
    -t friedrice2/myaku_mongo.crawldb:base \
    .
sudo docker build \
    --cache-from friedrice2/mongobackup:latest \
    --target base \
    -f ./docker/mongobackup/Dockerfile.mongobackup \
    -t friedrice2/mongobackup:base \
    .
sudo docker build \
    -f ./docker/myaku_run-tests/Dockerfile.run-tests \
    -t friedrice2/myaku_run-tests:dev \
    .
