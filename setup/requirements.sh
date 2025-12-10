#!/bin/bash

# Global Variables
USER='pi'
echo Please enter the password for the pi user...
read PASS

# these may be required...
# sudo apt -y -q update
# sudo apt -y -q full-upgrade
sudo apt -y -q install python3-pip
sudo apt -y -q install python3-scipy
sudo apt -y -q install libmariadb-dev
sudo apt -y -q install python3-picamera2

echo "samba-common samba-common/workgroup string  WORKGROUP" | sudo debconf-set-selections
echo "samba-common samba-common/dhcp boolean false" | sudo debconf-set-selections
echo "samba-common samba-common/do_debconf boolean true" | sudo debconf-set-selections
sudo apt -y -q install samba samba-common-bin
(echo $PASS; echo $PASS) | sudo smbpasswd -s -a $USER
sudo apt -y -q install libjpeg-dev
sudo apt -y -q install libtiff5-dev
sudo apt -y -q install libxml2-dev libxslt-dev
sudo apt -y -q install python3-lxml
sudo apt -y -q install libgeos-dev
sudo apt -y -q install python3-skimage
# option for windows web-cam
# sudo apt -y -q install python3-opencv

sudo pip3 install mariadb --break-system-packages
sudo pip3 install cherrypy --break-system-packages
sudo pip3 install shapely==1.4.1 --break-system-packages
sudo pip3 install markdown --break-system-packages

sudo apt -y -q install python3-skimage

echo 'Please Reboot...'
