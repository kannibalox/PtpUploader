from Job.JobManager import JobManager

from Globals import Globals
from PtpUploaderException import *

import time

class PtpUploader2:
	@staticmethod
	def __GetLoggerFromException(exception):
		if hasattr( exception, "Logger" ):
			return exception.Logger
		else:
			return Globals.Logger

	@staticmethod
	def Work():
		Globals.Logger.info( "Entering into the main loop." )
		jobManager = JobManager()

		while True:
			try:
				if not jobManager.ProcessJobs():
					time.sleep( 30 ) # Sleep 30 seconds, if there was no work to do.
			except PtpUploaderInvalidLoginException, e:
				PtpUploader2.__GetLoggerFromException( e ).exception( "Aborting." )
				break
			except Exception, e:
				PtpUploader2.__GetLoggerFromException( e ).exception( "Caught exception in the main loop. Trying to continue." )