from Source.Gft import Gft
from Source.SourceFactory import SourceFactory

from Main import Initialize, Run
from Ptp import Ptp
from Settings import Settings

if __name__ == '__main__':
	Initialize()

	print "Settings.VideoExtensionsToUpload: %s" % Settings.VideoExtensionsToUpload
	print "Settings.AdditionalExtensionsToUpload: %s" % Settings.AdditionalExtensionsToUpload
	
	print "GFT username: '%s', password: '%s'." % ( Settings.GftUserName, Settings.GftPassword )
	
	Ptp.Login()
	sourceFactory = SourceFactory()