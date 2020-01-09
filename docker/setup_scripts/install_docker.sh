#!/bin/bash
# Bootstrap script to install the current docker version being used for the
# project  on an Ubuntu instance.

set -ev

sudo apt-get remove -y docker docker-engine docker.io containerd runc

sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent \
    software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

sudo apt-get update
sudo apt-get -y install \
    "docker-ce=5:19.03.5~3-0~ubuntu-$(lsb_release -cs)" \
    "docker-ce-cli=5:19.03.5~3-0~ubuntu-$(lsb_release -cs)" \
    "containerd.io=1.2.10-3"
