from .JobRunningState import JobRunningState

from ..Database import Database
from ..PtpUploaderException import *

class WorkerBase:
	def __init__(self, phases, jobManager, jobManagerItem):
		self.Phases = phases
		self.JobManager = jobManager 
		self.JobManagerItem = jobManagerItem
		self.ReleaseInfo = jobManagerItem.ReleaseInfo

	def __WorkInternal(self):
		for phase in self.Phases:
			if self.JobManagerItem.StopRequested:
				self.ReleaseInfo.JobRunningState = JobRunningState.Paused
				Database.DbSession.commit()
				return
				
			phase()

	def Work(self):
		try:
			self.__WorkInternal()
		except Exception as e:
			if hasattr( e, "JobRunningState" ):
				self.ReleaseInfo.JobRunningState = e.JobRunningState
			else:
				self.ReleaseInfo.JobRunningState = JobRunningState.Failed

			self.ReleaseInfo.ErrorMessage = str( e )
			Database.DbSession.commit()
			
			e.Logger = self.ReleaseInfo.Logger
			raise
