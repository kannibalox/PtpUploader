from Source.Gft import Gft
from Source.SourceFactory import SourceFactory

from Main import Initialize, Run
from MyGlobals import MyGlobals
from Ptp import Ptp
from PtpUploaderException import *
from Settings import Settings

# TODO: temp
import urllib
import urllib2
import time
import traceback

# TODO: temp
class TestPtp:
	@staticmethod
	def __LoginInternal():
		if len( Settings.PtpUserName ) <= 0:
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Your user name is not specified.." )

		if len( Settings.PtpPassword ) <= 0:
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Your password is not specified.." )

		MyGlobals.Logger.info( "Logging in to PTP." );
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) );
		postData = urllib.urlencode( { "username": Settings.PtpUserName, "password": Settings.PtpPassword, "keeplogged": "1" } )
		request = urllib2.Request( "https://tls.passthepopcorn.me/login.php", postData );
		MyGlobals.Logger.info( "DEBUG: Before result = opener.open( request );" )
		result = opener.open( request );
		MyGlobals.Logger.info( "DEBUG: Before response = result.read();" )
		response = result.read();
		MyGlobals.Logger.info( "DEBUG: After response = result.read();" )
		TestPtp.CheckIfLoggedInFromResponse( result, response );
		MyGlobals.Logger.info( "Logged in to PTP." );

	@staticmethod
	def Login():
		try:
			TestPtp.__LoginInternal()
			return
		except PtpUploaderInvalidLoginException:
			raise
		except Exception:
			MyGlobals.Logger.exception( "Got exception in Login." )
			raise

	@staticmethod
	def __CheckIfLoggedInFromResponseLogResponse(result, responseBody):
		MyGlobals.Logger.info( "MSG: %s" % result.msg  )
		MyGlobals.Logger.info( "CODE: %s" % result.code  )
		MyGlobals.Logger.info( "URL: %s" % result.url )
		MyGlobals.Logger.info( "HEADERS: %s" % result.headers )
		MyGlobals.Logger.info( "STACK: %s" % traceback.format_stack() ) 
		MyGlobals.Logger.info( "RESPONSE BODY: %s" % responseBody ) 

	@staticmethod
	def CheckIfLoggedInFromResponse(result, responseBody):
		if responseBody.find( """<a href="login.php?act=recover">""" ) != -1:
			TestPtp.__CheckIfLoggedInFromResponseLogResponse( result, responseBody )
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Probably due to the bad user name or password." )
		
		if responseBody.find( """<p>Your IP has been banned.</p>""" ) != -1:
			TestPtp.__CheckIfLoggedInFromResponseLogResponse( result, responseBody )
			raise PtpUploaderInvalidLoginException( "Couldn't log in to PTP. Your IP has been banned." )
		
		if responseBody.find( 'action="login.php"' ) != -1:
			TestPtp.__CheckIfLoggedInFromResponseLogResponse( result, responseBody )
			raise PtpUploaderException( "Looks like you are not logged in to PTP. Probably due to the bad user name or password." )

if __name__ == '__main__':
	Initialize()
	
	# TODO: commented out temporarily
	#Ptp.Login()
	#sourceFactory = SourceFactory()
	
	# TODO: temp
	TestPtp.Login()
