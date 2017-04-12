﻿import socket
import atexit
import time
import sys
import logging

from thread import start_new_thread

def write( str ):
    sys.stdout.write( str )

class ModuleServer:
    
    BUFFER_SIZE = 1024

    def __init__( self, port ):
        self.logger = logging.getLogger('rp_auto_ctrl')
        self.logger.info('Initializing IPv4/TCP server...')
        #write('Initializing IPv4/TCP server...\n')
        self._init_server(port)
        start_new_thread(self._wkr_server, ()) 
        self.logger.info('Successfully initialized server')
        #write('<DONE>\n')
    
    def _init_server( self, port ):
        self.logger.debug('Opening IPv4/TCP port [' + port + ']...')
        #write('   Opening IPv4/TCP port [' + port + ']...')
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(('', int(port)))
        self._sock.listen(1)
        atexit.register(self._on_exit)
        self.logger.debug('Successfully opened port')
        #write('<DONE>\n')
        
    def _wkr_server( self ):
        while True:
            try:
                conn, addr = self._sock.accept()
                data = conn.recv(self.BUFFER_SIZE).strip()
                if data == 'SVR:HELLO':
                    conn.send('CNT:HELLO=RP_AUTO_SERVER_V1.0\r\n')
                elif data == 'SVR:DATA':
                    self.logger.debug('Sending data entry to client... <' + str(addr) + '>')
                    #write('** Sending logging entry to client... <' + str(addr) + '>\n')
                    conn.send('CNT:DATA=' + self.GatherModuleData())
                else:
                    conn.send('CNT:ERROR=UNKNOWN_CMD\r\n')
                conn.close()
            except Exception as err:    # when rp_auto_ctrl finishes, this thread will try to still use _sock -- catch that
                self.logger.warning('Terminating thread because of an error: ' + str(err))
                break

    def _on_exit( self ):
        self.logger.debug('Closing IPv4/TCP port [' + str(self._sock.getsockname()[1]) + ']')
        try:
            self._sock.shutdown(socket.SHUT_RDWR) 
        except Exception as err:
            self.logger.warning('Encountered error during socket shutdown: ' + str(err))
        self._sock.close() 
             
