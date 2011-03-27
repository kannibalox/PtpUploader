from Database import Database
from PtpUploaderException import *

class WorkerBase:
	def __init__(self, releaseInfo):
		self.ReleaseInfo = releaseInfo

	def Work(self):
		pass

	def WorkGuarded(self):
		try:
			self.Work()
		except Exception, e:
			if hasattr( e, "JobRunningState" ):
				self.ReleaseInfo.JobRunningState = e.JobRunningState
			else:
				self.ReleaseInfo.JobRunningState = JobRunningState.Failed

			self.ReleaseInfo.ErrorMessage = str( e )
			Database.DbSession.commit()
			
			e.Logger = self.ReleaseInfo.Logger
			raise