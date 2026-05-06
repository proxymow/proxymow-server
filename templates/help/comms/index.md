<h2 id="comms">Communications Feature</h2>

The *Communications* feature provides a read-only table of configured mowers.  
The table has columns for:

* Selected State
* Name
* Mower Type
* IP Address
* IP Port
* Ping Status
* Bluetooth Advertising Count
* Connected State

The time of the *Latest Scan* is also displayed. Scanning is only active when there is no mower selected.

You can *select* a mower by double-clicking a row of the table. If you select a UDP or virtual mower, then commands will be sent to the chosen ip address. If you select a Bluetooth Low Energy (BLE) mower, then the system will try to establish a bluetooth connection with the mower *advertising* under that name.
