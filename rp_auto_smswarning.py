import atexit
import time
import sys
import logging
import datetime

from thread import start_new_thread

class SmsWarning:

    first_issued = 0 # keep track when warning was first encountered. If 0, warning is not currently active
    last_issued = 0 # is updated whenever the warning is encountered
    last_emit = 0 # is only updated when a notification message is sent

    def __init__( self, name, modem, recipients, time_suppress, time_resolve ):

        self.logger = logging.getLogger('rp_auto_ctrl') # tie into the global rp_auto_ctrl logger
        self.logger.info('Opened issue <' + name + '>.')
        self.name = name    # an identifier
        self.modem = modem    # the ModuleModem object
        self.recipients = recipients    # the list of notification recipients, directly passed to modem's SendSMS() method
        self.suppress = time_suppress    # the time interval in seconds after a notification has been sent for which no new one will be sent if the warning condition is encountered again
        self.release = time_resolve     # the time interval in seconds after which an issue is considered resolved if the warning is not encountered again
        start_new_thread(self._wkr_warning, ()) # start new thread to track time_resolve independently
        atexit.register(self._on_exit)
        

    def _wkr_warning( self ):
    
        while True:
            if self.IsIssued(): # warning is marked as "active"...
                if (date.datetime.now() - self.last_issued).total_seconds() >= self.release:    # ... but has not been encountered for self.release seconds
                    self.Resolve()
            time.sleep(10)  # \ch: need some time here to avoid hogging resources, but not too long w.r.t. self.release

    def Emit( self, message='' ):
    
        self.last_issued = datetime.datetime.now()      # update last_issued
        is_first_issue = False
        
        if not self.IsIssued():
            is_first_issue = True
            self.first_issued = datetime.datetime.now()     # record current time in first_issued if this is the first time the warning is encountered
            
        if is_first_issue or ((self.last_issued - self.last_emit).total_seconds() >= self.suppress):
            self.modem.SendSMS(self.recipients, 'Warning <' + self.name + '> active since ' + self.first_issued.strftime("%Y-%m-%d %H:%M") + ': ' + message)
            self.last_emit = self.last_issued
        else:
            self.logger.debug('Suppressed warning <' + self.name + '>.')
            
    def Resolve( self ):
    
        self.logger.info('Warning <' + self.name + '> has been resolved: Condition passed')
        self.modem.SendSMS(self.recipients, 'Warning <' + self.name + '> has been resolved (active since ' + self.first_issued.strftime("%Y-%m-%d %H:%M") + ').')
        self.first_issued = 0
       
    def IsIssued( self ):
    
        return (self.first_issued != 0)     # need to check with != here because > is not available for datetime objects vs. int
        
    def _on_exit( self ):
    
        self.logger.debug('Closed issue <' + self.name '>.')
