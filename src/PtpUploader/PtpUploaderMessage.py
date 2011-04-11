class PtpUploaderMessageStartJob:
	def __init__(self, releaseInfoId):
		self.ReleaseInfoId = releaseInfoId
		
class PtpUploaderMessageStopJob:
	def __init__(self, releaseInfoId):
		self.ReleaseInfoId = releaseInfoId
		
class PtpUploaderMessageQuit: pass