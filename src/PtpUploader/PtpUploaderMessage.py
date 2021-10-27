class PtpUploaderMessageBase:
    pass


class PtpUploaderMessageStartJob(PtpUploaderMessageBase):
    def __init__(self, releaseInfoId):
        self.ReleaseInfoId = releaseInfoId


class PtpUploaderMessageStopJob(PtpUploaderMessageBase):
    def __init__(self, releaseInfoId):
        self.ReleaseInfoId = releaseInfoId


class PtpUploaderMessageNewAnnouncementFile(PtpUploaderMessageBase):
    def __init__(self, announcementFilePath):
        self.AnnouncementFilePath = announcementFilePath


class PtpUploaderMessageQuit(PtpUploaderMessageBase):
    pass
