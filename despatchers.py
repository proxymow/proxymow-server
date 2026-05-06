import sys
import json
from time import time
import socket


class Despatcher(object):
    '''
        Abstract parent class that implements shared behaviour
    '''

    _RSSI_THRESHOLDS = [0, -30, -67, -70, -80, -90, -999]
    _RSSI_CATEGORIES = ['Unbelievable', 'Amazing',
                   'Very Good', 'O.K.', 'Not Good', 'Unusable']

    def __init__(self, host, excl_lock):
        '''
            Constructor
        '''
        self.host = host
        self.logger = host.comms_logger
        self.despatch_lock = excl_lock
        self.reset_stats()
        
    def reset_stats(self):
        self.telemetry_recv_count = 0
        self.telemetry_succ_count = 0
        self.telemetry_mean_elapsed = 0
        self.async_recv_count = 0
        self.async_succ_count = 0
        self.async_mean_elapsed = 0
        self.sequential_failure_count = 0        
            
    def fetch_telemetry(self):
        start_time = time()
        resp = self.despatch('>get_telemetry()', True) # await response
        elapsed_time = time() - start_time
        msg = 'get telemetry resp: {} in {:.3f}secs'.format(resp, elapsed_time)
        self.logger.info(msg)
        sum_elapsed = (self.telemetry_mean_elapsed * self.telemetry_recv_count) + elapsed_time
        self.telemetry_recv_count += 1
        self.telemetry_mean_elapsed = sum_elapsed / self.telemetry_recv_count
        if self.is_valid(resp):
            tel_dict = json.loads(resp)
            self.telemetry_succ_count += 1
            self.sequential_failure_count = 0
        else:
            msg = 'Invalid Telemetry Data: {}'.format(resp)
            self.logger.error(msg)
            tel_dict = None
            self.sequential_failure_count += 1
            
        if tel_dict is not None:
            try:
                # analogue sensors
                # unpack raw values and match to names/factors if available
                channel_names = self.host.config['mower.sens_name_list'].split(',')
                channel_factors = self.host.config['mower.sens_factor_list'].split(',')
                sensors = {}
                for i, raw_adc in enumerate(tel_dict['analogs']):
                    try:
                        ch_name = channel_names[i].strip()
                        if ch_name == '':
                            raise Exception()
                    except:
                        ch_name = f'Channel {i+1}'
                    try:
                        ch_factor = channel_factors[i]
                        if ch_factor.strip() == '':
                            raise Exception()
                    except:
                        ch_factor = 1.0
                    sensors[ch_name] = round(raw_adc * float(ch_factor), 3)
                    
                tel_dict['sensors'] = sensors
                self.apply_wifi(tel_dict)
                # add last-fetch time here...
                tel_dict['last-fetch'] = time()
            except Exception as e1:
                err_line = sys.exc_info()[-1].tb_lineno
                self.logger.error('Error post processing telemetry: {}'.format(
                    e1) + ' on line ' + str(err_line))
                tel_dict['wifi_quality'] = 0
        else:
            self.logger.warn('utilities fetch_telemetry - Mower Offline!')

        return tel_dict
        
    def fetch_pose(self):
        start_time = time()
        resp = self.despatch('>get_pose()', True)
        elapsed_time = time() - start_time
        msg = 'pose resp: {} in {:.3f}secs'.format(resp, elapsed_time)
        self.logger.debug(msg)
        if self.is_valid(resp):
            pose_json = json.loads(resp)
        else:
            msg = 'Invalid Pose Data: {}'.format(resp)
            self.logger.warn(msg)
            pose_json = None
        return pose_json
    
    def despatch(self, cmd, await_response=True):
        resp = None
        res = self.despatch_lock is None or self.despatch_lock.acquire(timeout=self.timeout_secs * 2) # blocks
        if res:
            try:
                msg = 'despatch lock acquired...'
                self.logger.debug(msg)
                try:
                    start_time = time()
                    _bytes_sent = self.send(cmd)
                    if await_response:
                        resp = self.recv(self.timeout_secs)
                        elapsed_time = time() - start_time
                    else:
                        resp = None
                        elapsed_time = 0
                        self.recv(self.timeout_secs) # flush
            
                    msg = '{} resp: {} in {:.3f}secs'.format(cmd, resp, elapsed_time)
                    self.logger.info(msg)
                    if await_response and cmd is not None and cmd[0] != '>':
                        # full duplex async only
                        sum_elapsed = (self.async_mean_elapsed * self.async_recv_count) + elapsed_time
                        self.async_recv_count += 1
                        self.async_mean_elapsed = sum_elapsed / self.async_recv_count
                        if resp is not None:
                            self.async_succ_count += 1
                            msg = 'Resetting sequential failure count'
                            self.logger.info(msg)
                            self.sequential_failure_count = 0
                        else:
                            msg = 'Invalid Data: {} from {}'.format(resp, cmd)
                            self.logger.error(msg)
                            self.sequential_failure_count += 1
                except Exception as err:
                    err_line = sys.exc_info()[-1].tb_lineno
                    msg = 'despatch error: ' + str(err) + ' on line: ' + str(err_line)
                    self.logger.error(msg)
            finally:
                if self.despatch_lock is not None:
                    self.despatch_lock.release()
                    msg = 'despatch lock released'
                    self.logger.debug(msg)
        else:
            # lock timeout - shouldn't happen!
            msg = 'despatch lock timeout'
            self.logger.warning(msg)
        
        return resp
    
    def is_valid(self, resp_string):
        try:
            if resp_string is not None:
                json.loads(resp_string)
                result = True
            else:
                result = False
        except json.JSONDecodeError:
            result = False
        return result
    
    def close(self):
        # use for tidying up - by default does nothing
        msg = 'Despatcher closing'
        self.logger.debug(msg)
        
    def connection(self):
        # provide an identification string
        pass
    
    def rssi_category(self, rssi):
        try:
            rssi_index = next(i for i in range(len(self._RSSI_THRESHOLDS) - 1)
                              if self._RSSI_THRESHOLDS[i] >= rssi >= self._RSSI_THRESHOLDS[i + 1])
            cat = self._RSSI_CATEGORIES[rssi_index]
        except Exception:
            cat = self._RSSI_CATEGORIES[-1]
        return cat

    
    def __repr__(self):
        result = self.connection + '\n'
        result += '=' * len(result[:-1])
        result += '\ntelem receive count: {}\n'.format(self.telemetry_recv_count)
        result += 'telem success count: {}\n'.format(self.telemetry_succ_count)
        result += 'telem mean elapsed: {:.3f}secs\n'.format(self.telemetry_mean_elapsed)
        result += 'async receive count: {}\n'.format(self.async_recv_count)
        result += 'async success count: {}\n'.format(self.async_succ_count)
        result += 'async mean elapsed: {:.3f}secs\n'.format(self.async_mean_elapsed)
        result += 'quality: {:.0f}%\n'.format(
            100 * (self.telemetry_succ_count + self.async_succ_count) / 
            (self.telemetry_recv_count + self.async_recv_count + 0.000001)
        )
        result += 'sequential failure count: {}'.format(self.sequential_failure_count)
        return result
        
