#! /bin/bash

# Install easy_install and pip
sudo apt-get install python-setuptools python-dev build-essential
sudo easy_install pip
sudo pip install --upgrade pip

# Install django
sudo pip install django

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

# Build Pootle
# echo "Building and installing Pootle..."
# sudo python setup.py build install

echo "You may also need to download Google Protocol Buffers to work with MT Server Land and XML-RPC."
echo "http://code.google.com/p/protobuf/"
echo "Done."

