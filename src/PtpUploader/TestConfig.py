from Source.SourceFactory import SourceFactory

from Main import Initialize, Run
from Ptp import Ptp
from Settings import Settings

if __name__ == '__main__':
	Initialize()
	Ptp.Login()
	sourceFactory = SourceFactory()

	print "Settings.VideoExtensionsToUpload: %s" % Settings.VideoExtensionsToUpload
	print "Settings.AdditionalExtensionsToUpload: %s" % Settings.AdditionalExtensionsToUpload