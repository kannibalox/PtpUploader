class PtpUploaderMessageStartJob:
	def __init__(self, releaseInfoId):
		self.ReleaseInfoId = releaseInfoId
		
class PtpUploaderMessageCancelJob:
	def __init__(self, releaseInfoId):
		self.ReleaseInfoId = releaseInfoId
		
#class PtpUploaderMessageQuit: pass