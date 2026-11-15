#!/bin/bash

# Global Variables
USER='pi'
read -s -p "Please enter the password for the pi user: " PASS

# these may be required...
sudo apt -y -q update
sudo apt -y -q full-upgrade

sudo apt -y -q install python3-numpy
sudo apt -y -q install libmariadb-dev
sudo apt install -y -q --no-install-recommends python3-picamera2
sudo apt install -y -q libopenblas-dev
sudo apt install -y python3-dev build-essential pkg-config
sudo apt -y -q install libxml2-dev libxslt-dev
sudo apt -y -q install python3-lxml
sudo apt -y -q install python3-skimage
sudo apt -y -q install python3-shapely
sudo apt -y -q install git

echo "samba-common samba-common/workgroup string  WORKGROUP" | sudo debconf-set-selections
echo "samba-common samba-common/dhcp boolean false" | sudo debconf-set-selections
echo "samba-common samba-common/do_debconf boolean true" | sudo debconf-set-selections
sudo apt -y -q install samba samba-common-bin
(echo $PASS; echo $PASS) | sudo smbpasswd -s -a $USER

# better option for windows
# install full python3-opencv

# create virtual environment with access to site packages
python -m venv --system-site-packages /home/pi/pxm-venv/

# activate virtual environment
source /home/pi/pxm-venv/bin/activate

# install into environment
pip install psutil
pip install mariadb
pip install cherrypy
pip install jinja2
pip install markdown
pip install bleak
pip install ping3
pip install opencv-python-headless

echo 'Please Reboot, then start proxymow (in debug mode) with "/home/pi/pxm-venv/bin/python /home/pi/proxymow-server/proxymow.py -d"'