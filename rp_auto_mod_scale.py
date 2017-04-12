import serial
import atexit
import time
import sys
import logging

def write( str ):
    sys.stdout.write( str )

class ModuleScale:
    
    _prt = None
    
    def __init__( self, port ):
        self.logger = logging.getLogger('rp_auto_ctrl')
        self.logger.info('Initializing KERN scale...')
        #write('Initializing KERN scale:\n')
        self._prt = self._open_port('/dev/' + port)
        self.logger.info('Scale initialization complete')
        #write('<DONE>\n')

    def _open_port( self, tty ):
        self.logger.debug('Opening port ' + tty)
        #write( '   Opening port [' + tty + ']... ' )
        retval = serial.Serial( 
            port = tty,
            baudrate = 9600,
            bytesize = serial.EIGHTBITS,
            parity = serial.PARITY_NONE,
            stopbits = serial.STOPBITS_ONE,
            timeout = 1,
            xonxoff = False,
            rtscts = False,
            dsrdtr = False
        )
        if not retval.isOpen: retval.open()
        while retval.inWaiting() > 0: retval.read(self._prt.inWaiting())
        atexit.register(self._on_exit)
        self.logger.debug('Successfully opened port')
        #write( '<DONE>\n' )    
        return retval

    def GetValue( self ):
        self.logger.debug('Getting value from scale...')
        #write('### ' + time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()) + '# Getting value from scale... ') 
        #sys.stdout.flush()    # \ch: force update of output buffer, otherwise teed log isn't displayed simultaneously
        cmd = 'w'
        self._prt.write(cmd)
        time.sleep(0.5)
        echo = []
        while self._prt.inWaiting() > 0: echo.append(self._prt.readline().strip())
        if len(echo) != 1: raise NameError('Unable to read value!')
        retval = echo[0]
        self.logger.debug('Received ' + retval)
        #write(retval)
        if ' ' in retval: retval = retval[0:(retval.rfind(' '))]
        if retval.replace(' ', '' ) == '-': retval = echo[0]
        retval = retval.replace(' ', '')
        self.logger.debug('Converted value to ' + retval)
        #write('<' + retval + '>')
        #write('<DONE>\n')
        return float(retval)
        
    def _on_exit( self ):
        self.logger.debug('Closing port [' + self._prt.port + ']')
        #write( '** Closing port [' + self._prt.port + ']\n' ) 
        self._prt.close()
