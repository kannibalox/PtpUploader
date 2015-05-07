from WebServer import app

from MyGlobals import MyGlobals
from Settings import Settings

import logging
import threading

class MyWebServer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__( self, name = "WebServerThread" )
		
	def run(self):
		host, separator, port = Settings.WebServerAddress.rpartition( ":" )
		if len( host ) <= 0:
			host = "127.0.0.1"
		
		if len( port ) > 0:
			port = int( port )
		else:
			port = 5500

		app.logger.addHandler( MyGlobals.Logger )

		# By default werkzeug logs all requests.
		werkzeugLogger = logging.getLogger( 'werkzeug' )
		werkzeugLogger.setLevel( logging.ERROR )

		sslContext = None

		if len( Settings.WebServerSslCertificatePath ) > 0 and len( Settings.WebServerSslPrivateKeyPath ) > 0:
			MyGlobals.Logger.info( "Starting webserver on https://%s:%s." % ( host, port ) )
			sslContext = ( Settings.WebServerSslCertificatePath, Settings.WebServerSslPrivateKeyPath )
		else:
			MyGlobals.Logger.info( "Starting webserver on http://%s:%s." % ( host, port ) )

		app.run( host, port, debug = False, use_reloader = False, ssl_context = sslContext )

	def StopServer(self):
		MyGlobals.Logger.info( "Stopping webserver." )

		self.join()
