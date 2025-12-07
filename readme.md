# Prowymow Automated Robot Lawn Mower (Server)

## What the project does
Proxymow is a robotic lawn mower system that uses computer vision to locate and guide the mower. This repository contains the source code for the server. The  sister repository [Proxymow Mower](https://github.com/proxymow/proxymow-mower) contains the source code for the mower device.

## Why the project is useful
Proxymow differs from many robotic mowers:
* Does not rely on vulnerable boundary wires
* Does not use GPS or Bollards
* Does not need to be taught a route, supports plug-in mowing patterns
* Employs very low cost technology: Raspberry Pi, NodeMCU, RPi Pico, ESP32

## Getting started
Use Raspberry Pi Imager to write the trixie-proxymow-shrunk.img.xz file to an SD Card (min 16GB).
The image file is an asset bundled with the release on GitHub. 
The login details are pi/raspberry which you should change, and SSH is enabled.
or
Start with a fresh install of Raspberry Pi OS Lite (32-bit).
Clone or Download the repo.

Ensure all pre-requisite software is installed...
```
cd proxymow-server/setup 
sudo chmod +x requirements.sh
./requirements.sh
```
you will be prompted for your pi user password.

When script has finished (20mins?/coffee) reboot pi...
```
sudo reboot
```
Change directory to the installation directory and start server...
```
cd proxymow-server
python proxymow.py  
```
Browse to displayed url.

## Getting help
Read the detailed [documentation](https://proxymow.co.uk).

## Who maintains and contributes to the project
info@proxymow.co.uk
