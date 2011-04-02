from Job.WorkerThread import WorkerThread

from PtpUploaderMessage import *

import Queue
import threading

class PtpUploader:
	def __init__(self):
		self.WaitEvent = threading.Event()
		self.StopRequested = False
		self.MessageQueue = Queue.Queue() # Contains class instances from PtpUploaderMessage.
		self.WorkerThread = WorkerThread()

	def RequestStop(self):
		self.StopRequested = True
		self.WaitEvent.set()

	def AddMessage(self, message):
		self.MessageQueue.put( message )
		self.WaitEvent.set()
		
	def __ProcessMessages(self):
		while not self.MessageQueue.empty():
			message = self.MessageQueue.get()
			if isinstance( message, PtpUploaderMessageStartJob ):
				self.WorkerThread.RequestStartJob( message.ReleaseInfoId )
			elif isinstance( message, PtpUploaderMessageCancelJob ):
				self.WorkerThread.RequestStopJob( message.ReleaseInfoId )

	def __MessageLoop(self):
		print "Entering into message loop."

		while not self.StopRequested:
			self.WaitEvent.wait()
			self.WaitEvent.clear()
			self.__ProcessMessages()

	def Work(self):
		self.WorkerThread.StartWorkerThread()
		self.__MessageLoop()
		self.WorkerThread.StopWorkerThread()