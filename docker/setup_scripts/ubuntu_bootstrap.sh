#!/bin/bash
# Bootstrap script to install docker on a new Ubuntu server instance

sudo apt-get remove docker docker-engine docker.io containerd runc

sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent \
    software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

sudo apt-get update
sudo apt-get -y install docker-ce docker-ce-cli containerd.io

sudo usermod -a -G docker $USER

# Convenience functions for checking myaku logs
~/.bashrc << EOF
tmlv()
{
    sudo tail -f /var/lib/docker/volumes/myaku_dev_\$1_log/_data/\$2
}

tpmlv()
{
    sudo tail -f /var/lib/docker/volumes/myaku_\$1_log/_data/\$2
}

lmlv()
{
    sudo less /var/lib/docker/volumes/myaku_dev_\$1_log/_data/\$2
}

lpmlv()
{
    sudo less /var/lib/docker/volumes/myaku_\$1_log/_data/\$2
}
EOF
source ~/.bashrc
