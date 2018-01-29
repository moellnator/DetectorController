import serial
import atexit
import time
import sys
import logging

def write( str ):
    sys.stdout.write( str )

class ModuleModem:
    
    _prt = None
    
    def __init__( self, port, pin ):
        self.logger = logging.getLogger('rp_auto_ctrl')
        self.logger.info('Initializing WAVECOM modem...')
        #write('Initializing WAVECOM modem:\n')
        self._prt = self._open_port('/dev/' + port)
        self._check_device()
        self._check_pin(pin)
        self._check_network()
        self.exitcallback = None
        self.logger.info('WAVECOM modem initialization complete')
        #write('<DONE>\n')

    def _open_port( self, tty ):
        self.logger.debug('Opening port [' + tty + ']... ')
        #write( '   Opening port [' + tty + ']... ' )
        retval = serial.Serial( 
            port = tty,
            baudrate = 19200,
            bytesize = serial.EIGHTBITS,
            parity = serial.PARITY_NONE,
            stopbits = serial.STOPBITS_ONE,
            timeout = 1,
            xonxoff = False,
            rtscts = True,
            dsrdtr = True
        )
        if not retval.isOpen: retval.open()
        while retval.inWaiting() > 0: retval.read(self._prt.inWaiting())
        atexit.register( self._on_exit)
        self.logger.debug('Port ' + tty + ' opened')
        #write( '<DONE>\n' )    
        return retval

    def _send_cmd( self, str ):
        cmd = 'AT' + str + '\r'
        self._prt.write(cmd)
        time.sleep(0.5)
        echo = []
        while self._prt.inWaiting() > 0: echo.append(self._prt.readline().strip())
        return echo
        
    def _send_cmd_ret( self, str ):
        echo = self._send_cmd(str)
        if len(echo) <= 1:
            raise ValueError('Invalid return value!')
        return echo[1]  # \ch: "1" bc. modem returns command in echo[0]?
        
    def _check_device( self ):
        self.logger.debug('Checking connected device...')
        #write( '   Checking connected device... ' )
        retval = self._send_cmd_ret('+CGMI')
        self.logger.debug('Received response <' + retval + '>')
        #write('<' + retval + '>')
        if retval == 'WAVECOM MODEM':
            self.logger.debug('Device recognized')
            #write('<DONE>\n')
            return True
        else:
            raise Exception('Connected device is unknown / connection error!')
    
    def _check_pin( self, pin ):
        self.logger.debug('Checking SIM PIN...')
        #write( '   Checking SIM PIN... ' )
        retval = self._send_cmd_ret('+CPIN?')
        self.logger.debug('Recieved response <' + retval + '>')
        #write('<' + retval + '>')
        if retval == '+CPIN: READY':
            self.logger.debug('SIM PIN accepted')
            #write('<DONE>\n')
            return True
        elif retval == '+CPIN: SIM PIN':
            self.logger.debug('Entering SIM PIN...')
            #write( '\n      Entering SIM PIN... ' )
            retval = self._send_cmd_ret('+CPIN=' + pin)
            self.logger.debug('Using PIN ' + retval)
            #write('<' +  retval + '>')
            if retval == "ERROR": raise Exception('** Invalid PIN!')
            time.sleep(10)
            self.logger.debug('Complete')
            #write('<DONE>\n')
            return True
        else:
            raise Exception('** SIM card is protected by PUK!')
            
    def _check_network( self ):
        self.logger.debug('Checking network registration...')
        #write( '   Checking network registration... ' )
        retval = self._send_cmd_ret('+CREG?')
        if retval == '+CREG: 0,1':
            self.logger.debug('LOCAL mode detected')
            #write("<LOCAL><DONE>\n")
            return True
        elif retval == '+CREG: 0,5':
            self.logger.debug('ROAMING mode detected')
            #write("<ROAMING><DONE>\n")
            return True
        else:
            raise Exception('** Unknown network registration state!')
    
    def SendSMS( self, address, msg ):
        if ',' in address:            # \ch: implement recursive call to allow comma-separated list of recipients
            addresslist = address.split(',')
            for x in addresslist: self.SendSMS(x, msg)
        else:
            if not address:    # i.e., address is empty
                self.logger.info('No recipient address defined')
                return False
            self.logger.info('Sending short mail to [' + address + ']... ')
            self.logger.debug('Mail content: ' + msg)
            echo = self._send_cmd('+CMGS="' + address + '"')
            self.logger.debug('Modem returned <' + '><'.join(echo) + '>')
            if not ( len(echo) >= 2 and echo[-1] == '>' ):  # usually echo will only be two elements, but sometimes modem will notify about unread incoming messages as well
                self.logger.warning('Aborting send operation due to invalid return value')
                return False
            self._prt.write(msg + chr(26))
            time.sleep(0.2)
            self._prt.readline() 
            loopctr = 0
            while self._prt.inWaiting() == 0:
                time.sleep(0.01)  
                loopctr += 1    # prevent infinite loop
                if loopctr>3000:
                    raise Exception('Timeout waiting for response')
            retval = []
            time.sleep(0.2)
            while self._prt.inWaiting() > 0: retval.append(self._prt.readline().strip())
            if retval[-1] == 'OK':
                self.logger.info('Success, return value ' + retval[1])
                return True
            else:
                self.logger.info('Failed')
                return False   
        
    def RegisterExitCallback( self, f):
        self.exitcallback = f
        
    def _on_exit( self ):
        if self.exitcallback: self.exitcallback()
        self.logger.debug('Closing port [' + self._prt.port +']')
        #write( '** Closing port [' + self._prt.port + ']\n' ) 
        self._prt.close()
