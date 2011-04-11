import codecs
import datetime
import sys
import traceback

# The reason for not using Python's logger:
# "While it might be tempting to create Logger instances on a per-connection basis, this is not a good idea because these instances are not garbage collected." 
# http://docs.python.org/library/logging.html
class Logger:
	def __init__(self, logFilePath):
		self.LogFilePath = logFilePath;

	def __Log(self, messageType, message, logException = False):
		messageTime = datetime.datetime.now().strftime( "%Y-%m-%d %H:%M:%S" );
		file = codecs.open( self.LogFilePath, "a", "utf-8" );

		exceptionMessage = None
		if logException:
			exceptionMessage = traceback.format_exc( limit = None )

		formattedMessage = None
		if exceptionMessage is None:
			formattedMessage = u"[%s] %s %s" % ( messageTime, messageType, message ) 
		else:
			formattedMessage = u"[%s] %s %s\n%s" % ( messageTime, messageType, message, exceptionMessage )

		# To avoid "UnicodeEncodeError: 'ascii' codec can't encode character" errors...  
		print formattedMessage.encode( sys.stdout.encoding, "ignore" )
		
		file.write( formattedMessage )
		file.write( "\n" )
		file.close()

	def info(self, message):
		self.__Log( u"INFO", message )
		
	def error(self, message):
		self.__Log( u"ERROR", message )
		
	def exception(self, message):
		self.__Log( u"ERROR", message, logException = True )
		
	def warning(self, message):
		self.__Log( u"WARNING", message )