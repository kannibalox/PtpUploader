import datetime
import os

from django.db import models

from PtpUploader.Job.FinishedJobPhase import FinishedJobPhase
from PtpUploader.Job.JobRunningState import JobRunningState
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings


class ReleaseInfoFlags:
    # There are three categories on PTP: SD, HD and Other. The former two can figured out from the resolution type.
    # This flag is for indicating the Other ("Not main movie") category. Extras, Rifftrax, etc. belong here.
    SpecialRelease = 1 << 0

    # Release made by a scene group.
    SceneRelease = 1 << 1

    # If set, then it overrides the value returned by SourceBase.IsSingleFileTorrentNeedsDirectory.
    ForceDirectorylessSingleFileTorrent = 1 << 2

    # If this is set then the job will be the next processed job and the download will start regardless the number of maximum parallel downloads set for the source.
    StartImmediately = 1 << 3

    # Job will be stopped before uploading.
    StopBeforeUploading = 1 << 4

    TrumpableForNoEnglishSubtitles = 1 << 5
    OverrideScreenshots = 1 << 6

    PersonalRip = 1 << 7



    
class ReleaseInfo(models.Model):
    class Meta:
        app_label = 'db'
        __tablename__ = "release"

    Id = models.AutoField(primary_key=True)

    # Announcement
    AnnouncementSourceName = models.TextField(blank=True, default='')
    AnnouncementId = models.TextField(blank=True, default='')
    ReleaseName = models.TextField(blank=True, default='')

    # For PTP
    Type = models.TextField(blank=True, default='Feature Film')
    ImdbId = models.TextField(blank=True, default='')
    Directors = models.TextField(blank=True, default='')
    Title = models.TextField(blank=True, default='')
    Year = models.TextField(blank=True, default='')
    Tags = models.TextField(blank=True, default='')
    MovieDescription = models.TextField(blank=True, default='')
    CoverArtUrl = models.TextField(blank=True, default='')
    YouTubeId = models.TextField(blank=True, default='')
    MetacriticUrl = models.TextField(blank=True, default='')
    RottenTomatoesUrl = models.TextField(blank=True, default='')
    Codec = models.TextField(blank=True, default='')
    CodecOther = models.TextField(blank=True, default='')
    Container = models.TextField(blank=True, default='')
    ContainerOther = models.TextField(blank=True, default='')
    ResolutionType = models.TextField(blank=True, default='')
    Resolution = models.TextField(blank=True, default='')
    Source = models.TextField(blank=True, default='')
    SourceOther = models.TextField(blank=True, default='')
    RemasterTitle = models.TextField(blank=True, default='')
    RemasterYear = models.TextField(blank=True, default='')

    # Other
    JobStartMode = models.IntegerField(default=JobStartMode.Automatic)
    JobRunningState = models.IntegerField(default=JobRunningState.WaitingForStart)
    FinishedJobPhase = models.IntegerField(default=0)
    Flags = models.IntegerField(default=0)
    ErrorMessage = models.TextField(blank=True, default='')
    PtpId = models.TextField(blank=True, default='')
    PtpTorrentId = models.TextField(blank=True, default='')
    InternationalTitle = models.TextField(blank=True, default='')
    Nfo = models.TextField(blank=True, default='')
    SourceTorrentFilePath = models.TextField(blank=True, default='')
    SourceTorrentInfoHash = models.TextField(blank=True, default='')
    UploadTorrentCreatePath = models.TextField(blank=True, default='')
    UploadTorrentFilePath = models.TextField(blank=True, default='')
    UploadTorrentInfoHash = models.TextField(blank=True, default='')
    ReleaseDownloadPath = models.TextField(blank=True, default='')
    ReleaseUploadPath = models.TextField(blank=True, default='')
    ReleaseNotes = models.TextField(blank=True, default='')
    Screenshots = models.TextField(blank=True, default='')
    LastModificationTime = models.DateTimeField(auto_now=True)
    Size = models.IntegerField(default=0)
    Subtitles = models.TextField(blank=True, default='')
    IncludedFiles = models.TextField(blank=True, default='')
    DuplicateCheckCanIgnore = models.IntegerField(default=0)
    ScheduleTimeUtc = models.DateTimeField()

    def __init__(self, *args, **kwargs):
        # <<< These are the required fields needed for an upload to PTP.
        super().__init__(*args, **kwargs)

        self.ScheduleTimeUtc = datetime.datetime.utcnow()

        self.AnnouncementSource = None  # A class from the Source namespace.
        self.Logger = None
        self.SceneAccessDownloadUrl = ""  # Temporary store for FunFile.
        self.SourceIsAFile = False  # Used by Source.File class.
        self.ImdbRating = ""  # Not saved in the database.
        self.ImdbVoteCount = ""  # Not saved in the database.
        self.JobStartTimeUtc = datetime.datetime.utcnow()

    def IsUserCreatedJob(self):
        return (
            self.JobStartMode == JobStartMode.Manual
            or self.JobStartMode == JobStartMode.ManualForced
        )

    def IsForceUpload(self):
        return self.JobStartMode == JobStartMode.ManualForced

    def GetDirectors(self):
        if len(self.Directors) > 0:
            return self.Directors.split(", ")
        else:
            return []

    def SetDirectors(self, list):
        for name in list:
            if name.find(",") != -1:
                raise PtpUploaderException(
                    "Director name '%s' contains a comma." % name
                )

        self.Directors = ", ".join(list)

    def GetSubtitles(self):
        if len(self.Subtitles) > 0:
            return self.Subtitles.split(", ")
        else:
            return []

    def SetSubtitles(self, list):
        for id in list:
            if id.find(",") != -1:
                raise PtpUploaderException("Language id '%s' contains a comma." % id)

        self.Subtitles = ", ".join(list)

    def IsPersonalRip(self):
        return (self.Flags & ReleaseInfoFlags.PersonalRip) != 0

    def SetPersonalRip(self):
        self.Flags |= ReleaseInfoFlags.PersonalRip

    def IsSceneRelease(self):
        return (self.Flags & ReleaseInfoFlags.SceneRelease) != 0

    def SetSceneRelease(self):
        self.Flags |= ReleaseInfoFlags.SceneRelease

    def IsHighDefinition(self):
        return (
            self.ResolutionType == "720p"
            or self.ResolutionType == "1080i"
            or self.ResolutionType == "1080p"
        )

    def IsStandardDefinition(self):
        return (not self.IsHighDefinition()) and (not self.IsUltraHighDefinition())

    def IsUltraHighDefinition(self):
        return self.ResolutionType == "4K"

    def IsRemux(self):
        return "Remux" in str(self.RemasterTitle)

    def IsDvdImage(self):
        return self.Codec == "DVD5" or self.Codec == "DVD9"

    # See the description at the flag.
    def IsSpecialRelease(self):
        return (self.Flags & ReleaseInfoFlags.SpecialRelease) != 0

    # See the description at the flag.
    def SetSpecialRelease(self):
        self.Flags |= ReleaseInfoFlags.SpecialRelease

    # See the description at the flag.
    def IsForceDirectorylessSingleFileTorrent(self):
        return (self.Flags & ReleaseInfoFlags.ForceDirectorylessSingleFileTorrent) != 0

    # See the description at the flag.
    def SetForceDirectorylessSingleFileTorrent(self):
        self.Flags |= ReleaseInfoFlags.ForceDirectorylessSingleFileTorrent

    # See the description at the flag.
    def IsStartImmediately(self):
        return (self.Flags & ReleaseInfoFlags.StartImmediately) != 0

    # See the description at the flag.
    def SetStartImmediately(self):
        self.Flags |= ReleaseInfoFlags.StartImmediately

    # See the description at the flag.
    def IsStopBeforeUploading(self):
        return (self.Flags & ReleaseInfoFlags.StopBeforeUploading) != 0

    def IsTrumpableForNoEnglishSubtitles(self):
        return (self.Flags & ReleaseInfoFlags.TrumpableForNoEnglishSubtitles) != 0

    def SetTrumpableForNoEnglishSubtitles(self):
        self.Flags |= ReleaseInfoFlags.TrumpableForNoEnglishSubtitles

    def IsOverrideScreenshotsSet(self):
        return (self.Flags & ReleaseInfoFlags.OverrideScreenshots) != 0

    def SetOverrideScreenshots(self, override):
        if override:
            self.Flags |= ReleaseInfoFlags.OverrideScreenshots
        else:
            self.Flags &= ~ReleaseInfoFlags.OverrideScreenshots

    # See the description at the flag.
    def SetStopBeforeUploading(self, stop):
        if stop:
            self.Flags |= ReleaseInfoFlags.StopBeforeUploading
        else:
            self.Flags &= ~ReleaseInfoFlags.StopBeforeUploading

    def CanEdited(self):
        return (
            self.JobRunningState != JobRunningState.WaitingForStart
            and self.JobRunningState != JobRunningState.Scheduled
            and self.JobRunningState != JobRunningState.InProgress
            and self.JobRunningState != JobRunningState.Finished
        )

    def IsReleaseNameEditable(self):
        return self.CanEdited() and not self.IsJobPhaseFinished(
            FinishedJobPhase.Download_CreateReleaseDirectory
        )

    def CanResumed(self):
        return self.CanEdited()

    def CanStopped(self):
        return (
            self.JobRunningState == JobRunningState.WaitingForStart
            or self.JobRunningState == JobRunningState.Scheduled
            or self.JobRunningState == JobRunningState.InProgress
        )

    def CanDeleted(self):
        return (
            self.JobRunningState != JobRunningState.WaitingForStart
            and self.JobRunningState != JobRunningState.Scheduled
            and self.JobRunningState != JobRunningState.InProgress
        )

    def IsJobPhaseFinished(self, jobPhase):
        return (self.FinishedJobPhase & jobPhase) != 0

    def SetJobPhaseFinished(self, jobPhase):
        self.FinishedJobPhase |= jobPhase

    # Eg.: "working directory/log/job/1"
    def GetLogFilePath(self):
        return os.path.join(Settings.GetJobLogPath(), str(self.Id))

    # Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
    def GetReleaseRootPath(self):
        releasesPath = os.path.join(Settings.WorkingPath, "release")
        return os.path.join(releasesPath, self.ReleaseName)

    # Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/download/"
    def GetReleaseDownloadPath(self):
        if self.ReleaseDownloadPath:
            return self.ReleaseDownloadPath
        return os.path.join(self.GetReleaseRootPath(), "download")

    # Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/upload/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
    # It must contain the final release name because of mktor.
    def GetReleaseUploadPath(self):
        if self.ReleaseUploadPath:
            return self.ReleaseUploadPath
        path = os.path.join(self.GetReleaseRootPath(), "upload")
        return os.path.join(path, self.ReleaseName)

    def SetReleaseUploadPath(self, path):
        self.ReleaseUploadPath = path

    def IsTorrentNeedsDuplicateChecking(self, torrentId):
        return torrentId > self.DuplicateCheckCanIgnore
