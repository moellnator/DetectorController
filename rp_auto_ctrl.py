import sys
import ConfigParser
import time
import datetime
import logging
import logging.handlers
import os

from rp_auto_mod_scale import ModuleScale
from rp_auto_mod_modem import ModuleModem
from rp_auto_mod_server import ModuleServer
from rp_auto_mod_pump import ModulePump
from rp_auto_mod_mmeter import ModuleMMeter

class _config:

    _setting = None
    
    def __init__( self, path ):
        self._setting = ConfigParser.ConfigParser()   
        self._setting.read(path + '.ini')
        
    def GetSetup( self, name ):
        return dict(self._setting.items(name))

class _runtime:

    def __init__( self ):
        # get config options from file
        self.config = _config('rp_auto_setup')
        # \ch: set up the logging system before everything else, so stuff can log its initialization
        self.logopts=self.config.GetSetup('logging')
        self.logger = logging.getLogger('rp_auto_ctrl')
        self.logger.setLevel(logging.DEBUG)
        logFormatter = logging.Formatter("%(asctime)s %(levelname)-5.5s: [%(module)-18.18s] %(message)s",datefmt="%Y-%m-%d %H:%M:%S")
        logFileHandler = logging.handlers.TimedRotatingFileHandler(self.logopts['logfile'], when='midnight', backupCount=7)   # \ch: output to log file, new file is created for every day, files are retained for 7 days
        logFileHandler.setFormatter(logFormatter)
        self.logger.addHandler(logFileHandler)
        logStreamHandler = logging.StreamHandler(sys.stdout)   # \ch: also output log to stdout
        logStreamHandler.setFormatter(logFormatter)
        logStreamHandler.setLevel(logging.INFO) # \ch: don't print debug info to stdout
        self.logger.addHandler(logStreamHandler)
        # \ ch set up the actual components
        self.modem = ModuleModem(**self.config.GetSetup('modem'))
        self.scale = ModuleScale(**self.config.GetSetup('scale'))
        self.pump = ModulePump(**self.config.GetSetup('pump'))
        self.server = ModuleServer(**self.config.GetSetup('server'))
        self.mmeter = ModuleMMeter(**self.config.GetSetup('mmeter'))
        self.server.GatherModuleData = self._gather_data
    
    def _run( self ):
        self.lastcheck = datetime.datetime.now()
        self.logger.info('LN2 control started')
        while True:
            # \ch: offer a way to gracefully shut the program down
            if os.path.isfile('rp_auto_quit'):
                self.logger.info('Shutdown indicator file ' + 'rp_auto_quit' + ' found, terminating...')
                os.remove('rp_auto_quit') # remove indicator file
                break
            self.value_mmeter = self.mmeter.GetValue()
            self.value_scale = self.scale.GetValue()
            self.value_pump = self.pump.GetPumpState()
            self.level_pump = self.pump.GetPumpLevel()
            if self.value_scale <= -4.0:
                if not self.value_pump:
                    self.logger.info('Lower boundary crossing (' + str(self.value_scale) + ') detected, attempting to start pump')
                    self.pump.StartPump()
                    self.lastcheck = datetime.datetime.now()
                    self.modem.SendSMS(self.logopts['address'],time.strftime("%Y-%m-%d %H:%M",time.gmtime()) + ': Scale value is ' + str(self.value_scale) + ' kg, starting LN2 pump. Dewar level is ' + "{:.1f}".format(self.level_pump) + ' cm, getter pump voltage is ' + str(self.value_mmeter) + ' V.')    # send sms to G. Weber, M. Vockert
            elif self.value_scale >= 0.06:
                if self.value_pump:
                    self.logger.info('Upper boundary crossing (' + str(self.value_scale) + ') detected, attempting to stop pump')
                    self.pump.StopPump()
                    self.modem.SendSMS(self.logopts['address'],time.strftime("%Y-%m-%d %H:%M",time.gmtime()) + ': Scale value is ' + str(self.value_scale) + ' kg, stopping LN2 pump. Getter pump voltage is ' + str(self.value_mmeter) + ' V.')
            time.sleep(1.0)

    def _gather_data( self ):
        return 'OK' + '\t' + str(self.value_scale) + '\t' + str(self.value_pump) + '\t' + str(self.level_pump) + '\t' + str(self.value_mmeter) + '\t' + str(self.lastcheck)

def main( ):
    rt = _runtime()
    rt._run()
    return 0

def toHex(s):
    lst = []
    for ch in s:
        hv = hex(ord(ch)).replace('0x', '')
        if len(hv) == 1:
            hv = '0'+hv
        lst.append(hv)
    
    return reduce(lambda x,y:x+' ' +y, lst)


if __name__ == "__main__":
    sys.exit(main())
