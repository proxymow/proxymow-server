import platform

from setting import *  # @UnusedWildImport
from forms.settings import *  # @UnusedWildImport


class Device(Morphable):
    '''
        represents a camera device
    '''
    _platform_agnostic = constants.PLATFORM_AGNOSTIC_DEVICES

    _chopts = {
        'VirtualSettings': 'Virtual Camera',
        'RemotePiSettings': 'Remote Pi'
    }
    if _platform_agnostic or platform.system() == 'Linux':
        _chopts.update({
            'PiSettings': 'Pi Camera',
            'LusbSettings': 'Linux USB',
        })
    if _platform_agnostic or platform.system() == 'Windows':
        _chopts.update({
            'WusbSettings': 'Windows USB'
        })
    channel = EnumerationSetting(
        'Channel', 'Hardware channel for camera', _chopts, {}, 'syncFieldsets(this);')
    index = IntSetting('Index', 'USB device index', '', 0, 10, 1)
    endpoint = TextSetting('Endpoint', 'server name:port of remote node')

    def __init__(self, channel=None, index=0, endpoint=None):
        self.channel = channel
        self.index = index
        self.endpoint = endpoint
        if self._platform_agnostic or platform.system() == 'Linux':  # Windows | Linux | Darwin(mac)
            self.piSettings = PiSettings()
            self.lusbSettings = LusbSettings()
        if self._platform_agnostic or platform.system() == 'Windows':
            self.wusbSettings = WusbSettings()
        self.virtualSettings = VirtualSettings()
