#!/bin/bash
# Bootstrap script to install both nodejs and the node module dependencies for
# the MyakuWeb React app.

set -ev

sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent
curl -sL https://deb.nodesource.com/setup_13.x | sudo -E bash -
sudo apt-get install -y nodejs=13.1.0-1nodesource1

cd "$(dirname "${BASH_SOURCE[0]}")/../../myakuweb-clientapp"
npm install
