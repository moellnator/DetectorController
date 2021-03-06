﻿import atexit
import time
import sys
import os
try:
    import serial
except ModuleNotFoundError:
    import termios
import logging

def write( str ):
    sys.stdout.write( str )

class ModulePump:
    
    _prt = None
    
    def __init__( self, tty, loggername = ""):
        self.logger = logging.getLogger(loggername or 'rp_auto_ctrl')
        self.logger.info('Initializing LN2 pump...')
        self.__tty = tty
        try:
            self._prt = self._open_port('/dev/' + tty, 'P') # try PySerial protocol first
            self._check_pump()
        except Exception as err:
            try: 
                self._prt.close() # just to be sure that previous prt does not remain open
            except:
                pass
            self.logger.info('PySerial linkup failed, switching to TermIOS: ' + str(err))
            
            self._prt = self._open_port('/dev/' + tty, 'T')
            self._check_pump()
        finally:
            self.logger.info('Successfully initialized LN2 pump')
            self._querySensorOffsets()

    def _open_port( self, tty, mode = 'P'):     # mode='P' for PySerial implementation, 'T' for TermIOS implementation
        if mode == 'T':     # termios implementation
            self.logger.debug('Opening port [' + tty + '] via TermIOS...')
            retval = os.open(tty, os.O_RDWR | os.O_NONBLOCK)
            attr = termios.tcgetattr(retval)
            attr[2] = termios.CS8 # byte size is 8 bits
            attr[4] = termios.B19200
            attr[5] = termios.B19200
            termios.tcsetattr(retval, termios.TCSADRAIN, attr)
            termios.tcflush(retval, termios.TCIFLUSH)   # sometimes the buffer will not be empty on connection, so that replies to commands are appended at the end and not found where expected when read back
        else:       # default PySerial implementation
            self.logger.debug('Opening port [' + tty + '] via PySerial...')
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
            if not retval.isOpen(): retval.open()
            retval.flushInput() # purge input buffer, since device writes continuously to buffer
            
        atexit.register( self._on_exit)
        self.logger.debug('Port opened in ' + mode + ' mode')
        return retval

    def _send_cmd( self, cmd ):
        if isinstance(cmd, str):
            cmd = cmd.encode('utf-8')  # make sure cmd is byte array
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
        retval = self._send_cmd('i')
        if len(retval)<5 or not retval[5] == 'Ready': raise Exception('Unknown device connected!')
        self.logger.debug('Received answer <' + retval[1][9:] + '>')
        self.logger.debug('Device check complete')
        
    def _querySensorOffsets( self ):
        self.logger.debug('Getting sensor offsets...')
        # first, the "main" sensor at the pump inlet
        try:
            retval = self._send_cmd('re 016 2')
            self.logger.debug('Received <' + retval[1] + '>')
            if not retval[2] == 'Ready': raise Exception('Unable to contact LN2 pump!')
            self.pumpsensoroffset = (int(''.join(reversed(retval[1].split())), 16))   # reversed() acrobatics needed because retval is big-endian
            self.logger.debug('Converted value to ' + str(self.pumpsensoroffset))
        except Exception as err:
            self.logger.warning('Error getting pump sensor offset: ' + str(err))
            self.pumpsensoroffset = 145   # use a value that was previously observed
        # second, the "auxiliary" sensor, e.g positioned at the tube outlet
        try:
            retval = self._send_cmd('re 014 2')
            self.logger.debug('Received <' + retval[1] + '>')
            if not retval[2] == 'Ready': raise Exception('Unable to contact LN2 pump!')
            self.auxsensoroffset = (int(''.join(reversed(retval[1].split())), 16))   # reversed() acrobatics needed because retval is big-endian
            self.logger.debug('Converted value to ' + str(self.auxsensoroffset))
        except Exception as err:
            self.logger.warning('Error getting auxiliary sensor offset: ' + str(err))
            self.auxsensoroffset = 145   # use a value that was previously observed
        # third, the level sensor
        try:
            retval = self._send_cmd('re 01c 2')
            self.logger.debug('Received <' + retval[1] + '>')
            if not retval[2] == 'Ready': raise Exception('Unable to contact LN2 pump!')
            self.levelsensoroffset = (int(''.join(reversed(retval[1].split())), 16))   # reversed() acrobatics needed because retval is big-endian
            self.logger.debug('Converted value to ' + str(self.levelsensoroffset))
        except Exception as err:
            self.logger.warning('Error getting level sensor offset: ' + str(err))
            self.levelsensoroffset = 38   # use a value that was previously observed

    def StartPump( self ):
        self.logger.info('Start pumping LN2...')
        retval = self._send_cmd('pon')
        if not retval[2] == 'Ready': raise Exception('Unable to start LN2 pump!')
        self.logger.info('Pump successfully started')

    def StopPump( self ):
        self.logger.info('Stop pumping LN2')
        retval = self._send_cmd('pof')
        if not retval[2] == 'Ready': raise Exception('Unable to stop LN2 pump!')
        self.logger.info('Pump successfully stopped')

    def GetPumpState( self ):
        """Returns True if pump is running, False otherwise."""
        self.logger.debug('Getting pump status...')
        retval = self._send_cmd('rm 114')
        self.logger.debug('Received <' + retval[1] + '>')
        if not retval[2] == 'Ready': raise Exception('Unable to contact LN2 pump!')
        return retval[1] == '01'
    
    def GetPumpLevel( self ):
        self.logger.debug('Getting LN2 level from pump...')
        try: 
            retval = self._send_cmd('rm 0ce 1')
            self.logger.debug('Received <' + retval[1] + '>')
            if not retval[2] == 'Ready': raise Exception('Unable to contact LN2 pump!')
            level = (int(retval[1], 16) - self.levelsensoroffset)*0.542888/0.808   
            self.logger.debug('Converted value to ' + str(level))
            return level
        except Exception as err:
            self.logger.warning('Error getting pump level: ' + str(err))
            return float("nan")
    
    def GetPumpSensorTemperature( self ):
        self.logger.debug('Getting pump sensor temperature...')
        try:
            retval = self._send_cmd('rm 086 2')
            self.logger.debug('Received <' + retval[1] + '>')
            if not retval[2] == 'Ready': raise Exception('Unable to contact LN2 pump!')
            temp = (int(''.join(reversed(retval[1].split())), 16)-self.pumpsensoroffset)   # reversed() acrobatics needed because retval is big-endian
            self.logger.debug('Converted value to ' + str(temp))
            return temp
        except Exception as err:
            self.logger.warning('Error getting pump sensor temperature: ' + str(err))
            return float("nan")
        
    def GetAuxSensorTemperature( self ):
        self.logger.debug('Getting auxiliary sensor temperature ...')
        try:
            retval = self._send_cmd('rm 084 2')
            self.logger.debug('Received <' + retval[1] + '>')
            if not retval[2] == 'Ready': raise Exception('Unable to contact LN2 pump!')
            temp = (int(''.join(reversed(retval[1].split())), 16)-self.auxsensoroffset)   # reversed() acrobatics needed because retval is big-endian
            self.logger.debug('Converted value to ' + str(temp))
            return temp
        except Exception as err:
            self.logger.warning('Error getting auxiliary sensor temperature: ' + str(err))
            return float("nan")
    
    def _on_exit( self ):
        # try shutting down the pump if it's still running when the handler terminates
        try:
            if self.GetPumpState():
                self.StopPump()
        except Exception:
            pass
        self.logger.debug('Closing port [/dev/' + self.__tty + ']')
        try:
            if type(self._prt) is serial.serialposix.Serial:  # pyserial implementation
                self._prt.close()
            else:   # termios implementation
                os.close(self._prt)
        except OSError:     # if _port_open was executed more than once (because the first call actually did not provide a usable port), _on_exit will try to close the self._prt more than once
            pass
