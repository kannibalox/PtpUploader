from Source.Gft import Gft
from Source.SourceFactory import SourceFactory

from Main import Initialize, Run
from MyGlobals import MyGlobals
from Ptp import Ptp
from Settings import Settings

# TODO: temp
import urllib
import urllib2

# TODO: temp
class TestGft:
	@staticmethod
	def Login():
		MyGlobals.Logger.info( "Logging in to GFT." );
		
		# GFT stores a cookie when login.php is loaded that is needed for takeloin.php. 
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		result = opener.open( "http://www.thegft.org/login.php" )
		response = result.read()
		MyGlobals.Logger.info( response )

		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": Settings.GftUserName, "password": Settings.GftPassword } )
		result = opener.open( "http://www.thegft.org/takelogin.php", postData )
		response = result.read()
		MyGlobals.Logger.info( "\n" )
		MyGlobals.Logger.info( "-" * 80 )
		MyGlobals.Logger.info( "\n" )
		MyGlobals.Logger.info( response )
		TestGft.CheckIfLoggedInFromResponse( response );
	
	@staticmethod
	def CheckIfLoggedInFromResponse(response):
		if response.find( """action='takelogin.php'""" ) != -1 or response.find( """<a href='login.php'>Back to Login</a>""" ) != -1:
			raise PtpUploaderException( "Looks like you are not logged in to GFT. Probably due to the bad user name or password in settings." )


if __name__ == '__main__':
	Initialize()
	
	# TODO: commented out temporarily
	#Ptp.Login()
	#sourceFactory = SourceFactory()
	
	# TODO: temp
	TestGft.Login()