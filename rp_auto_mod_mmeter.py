import serial
import atexit
import time
import sys
import logging

def write( str ):
    sys.stdout.write( str )

class ModuleMMeter:
    
    _prt = None
    
    def __init__( self, port, outunit='V' ):
        self.logger = logging.getLogger('rp_auto_ctrl')
        self.logger.info('Initializing multimeter...')
        self._prt = self._open_port('/dev/' + port)
        self.OutUnit = outunit
        self.logger.info('Multimeter initialization complete')

    def _open_port( self, tty ):
        self.logger.debug('Opening port ' + tty)
        #write( '   Opening port [' + tty + ']... ' )
        retval = serial.Serial( 
            port = tty,
            baudrate = 19200,
            bytesize = serial.SEVENBITS,
            parity = serial.PARITY_NONE,
            stopbits = serial.STOPBITS_ONE,
            timeout = 1,
            xonxoff = False,
            rtscts = False,
            dsrdtr = False
        )
        if not retval.isOpen: retval.open()
        retval.flushInput() # purge input buffer, since device writes continuously to buffer
        atexit.register(self._on_exit)
        self.logger.debug('Successfully opened port')
        #write( '<DONE>\n' )    
        return retval

    def GetValue( self ):
        self.logger.debug('Getting value from multimeter...')
        # clear input buffer, then get reading from byte stream -- delimited by b1101 b1010
        try:
            self._prt.read(self._prt.inWaiting())
        except:
            pass
        echo = bytearray(self._prt.readline())
        self.logger.debug('Received <' + str(echo).strip() + '>')
        # parse the reading
        retval=parseReading(echo)
        # check overload, units
        if retval["overload"]: 
            self.logger.warning('Multimeter overload')
            return float("inf")
        if retval["unit"] != self.OutUnit:
            self.logger.warning('Multimeter not in ' + self.OutUnit + ' mode')
            return float("nan")
        # if everything is ok, return the value
        self.logger.debug('Converted value to ' + str(retval["value"]))
        return retval["value"]
        
    def _on_exit( self ):
        self.logger.debug('Closing port [' + self._prt.port + ']')
        #write( '** Closing port [' + self._prt.port + ']\n' ) 
        self._prt.close()
        
def parseReading(byte_array):
    # takes a 11-byte input array and extracts the actual instrument reading
    # check for overload
    overload = 0b0001 & byte_array[6] # get overload flag from byte 6 through bitmask
    # read number
    value = 0
    for idx in range(1,5):  # \ch: use range(1,5) to loop through [1, 2, 3, 4]
        value = value*10.0 + (0b1111 & byte_array[idx]) # shift result by one decimal place, then add new digit
    # check for negative value
    if 0b0100 & byte_array[6]: value = -value # lonibble of byte 6 is indicator portion of reading
    # get operation mode from byte 5 -- TODO: check whether "diode" is bit-0 or bit-1
    opmode_array=["", "diode", "kHz", "Ohm", "temperature", "passthrough", "nFarad", "", "", "A", "", "V", "", "uA", "transistor test", "mA"]
    try:
        opmode = opmode_array[0b1111 & byte_array[5]]
    except Exception as err:
        self.logger.warning('Failed to determine operation mode: ' + str(err))
        opmode = ""
    # get range from byte 0. range_array lists decimal value of last digit of reading
    range_array={ "kHz": [1, 1e1, 1e2, 1e3, 1e4], "Ohm": [1e-1, 1, 1e1, 1e2, 1e3, 1e4], "nFarad": [1e-3, 1e-2, 1e-1, 1, 1e1, 1e2, 1e3], "A": [1e-2], "V": [1e-3, 1e-2, 1e-1, 1, 1e-4], "uA": [1e-1, 1], "mA": [1e-2, 1e-1] }
    try:
        value = value * range_array[opmode][0b0111 & byte_array[0]]
    except Exception as err:
        self.logger.warning('Failed to convert value: ' + str(err))
        #value=value # assume conversion factor 1
        
    return {"value": value , "unit": opmode, "overload": overload}
