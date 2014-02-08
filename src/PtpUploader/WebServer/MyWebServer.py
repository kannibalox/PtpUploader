from WebServer import app

from MyGlobals import MyGlobals
from Settings import Settings

from cherrypy import wsgiserver
import threading

class MyWebServer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__( self, name = "WebServerThread" )
		self.CherryPyServer = None 
		
	def run(self):
		#app.config[ "DEBUG" ] = True
		
		host, separator, port = Settings.WebServerAddress.rpartition( ":" )
		if len( host ) <= 0:
			host = "127.0.0.1"
		
		if len( port ) > 0:
			port = int( port )
		else:
			port = 5500

		app.logger.addHandler( MyGlobals.Logger )

		# We are using CherryPy because there is no way to stop Flask's built-in test server.
		# See: https://github.com/mitsuhiko/werkzeug/issues#issue/36

		if len( Settings.WebServerSslCertificatePath ) > 0 and len( Settings.WebServerSslPrivateKeyPath ) > 0:
			MyGlobals.Logger.info( "Starting webserver on https://%s:%s." % ( host, port ) )
			wsgiserver.CherryPyWSGIServer.ssl_certificate = Settings.WebServerSslCertificatePath
			wsgiserver.CherryPyWSGIServer.ssl_private_key = Settings.WebServerSslPrivateKeyPath
		else:
			MyGlobals.Logger.info( "Starting webserver on http://%s:%s." % ( host, port ) )

		dispatcher = wsgiserver.WSGIPathInfoDispatcher( { '/': app } )
		self.CherryPyServer = wsgiserver.CherryPyWSGIServer( ( host, port ), dispatcher )
		self.CherryPyServer.start()

	def StopServer(self):
		MyGlobals.Logger.info( "Stopping webserver." )

		self.CherryPyServer.stop()
		self.join()