class UDPDespatcher(Despatcher):
    '''
        Concrete class that implements UDP comms
    '''

    def __init__(self, host, ip_addr, port, timeout_secs, excl_lock=None):
        '''
            Constructor
        '''
        super().__init__(host, excl_lock)
        # create a UDP Socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock_addr = (ip_addr, port)
        self.timeout_secs = timeout_secs
        msg = 'UDP Despatcher initialised'
        self.logger.debug(msg)
        
    def send(self, cmd):
        msg = 'UDP Despatcher sending {}'.format(cmd)
        self.logger.info(msg)
        txmsg = bytes(cmd + '\r\n', 'utf8')
        bytes_sent = self.udp_socket.sendto(txmsg, self.sock_addr)
        return bytes_sent
    
    def recv(self, timeout):
        msg = 'UDP Despatcher receiving...'
        self.logger.debug(msg)
        self.udp_socket.settimeout(timeout)
        try:
            data, _addr = self.udp_socket.recvfrom(1024)
            resp = data.decode('utf-8')
        except socket.timeout:
            resp = None
        return resp

    def close(self):
        # use for tidying up
        msg = 'UDP Despatcher closing...'
        self.logger.debug(msg)
        try:
            self.udp_socket.close()
        except Exception as e:
            msg = 'error closing UDP Despatcher: {}'.format(e)
            self.logger.error(msg)
            
    def apply_wifi(self, tel_dict):
        wifi_rssi = tel_dict['rssi'] if 'rssi' in tel_dict else None  # dbm
        if wifi_rssi is not None:
            wifi_quality = self.rssi_category(wifi_rssi)
            tel_dict['wifi_quality'] = wifi_quality

    @property
    def connection(self):
        # provide an identification string
        device = self.sock_addr
        result = '{}({})'.format(self.__class__.__name__, device)
        return result
    
class BLEDespatcher(Despatcher):
    '''
        Concrete class that implements Bluetooth comms
    '''

    def __init__(self, host, timeout_secs, excl_lock=None):
        '''
            Constructor
        '''
        super().__init__(host, excl_lock)
        self.blue_proxy = host.blue_proxy
        self.timeout_secs = timeout_secs
        msg = 'BLE Despatcher initialised'
        self.logger.debug(msg)
        
    def send(self, cmd):
        msg = 'BLE Despatcher sending {}'.format(cmd)
        self.logger.info(msg)
        self.blue_proxy.send(cmd)
        return len(cmd)
    
    def recv(self, timeout):
        msg = 'BLE Despatcher receiving...'
        self.logger.debug(msg)
        data = self.blue_proxy.recv(timeout)
        return data
    
    def close(self):
        # use for tidying up
        msg = 'BLE Despatcher closing...'
        self.logger.debug(msg)
        self.blue_proxy.disconnect()
        
    def apply_wifi(self, tel_dict):
        # rssi unavailable on bluetooth
        tel_dict['rssi'] = 0 # so icon goes 4-bar green
        tel_dict['wifi_quality'] = 'unavailable'

    @property
    def connection(self):
        # provide an identification string
        if self.blue_proxy.is_connected():
            device = self.blue_proxy.device_name
        else:
            device = 'None'
        result = '{}({})'.format(self.__class__.__name__, device)
        return result
    