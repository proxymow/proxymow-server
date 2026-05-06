from time import sleep, strftime
import sys
from threading import Lock

from datatable import DataTable
from dupe_key_dict import DupeKeyDict
from utilities import ping_server
from despatchers import UDPDespatcher, BLEDespatcher

class Scanner(object):
    '''
        handles background scanning for mowers
    '''

    def __init__(self, host):
        '''
            Constructor
        '''
        self.host = host
        self.config = host.config
        self.col_names = ['selected', 'name', 'type', 'ip', 'port', 'ping', 'advertising', 'connected']
        self.col_dtypes = [bool, str, str, str, int, bool, int, bool]
        self.datatable = DataTable(self.col_names, self.col_dtypes)
        self.prime(self.config)
        self.last_scan = ''
        self.bt_avail = ('blue_proxy' in vars(self.host) and 
                         self.host.blue_proxy is not None)

    def prime(self, config):
        for mower_element in config.cfg_root.findall('.//mower'):
            self.update(mower_element, {})

    def update(self, mower_element, mower_row):
        mower_key = mower_element.attrib['name']
        mower_row['name'] = mower_key
        identity_element = mower_element.find('identity')
        for mower_att_key in identity_element.attrib:
            try:
                col_index = self.col_names.index(mower_att_key)
                dtype = self.col_dtypes[col_index]
                attr_data = dtype(identity_element.attrib[mower_att_key])
                if mower_att_key in mower_row:
                    cell_data = mower_row[mower_att_key]
                elif dtype is bool:
                    cell_data = False
                elif dtype in [int, float]:
                    cell_data = -1
                else:
                    cell_data = None
                if attr_data != cell_data:
                    mower_row[mower_att_key] = attr_data
            except Exception as e:
                err_line = sys.exc_info()[-1].tb_lineno
                self.host.comms_logger.error('error in scanner update: {} on line: {}'.format(e, err_line))
        
        is_selected = (self.host.config['current.mower'] == mower_key)
        mower_row['selected'] = is_selected
        if 'ping' not in mower_row: mower_row['ping'] = False
        if 'advertising' not in mower_row: mower_row['advertising'] = 0
        if 'connected' not in mower_row: mower_row['connected'] = False
        self.datatable[mower_key] = mower_row

    def refresh(self, mode, need_to_scan):
        try:
            for mower_key in list(self.datatable):
                mower_element = self.config.cfg_root.find('.//mower[@name="{}"]'.format(mower_key))
                # there are 2 possibilities: we both have it => do nothing, or we do you don't => delete
                if mower_element is None:
                    self.host.comms_logger.info('scanner removing {} mower from datatable'.format(mower_key))
                    del self.datatable[mower_key]
    
            for mower_element in self.config.cfg_root.findall('.//mower'):
                mower_key = mower_element.attrib['name']
                # there are 2 possibilities: we have it => update, or we don't have it => insert
                if mower_key in self.datatable:
                    self.update(mower_element, self.datatable[mower_key]) 
                else:
                    self.host.comms_logger.info('scanner inserting {} mower in datatable'.format(mower_key))
                    self.datatable[mower_key] = {}
                    self.update(mower_element, self.datatable[mower_key])
                    
            if mode > 0:
                # current connection?
                mower_transport = self.host.config['mower.transport']
                ble_connected = self.bt_avail and self.host.blue_proxy.is_connected()
                self.host.comms_logger.debug('scanner ble connected: {}'.format(ble_connected))
                sel_mower = self.host.config['current.mower']
                con_mower = self.host.blue_proxy.device_name if self.bt_avail else None
                wrong_connection = (sel_mower != con_mower)
                self.host.comms_logger.debug('scanner wrong connection? {} != {} => {}'.format(sel_mower, con_mower, wrong_connection))
                adv_mowers = [d.name for d in self.host.blue_proxy.devices] if self.bt_avail else []
                is_mower_adv = (sel_mower in adv_mowers)
                self.host.comms_logger.debug('scanner is mower advertising? {} in {} => {}'.format(sel_mower, adv_mowers, is_mower_adv))

                if ble_connected:
                    # connected to wrong device?
                    if wrong_connection:
                        self.host.blue_proxy.disconnect()
                        self.host.comms_logger.info('scanner disconnecting...')
                    elif self.host.despatcher.sequential_failure_count > 3:
                        # despatches failing
                        self.host.blue_proxy.disconnect()
                        self.host.comms_logger.info('despatches failing - scanner disconnecting...')
                else:
                    if is_mower_adv:
                        # connect
                        self.host.comms_logger.info('scanner connecting...')
                        try:
                            self.host.blue_proxy.connect(sel_mower)
                            self.host.blue_proxy.register_notify()
                            self.host.comms_logger.debug(self.host.blue_proxy)
                            # close existing?
                            if self.host.despatcher is not None:
                                msg = 'scanner closing despatcher {}'.format(self.host.despatcher.connection)
                                self.host.comms_logger.info(msg)
                                self.host.despatcher.close()
                            self.host.comms_logger.info('scanner creating BLE Despatcher...')
                            self.host.despatcher = BLEDespatcher(self.host, 10, Lock()) # timeout 10 secs, exclusive
                        except Exception as e:
                            err_line = sys.exc_info()[-1].tb_lineno
                            self.host.comms_logger.warn('Selected mower did not connect: {} on line {}'.format(e, err_line))
                    elif mower_transport == 'udp':
                        # udp and virtual mowers don't connect as such, but we need a despatcher
                        ip_addr = self.host.config['mower.ip']
                        port = self.host.config['mower.port']
                        # close existing?
                        if (self.host.despatcher is not None and 
                            'sock_addr' in vars(self.host.despatcher) and
                            self.host.despatcher.sock_addr != (ip_addr, port)
                            ):
                            msg = 'scanner closing despatcher {}'.format(self.host.despatcher.connection)
                            self.host.comms_logger.info(msg)
                            self.host.despatcher.close()
                            self.host.despatcher = None
                        if self.host.despatcher is None:
                            self.host.comms_logger.info('scanner creating UDP Despatcher...')
                            self.host.despatcher = UDPDespatcher(self.host, ip_addr, port, 10, Lock()) # timeout 10 secs, exclusive
                    else:
                        if self.host.despatcher is not None:
                            # close existing
                            msg = 'scanner closing despatcher {}'.format(self.host.despatcher.connection)
                            self.host.comms_logger.info(msg)
                            self.host.despatcher.close()
                            # null despatcher
                            self.host.comms_logger.info('scanner nulling despatcher')
                            self.host.despatcher = None
                            
                        if need_to_scan:
                            # scan for ble devices?
                            if self.bt_avail:
                                self.host.comms_logger.info('scanner scanning for ble devices...')
                                self.host.blue_proxy.scan()
                                for mower_key in self.datatable:
                                    mower_row = self.datatable[mower_key]
                                    # advertising
                                    is_advertising = mower_row['name'] in [d.name for d in self.host.blue_proxy.devices]
                                    if 'advertising' in mower_row:
                                        mower_row['advertising'] += is_advertising
                                    else:
                                        mower_row['advertising'] = 0
                                                    
                            # ping loop
                            self.host.comms_logger.info('scanner pinging...')
                            cache_dict = {}
                            for mower_key in self.datatable:
                                mower_row = self.datatable[mower_key]
                                # append ping status?
                                ip_addr = mower_row['ip']
                                port = mower_row['port']
                                if (ip_addr, port) in cache_dict:
                                    ping_status = cache_dict[(ip_addr, port)]
                                else:
                                    ping_status = ping_server(ip_addr)
                                    cache_dict[(ip_addr, port)] = ping_status
                                mower_row['ping'] = ping_status
                            self.last_scan = strftime('%H:%M:%S')
                        else:
                            self.host.comms_logger.debug('scanner no scanning needed')
                            

                # selected connected
                for mower_key in self.datatable:
                    mower_row = self.datatable[mower_key]
                    is_selected = (self.host.config['current.mower'] == mower_key)
                    mower_row['selected'] = is_selected
                    ble_connected = self.bt_avail and self.host.blue_proxy.is_connected()
                    mower_row['connected'] = is_selected and (ble_connected or mower_transport == 'udp')
            else:
                for mower_key in self.datatable:
                    mower_row = self.datatable[mower_key]
                    mower_row['ping'] = False
                    mower_row['advertising'] = 0 if self.bt_avail else ''
                    mower_row['connected'] = False
                    mower_row['selected'] = False
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.host.comms_logger.error('Error in scanner refresh: ' +
                           str(e) + ' on line ' + str(err_line))
            
    def render(self):
        row_list = []
        try:
            for mower_key in self.datatable:
                try:
                    mower_row = self.datatable[mower_key]
                    row_list.append(list(self.render_row(mower_row).values()))
                except Exception as e:
                    err_line = sys.exc_info()[-1].tb_lineno
                    self.host.comms_logger.warning('scanner render key missing ' +
                                   str(e) + ' on line ' + str(err_line))
        except Exception as e:
            err_line = sys.exc_info()[-1].tb_lineno
            self.host.comms_logger.error('Error in scanner render: ' +
                           str(e) + ' on line ' + str(err_line))
        return row_list

    def render_row(self, mower_row):
        debug = False
        docs = False
        # set empty to show all columns for debugging
        hidden_col_prefix = '' if debug else '_'
        _variant = self.__class__.__name__

        # conditional inclusion not permitted - a column must be populated
        row_attributes = {}
        
        row_class = 'row-' + mower_row['type'].lower()
        if mower_row['selected']:
            row_class += ' row-selected'
        advice_verb = 'act'
        cancel = False

        if mower_row['type'].endswith('ble') and not self.bt_avail:
            # no actions available
            row_class = 'row-btdis'
            advice_verb = None
        elif mower_row['type'].endswith('ble'):
            if mower_row['selected']:
                # disconnect & deselect
                advice_verb = 'disconnect & deselect'
                cancel = True
            else:
                # select & connect
                advice_verb = 'select & connect'
        else:
            # udp or virtual
            if mower_row['selected']:
                # deselect
                advice_verb = 'deselect'
                cancel = True
            else:
                # select
                advice_verb = 'select'
                
        if advice_verb is None:
            advice = 'unable to select - no bluetooth available'
            action = None
        else:
            advice = 'double click row to {}'.format(advice_verb)
            question = 'Are you sure you want to {} {}?'.format(advice_verb, mower_row['name'])
            prompt = "if (confirm('{}')) ".format(question)
            cmd = "sendData('PUT', 'api', 'current.mower', '{}', true);".format(
                'None' if cancel else mower_row['name'])
            action = prompt + cmd 
        
        row_attributes[hidden_col_prefix + '@row_class'] = row_class
        row_attributes[hidden_col_prefix + '@row_title'] = advice
        row_attributes[hidden_col_prefix + '@row_ondblclick'] = action

        # merge extra items and row attributes into new dict
        dkdict = DupeKeyDict(row_attributes)
        dkdict['Selected'] = '<br />'
        if mower_row['selected']:
            dkdict[hidden_col_prefix + '@cell_class'] = 'cell-sel'
        else:
            dkdict[hidden_col_prefix + '@cell_class'] = None
        dkdict['Name'] = mower_row['name']
        dkdict['Type'] = mower_row['type']
        dkdict['Address'] = '192.168.x.x' if docs else mower_row['ip']
        dkdict['Port'] = 1234 if docs else mower_row['port']
        dkdict['Ping'] = '<br />'
        if mower_row['ping']:
            dkdict[hidden_col_prefix + '@cell_class'] = 'cell-tick'
        else:
            dkdict[hidden_col_prefix + '@cell_class'] = None
        dkdict['Advertising'] = mower_row['advertising']
        dkdict[hidden_col_prefix + '@cell_class'] = 'cell-numeric'
        
        dkdict['Connected'] = '<br />'
        if mower_row['connected']:
            dkdict[hidden_col_prefix + '@cell_class'] = 'cell-tick'
        else:
            dkdict[hidden_col_prefix + '@cell_class'] = None
            
        return dkdict
    
    def process(self):
        self.refresh(mode=0, need_to_scan=False)
        while True:
            need_to_scan = (
                (self.config['current.mower'] is not None and 
                self.config['current.mower'] != 'None') or 
                self.host.comms_gui_requests > 0
            ) 
            self.refresh(mode=1, need_to_scan=need_to_scan)
            self.host.comms_gui_requests = 0 # reset
            sleep(5)       

    def reset_stats(self):
        for mower_key in self.datatable:
            mower_row = self.datatable[mower_key]
            mower_row['ping'] = False
            mower_row['advertising'] = 0
        
    def __repr__(self):
        return str(self.datatable)