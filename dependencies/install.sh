#! /bin/bash

GIT_PARENT_DIRECTORY="/home/nick/workspace/"
GIT_PROJECT_NAME="wikitrans-pootle"
GIT_LOCAL_DIRECTORY=$GIT_PARENT_DIRECTORY$GIT_PROJECT_NAME
GITHUB_BASE_URL="github.com/NickRuiz/"
GITHUB_PROJECT_URL="http://"$GITHUB_BASE_URL$GIT_PROJECT_NAME
GITHUB_READONLY_PROJECT="git://"$GITHUB_BASE_URL$GIT_PROJECT_NAME".git"

# Install git
sudo apt-get install git-core git-gui git-doc

# Install easy_install and pip
sudo apt-get install python-setuptools python-dev build-essential
sudo easy_install pip
sudo pip install --upgrade pip

# Install django
sudo pip install django

# User-interaction: fork the project from github
echo "1. Please create an account on github, if you have not already."
echo "http://www.github.com"
echo "2. You will need to follow the directions here to add a ssh key to github."
echo "http://help.github.com/linux-key-setup/"
echo "3. Create your own fork of the project listed below."
echo $GITHUB_PROJECT_URL
echo "4. Once you have your own fork, paste the Private URL here: "
read GIT_PRIVATE_URL
echo ""

# Automatically retrieve the project from github
echo "Navigating to "$GIT_PARENT_DIRECTORY
cd $GIT_PARENT_DIRECTORY
echo "Cloning project at "$GIT_PRIVATE_URL
git clone $GIT_PRIVATE_URL

echo "Navigating to "$GIT_PROJECT_NAME
cd $GIT_PROJECT_NAME
echo "Add a git upstream to "$GITHUB_READONLY_PROJECT
git remote add upstream $GITHUB_READONLY_PROJECT
echo "Fetch the data"
git fetch upstream

echo "Setting directory to "$GIT_LOCAL_DIRECTORY"/Pootle"
cd $GIT_LOCAL_DIRECTORY/Pootle

# Install dependencies from requirements.txt
sudo apt-get install libyaml-0-2
sudo pip install -I pyyaml
sudo pip install http://dist.repoze.org/PIL-1.1.6.tar.gz

sudo apt-get install libxml2-dev
sudo apt-get install libxslt-dev
sudo pip install lxml

sudo apt-get install libevent-dev
sudo pip install -I -r requirements.txt

# Configure nltk
python nltk_config.py

GIT_PARENT_DIRECTORY="/home/nick/workspace/"
GIT_PROJECT_NAME="wikitrans-pootle"
GIT_LOCAL_DIRECTORY=$GIT_PARENT_DIRECTORY$GIT_PROJECT_NAME

echo "Setting directory to "$GIT_LOCAL_DIRECTORY
cd $GIT_LOCAL_DIRECTORY

# Build Pootle
echo "Building and installing Pootle..."
sudo python setup.py build install

echo "You will also need to download Google Protocol Buffers to work with MT Server Land and XML-RPC."
echo "http://code.google.com/p/protobuf/"
echo "Done."

