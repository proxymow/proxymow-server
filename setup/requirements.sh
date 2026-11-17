#!/bin/bash

# Global Variables
USER="pi"
VENV="/home/"$USER"/pxm-venv/"
echo "Virtual Environment: " $VENV
BIN=$VENV"bin/"
echo "Bin Path: " $BIN
PIP=$BIN"pip"
echo "Pip Path: " $PIP

read -s -p "Please enter the password for the pi user: " PASS
echo

# these may be required...
apt -y -q update
apt -y -q full-upgrade

apt -y -q install python3-numpy
apt -y -q install libmariadb-dev
apt install -y -q --no-install-recommends python3-picamera2
apt install -y -q libopenblas-dev
apt install -y python3-dev build-essential pkg-config
apt -y -q install libxml2-dev libxslt-dev
apt -y -q install python3-lxml
apt -y -q install python3-skimage
apt -y -q install python3-shapely
apt -y -q install git

echo "samba-common samba-common/workgroup string  WORKGROUP" | debconf-set-selections
echo "samba-common samba-common/dhcp boolean false" | debconf-set-selections
echo "samba-common samba-common/do_debconf boolean true" | debconf-set-selections
apt -y -q install samba samba-common-bin
(echo $PASS; echo $PASS) | smbpasswd -s -a $USER

# better option for windows
# install full python3-opencv

# create virtual environment with access to site packages
sudo -u $USER python -m venv --system-site-packages $VENV

# activate virtual environment
source $BIN/activate

# install into environment
sudo -u $USER $PIP install psutil
sudo -u $USER $PIP install mariadb
sudo -u $USER $PIP install cherrypy
sudo -u $USER $PIP install jinja2
sudo -u $USER $PIP install markdown
sudo -u $USER $PIP install bleak
sudo -u $USER $PIP install ping3
sudo -u $USER $PIP install opencv-python-headless

echo "Please Reboot, then start proxymow (in debug mode) with "$BIN"python /home/"$USER"/proxymow-server/proxymow.py -d"
