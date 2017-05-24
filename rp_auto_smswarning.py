import logging
import datetime

class SmsWarning:
    
    first_issued = 0    # track since when the current warning condition is active
    last_issued = 0     # track when a notification was last sent out
    
    def __init__( self, name, modem, recipients, suppress ):
    
        self.logger = logging.getLogger('rp_auto_ctrl')   # tie into the global rp_auto_ctrl logger. \ch: unfortunately this means that logging messages have 'SmsWarning' as module descriptor. Attempting to overwrite %(module) results in an error. Could be circumvented with lr=logging.makeLogRecord(), self.logger.handle(lr) --- but should we?
        self.name = name          # the identifier
        self.suppress = suppress  # the suppression time of the warning, in seconds
        self.modem = modem        # the sms modem
        self.recipients = recipients    # the recipients string, passed directly to the modem's SendSMS() method

    def Send( self, message ):

        self.logger.warning('WARN[' + name + ']: ' + message)   # \ch: might be better to separate logger() handling of warning messages from this module's sms sending
        if not self.first_issued > 0:
            self.first_issued=datetime.datetime.now()
        if (datetime.datetime.now() - self.last_issued).total_seconds() >= self.suppress :
            self.modem.SendSMS(self.recipients, 'WARN[' + name + '] active since ' + first_issued.strftime("%Y-%m-%d %H:%M") + ': ' + message)
            self.last_issued = datetime.datetime.now()
        else:
            self.logger.debug('Suppressed warning ' + name + ' ')
            
    def Resolve( self ):    # \ch: or some such name -- indicated that warning condition is no longer fulfilled, 
    
        self.logger.info('WARN[' + name + ']: condition passed')
        self.modem.SendSMS(self.recipients, 'WARN[' + name + '] no longer triggered, was active since ' + first_issued.strftime("%Y-%m-%d %H:%M"))
        self.first_issued = 0 # reset "warning active" indicator
        
        