from bleak import BleakClient, BleakScanner, BleakGATTCharacteristic
import asyncio
import pprint
from threading import Lock

class BlueProxy():
    
    def __init__(self, logger=None):
        
        # nordic uuids
        self._NUS_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
        self._BLE_TX_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e' # RX on server
        self._BLE_RX_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e' # TX on server

        try:
            self.notify_queue = asyncio.Queue(maxsize=1)
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            BleakGATTCharacteristic.max_write_without_response_size = 255 

            # force check for bluetooth adaptor...
            self.loop.run_until_complete(self.async_find_all_devices(0))
        except Exception as e:
            raise Exception('Unable to initialise BlueProxy: ' + str(e))
        
        self.return_adv = True
        self.devices = []
        self.services = []
        self.client = None
        self.device_name = None
        self.logger = logger
        self.lock = Lock()
        self.lock_timeout = 15 # seconds
        self.logger.info('BlueProxy object initialised')
        

    def scan(self, scan_timeout_secs=10):
        self.logger.info('scanning for devices')
        lckd = self.lock.acquire(timeout=self.lock_timeout)
        if lckd:
            try:
                devices = self.loop.run_until_complete(self.async_find_all_devices(scan_timeout_secs, self.return_adv))
            finally:
                self.lock.release()
        if self.return_adv:
            self.devices = [d[0] for d in list(devices.values())]
        else:
            self.devices = devices
        
    def connect(self, device_name=None):
        self.logger.info('connecting from available devices {}...'.format(self.devices))
        filtered_devices = [d for d in self.devices if d.name == device_name]
        self.available = (len(filtered_devices) == 1)
        if self.available:
            lckd = self.lock.acquire(timeout=self.lock_timeout)
            if lckd:
                try:
                    self.device = filtered_devices[0]
                    self.logger.info('connecting to available device {} {}...'.format(self.device.name, self.device.address))
                    self.client = self.loop.run_until_complete(self.async_connect(self.device.address))
                    self.logger.info('connected to device {}'.format(device_name))
                    self.device_name = device_name
                except Exception as bdnfe:
                    self.logger.error('available device {} did not connect: {}'.format(device_name, bdnfe))
                    self.client = None
                finally:
                    self.lock.release()
        else:
            self.logger.warn('unavailable device {}'.format(device_name))
            
    def is_connected(self):
        return self.client is not None

    def list_ctics(self):
        self.logger.info('getting characteristics...')
        self.services = self.client.services
        
    def notify_callback(self, _sender, data):
        self.logger.debug('callback response length: {}'.format(len(data)))
        self.logger.debug('callback response: {}'.format(data))
        resp = str(data.decode("utf-8"))
        self.notify_queue.put_nowait(resp)
  
    def register_notify(self):
        self.logger.info('registering notification on {}'.format(self._BLE_RX_UUID))
        lckd = self.lock.acquire(timeout=self.lock_timeout)
        if lckd:
            try:
                self.loop.run_until_complete(self.async_subscribe(self.client, self.notify_callback))
            finally:
                self.lock.release()
        
    def cancel_notify(self):
        self.logger.info('cancelling notification on {}'.format(self._BLE_RX_UUID))
        lckd = self.lock.acquire(timeout=self.lock_timeout)
        if lckd:
            try:
                self.loop.run_until_complete(self.async_unsubscribe(self.client))
            finally:
                self.lock.release()
        
    def _despatch(self, cmd, timeout_secs=5):
        try:
            self.send(cmd)
            resp = self.recv(timeout_secs)
        except Exception as e:
            self.logger.warn('unable to despatch: {}'.format(e))
        return resp

    def send(self, cmd):
        req = cmd.encode("utf-8")
        lckd = self.lock.acquire(timeout=self.lock_timeout)
        if lckd:
            try:
                if self.is_connected():
                    # clear queue
                    self.notify_queue._queue.clear()
                    self.logger.debug('writing to {}...'.format(self._BLE_TX_UUID))
                    self.loop.run_until_complete(self.async_write(self.client, self._BLE_TX_UUID, req))
                else:
                    self.logger.warn('unable to despatch to unconnected client')
            except Exception as e:
                self.logger.warn('unable to send: {}'.format(e))

    def recv(self, timeout_secs=5):
        resp = None
                
        try:
            # block awaiting response
            resp = self.loop.run_until_complete(
                asyncio.wait_for(self.notify_queue.get(), timeout_secs)
            )
        except Exception as e:
            self.logger.warn('unable to recv: {}'.format(e))
        finally:
            self.lock.release()
    
        return resp
    
    def disconnect(self):
        self.logger.info('disconnecting from {}'.format(self.client))
        if self.client is not None:
            lckd = self.lock.acquire(timeout=self.lock_timeout)
            if lckd:
                self.logger.debug('disconnecting has lock')
                try:
                    self.loop.run_until_complete(self.async_disconnect(self.client))
                except Exception as e:
                    self.logger.error('error disconnecting: {}'.format(e))                
                finally:
                    self.client = None
                    self.device_name = None
                    self.logger.debug('disconnecting releasing lock...')
                    self.lock.release()
        
    async def async_find_all_devices(self, scan_timeout_secs=10, return_adv=False):
        return await BleakScanner.discover(timeout=scan_timeout_secs, return_adv=return_adv)
                
    async def async_connect(self, address):
        # create client
        client = BleakClient(address)
        # explicit connect
        await client.connect()
        return client

    async def async_subscribe(self, client, callback):
        # subscribe to notifications
        await client.start_notify(self._BLE_RX_UUID, callback)
    
    async def async_unsubscribe(self, client):
        # subscribe to notifications
        await client.stop_notify(self._BLE_RX_UUID)

    async def async_write(self, client, uuid, req):
        await client.write_gatt_char(uuid, req)
    
    async def async_disconnect(self, client):
        # explicit disconnect
        await client.disconnect()
        
    def __repr__(self):
        result = '\nBlueProxy\n'
        result += '=========\n'
        result += 'Devices: ' + pprint.pformat(self.devices) + '\n'
        result += 'Client: ' + str(self.client) + '\n'
        result += 'Mtu: ' + str(self.client.mtu_size) if self.client is not None else ''
        result += pprint.pformat(
            [
                (s.uuid, s.description, [(c.properties, c.uuid) 
                    for c in s.characteristics]
                ) 
                    for s in self.services 
                        if s.uuid.lower() == self._NUS_UUID.lower()
            ]
        ) + '\n'
        return result