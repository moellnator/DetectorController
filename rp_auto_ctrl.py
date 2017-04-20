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
        self._setting.read('rp_auto_default.ini')   # initialize settings structure with defaults
        self._setting.read(path + '.ini')
        
    def GetSetup( self, name ):
        return dict(self._setting.items(name))

class _runtime:

    def __init__( self ):
        # get config options from file
        self.config = _config('rp_auto_setup')
        # \ch: set up the logging system before everything else, so stuff can log its initialization
        self.logopts = self.config.GetSetup('logging')
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
        # get other parameters
        self.runparams = self.config.GetSetup('runparams')
        # process parameters
        try:
            self.lnlevel2fillings = float(self.runparams["dewarvolume"])/float(self.runparams["dewarheight"])*0.808/(float(self.runparams["maxweight"])-float(self.runparams["minweight"])) # scale ln2 level to total dewar volume, convert that to kg's (LN2 density is 0.808) and divide by "weight per pumping process"
        except Exception as err:
            self.logger.warning('Could not determine level-to-fillings conversion factor, setting it to 1: ' + str(err))
            self.lnlevel2fillings = 1.0
        # initialize some other stuff
        self.docleanexit = False
        self.modem.RegisterExitCallback(self._sms_exitcallback)
        try:
            self.pollinterval = float(self.runparams["pollinterval"])
            if self.pollinterval<1.0: raise NameError('pollinterval has to be at least 1.0s')
        except Exception as err:
            self.logger.warning('Could not set polling interval, setting it to 1s: ' + str(err))
            self.pollinterval = 1.0
        
    
    def _run( self ):
        self.lastcheck = datetime.datetime.now()
        self.logger.info('LN2 control started')
        while True:
            # \ch: offer a way to gracefully shut the program down
            if os.path.isfile(self.runparams["quitfile"]):
                self.logger.info('Shutdown indicator file ' + self.runparams["quitfile"] + ' found, terminating...')
                self.docleanexit = True
                os.rename(self.runparams["quitfile"], self.runparams["quitfile"] + '_bak') # rename indicator file
                break
            self.value_mmeter = self.mmeter.GetValue()
            self.value_scale = self.scale.GetValue()
            self.value_pump = self.pump.GetPumpState()
            self.level_pump = self.pump.GetPumpLevel()
            if self.value_scale <= float(self.runparams["minweight"]):
                if not self.value_pump:
                    self.logger.info('Lower boundary crossing (' + str(self.value_scale) + ') detected, attempting to start pump')
                    self.pump.StartPump()
                    self.lastcheck = datetime.datetime.now()
                    
                    self.modem.SendSMS(self.logopts['address'],time.strftime("%Y-%m-%d %H:%M",time.gmtime()) + \
                    ': Scale value is ' + str(self.value_scale) + \
                    ' kg, starting LN2 pump. Dewar level is ' + "{:.1f}".format(self.level_pump) + \
                    ' cm, so about ' +  "{:.1f}".format(self.level_pump*self.lnlevel2fillings) + \
                    ' LN2 fillings remaining. Getter pump voltage is ' + str(self.value_mmeter) + ' ' + self.mmeter.OutUnit)    # send sms to G. Weber, M. Vockert
            elif self.value_scale >= float(self.runparams["maxweight"]):
                if self.value_pump:
                    self.logger.info('Upper boundary crossing (' + str(self.value_scale) + ') detected, attempting to stop pump')
                    self.pump.StopPump()
                    self.modem.SendSMS(self.logopts['address'],time.strftime("%Y-%m-%d %H:%M",time.gmtime()) + ': Scale value is ' + str(self.value_scale) + ' kg, stopping LN2 pump. Getter pump voltage is ' + str(self.value_mmeter) + ' ' + self.mmeter.OutUnit)
            time.sleep(self.pollinterval)

    def _gather_data( self ):
        return 'OK' + '\t' + str(self.value_scale) + '\t' + str(self.value_pump) + '\t' + str(self.level_pump) + '\t' + str(self.value_mmeter) + '\t' + str(self.lastcheck)
        
    def _sms_exitcallback( self ):
        if not self.docleanexit:
            self.modem.SendSMS(self.logopts['address'], 'DANGER! DANGER! Unexpected LN2 control function abort in progress! Seek shelter immediately!')

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
