from Database import Database
from Globals import Globals
from ServerMain import app
from Settings import Settings

from cherrypy import wsgiserver
import threading

class WebServer(threading.Thread):
	def __init__(self):
		self.CherryPyServer = None 
		threading.Thread.__init__( self, name = "WebServerThread" )
		
	def run(self):
		if self.__CanStartWebServer():
			self.__StartServer()
		else:
			print "Web server is not running because username or passowrd is not set in the settings."

	@staticmethod
	def __CanStartWebServer():
		return len( Settings.WebServerUsername ) > 0 and len( Settings.WebServerPassword ) > 0
		
	def __StartServer(self):
		app.config[ "DEBUG" ] = True
		
		host, separator, port = Settings.WebServerAddress.rpartition( ":" )
		if len( host ) <= 0:
			host = "127.0.0.1"
		
		if len( port ) > 0:
			port = int( port )
		else:
			port = 5000
		
		# We are using CherryPy because there is no way to stop Flask's built-in test server.
		# See: https://github.com/mitsuhiko/werkzeug/issues#issue/36
		dispatcher = wsgiserver.WSGIPathInfoDispatcher( { '/': app } )
		self.CherryPyServer = wsgiserver.CherryPyWSGIServer( ( host, port ), dispatcher )
		self.CherryPyServer.start()

	def StopServer(self):
		if self.__CanStartWebServer():
			self.CherryPyServer.stop()
			
		self.join()

@app.after_request
def ShutdownSession(response):
	Database.DbSession.remove()
	return response