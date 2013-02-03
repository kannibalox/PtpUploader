class PtpUploaderMessageStartJob:
	def __init__(self, releaseInfoId):
		self.ReleaseInfoId = releaseInfoId
		
class PtpUploaderMessageStopJob:
	def __init__(self, releaseInfoId):
		self.ReleaseInfoId = releaseInfoId

class PtpUploaderMessageNewAnnouncementFile:
	def __init__( self, announcementFilePath ):
		self.AnnouncementFilePath = announcementFilePath

class PtpUploaderMessageQuit: pass