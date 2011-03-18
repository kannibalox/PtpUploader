from Job.JobManager import JobManager

from Globals import Globals
from PtpUploaderException import *

import time

class PtpUploader:
	TheJobManager = None
	
	@staticmethod
	def __GetLoggerFromException(exception):
		if hasattr( exception, "Logger" ):
			return exception.Logger
		else:
			return Globals.Logger

	@staticmethod
	def GetJobManager():
		return PtpUploader.TheJobManager

	@staticmethod
	def Work():
		Globals.Logger.info( "Entering into the main loop." )
		PtpUploader.TheJobManager = JobManager()

		while True:
			try:
				if not PtpUploader.TheJobManager.ProcessJobs():
					time.sleep( 30 ) # Sleep 30 seconds, if there was no work to do.
			except (KeyboardInterrupt, SystemExit):
				print "Exiting."
				raise
			except PtpUploaderInvalidLoginException, e:
				PtpUploader.__GetLoggerFromException( e ).exception( "Aborting." )
				break
			except Exception, e:
				PtpUploader.__GetLoggerFromException( e ).exception( "Caught exception in the main loop. Trying to continue." )