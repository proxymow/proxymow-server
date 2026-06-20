#!/bin/bash

# Global Variables
USER='pi'
echo Please enter the password for the pi user...
read PASS

# these may be required...
sudo apt -y -q update
sudo apt -y -q full-upgrade

sudo apt -y -q install python3-numpy
sudo apt -y -q install python3-scipy
sudo apt -y -q install libmariadb-dev
sudo apt -y -q install python3-picamera2

echo "samba-common samba-common/workgroup string  WORKGROUP" | sudo debconf-set-selections
echo "samba-common samba-common/dhcp boolean false" | sudo debconf-set-selections
echo "samba-common samba-common/do_debconf boolean true" | sudo debconf-set-selections
sudo apt -y -q install samba samba-common-bin
(echo $PASS; echo $PASS) | sudo smbpasswd -s -a $USER

sudo apt -y -q install python3-skimage

# option for windows web-cam
# sudo apt -y -q install python3-opencv

# create virtual environment with access to site packages
python -m venv --system-site-packages /home/pi/pxm-venv/

# activate virtual environment
source /home/pi/pxm-venv/bin/activate

# install into environment
pip install mariadb
pip install cherrypy
pip install jinja2
pip install shapely
pip install markdown
pip install bleak
pip install ping3

echo 'Please Reboot, then start proxymow (in debug mode) with "/home/pi/pxm-venv/bin/python /home/pi/proxymow-server/proxymow.py -d"'