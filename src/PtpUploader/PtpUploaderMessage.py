class PtpUploaderMessageBase:
    pass


class PtpUploaderMessageStartJob(PtpUploaderMessageBase):
    def __init__(self, releaseInfoId):
        self.ReleaseInfoId = releaseInfoId


class PtpUploaderMessageStopJob(PtpUploaderMessageBase):
    def __init__(self, releaseInfoId):
        self.ReleaseInfoId = releaseInfoId


class PtpUploaderMessageDeleteJob(PtpUploaderMessageBase):
    def __init__(self, releaseInfoId, mode):
        self.ReleaseInfoId = releaseInfoId
        self.mode = mode


class PtpUploaderMessageNewAnnouncementFile(PtpUploaderMessageBase):
    def __init__(self, announcementFilePath):
        self.AnnouncementFilePath = announcementFilePath


class PtpUploaderMessageQuit(PtpUploaderMessageBase):
    pass
