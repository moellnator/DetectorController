import atexit
import time
import sys
import termios
import os
import serial
import logging

def write( str ):
    sys.stdout.write( str )

class ModulePump:
    
    _prt = None
    
    def __init__( self, tty ):
        self.logger = logging.getLogger('rp_auto_ctrl')
        self.logger.info('Initializing LN2 pump...')
        #write('Initializing LN2 pump:\n')
        self.__tty = tty
        self._prt = self._open_port('/dev/' + tty, 'P') # try PySerial protocol first
        try:
            self._check_pump()
        except Exception as err:
            self.logger.info('PySerial linkup failed, switching to TermIOS: ' + str(err))
            self._prt = self._open_port('/dev/' + tty, 'T')
            self._check_pump()
        self.logger.info('Successfully initialized LN2 pump')
        #write('<DONE>\n')

    def _open_port( self, tty, mode = 'P'):     # mode='P' for PySerial implementation, 'T' for TermIOS implementation
        self.logger.debug('Opening port [' + tty + '] via PySerial...')
        #write( '   Opening port [' + tty + ']... ' )
        if mode == 'T':     # termios implementation
            retval = os.open(tty, os.O_RDWR | os.O_NONBLOCK)
            attr = termios.tcgetattr(retval)
            attr[2] = termios.CS8 # byte size is 8 bits
            attr[4] = termios.B19200
            attr[5] = termios.B19200
            termios.tcsetattr(retval, termios.TCSADRAIN, attr)
            termios.tcflush(retval, termios.TCIFLUSH)   # sometimes the buffer will not be empty on connection, so that replies to commands are appended at the end and not found where expected when read back
        else:       # default PySerial implementation
            retval = serial.Serial( 
                port = tty,
                baudrate = 19200,
                bytesize = serial.EIGHTBITS,
                parity = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                timeout = 1,
                xonxoff = False,
                rtscts = False,
                dsrdtr = False
            )
            if not retval.isOpen: retval.open()
            retval.flushInput() # purge input buffer, since device writes continuously to buffer
            
        atexit.register( self._on_exit)
        self.logger.debug('Successfully opened port')
        #write( '<DONE>\n' )    
        return retval

    def _send_cmd( self, cmd ):
        if type(self._prt) is serial.serialposix.Serial:  # pyserial implementation
            self._prt.write(cmd)
            time.sleep(0.4)
            echo = []
            while self._prt.inWaiting() > 0: echo.append(self._prt.readline().strip())
            return echo
        else:
            os.write(self._prt, cmd + '\x0d')
            time.sleep(0.4)
            return os.read(self._prt, 1024).split('\r\n')

    def _check_pump( self ):
        self.logger.debug('Checking device...')
        #write( '   Checking device... ' )
        retval = self._send_cmd('i')
        if len(retval)<5 or not retval[5] == 'Ready': raise NameError('Unknown device connected!')
        self.logger.debug('Received answer <' + retval[1][9:] + '>')
        self.logger.debug('Device check complete')
        #write( '<' + retval[1][9:] + '>' )
        #write( '<DONE>\n' )

    def StartPump( self ):
        self.logger.info('Start pumping LN2...')
        #write('### Start pumping LN2... ') 
        retval = self._send_cmd('pon')
        if not retval[2] == 'Ready': raise NameError('Unable to start LN2 pump!')
        self.logger.info('Pump successfully started')
        #write( '<DONE>\n' )

    def StopPump( self ):
        self.logger.info('Stop pumping LN2')
        #write('### Stopping pumping LN2... ') 
        retval = self._send_cmd('pof')
        if not retval[2] == 'Ready': raise NameError('Unable to stop LN2 pump!')
        self.logger.info('Pump successfully stopped')
        #write( '<DONE>\n' )

    def GetPumpState( self ):
        self.logger.debug('Getting pump status...')
        retval = self._send_cmd('rm 114')
        self.logger.debug('Received <' + retval[1] + '>')
        if not retval[2] == 'Ready': raise NameError('Unable to contact LN2 pump!')
        return retval[1] == '01'
    
    def GetPumpLevel( self ):
        self.logger.debug('Getting LN2 level from pump...')
        try: 
            retval = self._send_cmd('rm 0ce 1')
            self.logger.debug('Received <' + retval[1] + '>')
            if not retval[2] == 'Ready': raise NameError('Unable to contact LN2 pump!')
            level = (int(retval[1], 16) - 38)*0.542888/0.808    # 38 is a fixed offset, taken from the pump EEprom
            self.logger.debug('Converted value to ' + str(level))
            return level
        except Exception as err:
            self.logger.warning('Error getting pump level: ' + str(err))
            return float("nan")
    
    def _on_exit( self ):
        self.logger.debug('Closing port [' + self.__tty + ']')
        #write( '** Closing port [' + self.__tty + ']\n' ) 
        if type(self._prt) is serial.serialposix.Serial:  # pyserial implementation
            self._prt.close()
        else:
            os.close(self._prt)
