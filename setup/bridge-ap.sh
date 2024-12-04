sudo nmcli connection add type bridge con-name 'Bridge' ifname bridge0
sudo nmcli connection add type ethernet slave-type bridge \
    con-name 'Ethernet' ifname eth0 master bridge0

sudo nmcli connection add con-name 'Hotspot' \
   ifname wlan0 type wifi slave-type bridge master bridge0 \
   wifi.mode ap wifi.ssid 'ProxymowAP-0000x' wifi-sec.key-mgmt wpa-psk \
   wifi-sec.proto rsn wifi-sec.pairwise ccmp \
   wifi-sec.psk '*******'

sudo nmcli connection up Bridge
sudo nmcli connection up Hotspot
