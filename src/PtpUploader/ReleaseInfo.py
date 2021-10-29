import datetime
import os
from typing import Iterator

from django.core.validators import validate_comma_separated_integer_list
from django.db import models
from django.utils import timezone
from PtpUploader.Job.FinishedJobPhase import FinishedJobPhase
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.Logger import Logger
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings


class ReleaseInfo(models.Model):
    # pylint: disable=too-many-public-methods, too-many-instance-attributes
    class Meta:
        app_label = "web"

    class JobState(models.IntegerChoices):
        WaitingForStart = 0, "Waiting for start"
        InProgress = 1, "In progress"
        Paused = 2
        Finished = 3
        Failed = 4
        Ignored = 5
        Ignored_AlreadyExists = 6, "Ignored, already exists"
        Ignored_Forbidden = 7, "Ignored, forbidden"
        Ignored_MissingInfo = 8, "Ignored, missing info"
        Ignored_NotSupported = 9, "Ignored, not supported"
        DownloadedAlreadyExists = 10, "Downloaded, already exists"
        Scheduled = 11
        InDownload = 12, "Downloading"

    class MediaType(models.TextChoices):
        feature = ("Feature Film", "Feature Film")
        short = ("Short Film", "Short Film")
        miniseries = "Miniseries"
        standup = ("Stand-up Comedy", "Stand-up Comedy")
        concert = "Concert"
        live = ("Live Performance", "Live Performance")
        collection = ("Movie Collection", "Movie Collection")

    class CodecChoices(models.TextChoices):
        XVID = ("XviD", "XviD")
        DIVX = ("DivX", "DivX")
        H_264 = ("H.264", "H.264")
        X264 = ("x264", "x264")
        H_265 = ("H.265", "H.265")
        X265 = ("x265", "x265")
        DVD5 = ("DVD5", "DVD5")
        DVD9 = ("DVD9", "DVD9")
        BD25 = ("BD25", "BD25")
        BD50 = ("BD50", "BD50")
        BD66 = ("BD66", "BD66")
        BD100 = ("BD100", "BD100")
        Other = ("Other", "Other")

    class ContainerChoices(models.TextChoices):
        AVI = ("AVI", "AVI")
        MPG = ("MPG", "MPG")
        MKV = ("MKV", "MKV")
        MP4 = ("MP4", "MP4")
        VOB_IFO = ("VOB IFO", "VOB IFO")
        ISO = ("ISO", "ISO")
        M2TS = ("m2ts", "m2ts")
        Other = ("Other", "Other")

    class ResolutionChoices(models.TextChoices):
        NTSC = ("NTSC", "NTSC")
        PAL = ("PAL", "PAL")
        r480p = ("480p", "480p")
        r576p = ("576p", "576p")
        r720p = ("720p", "720p")
        r1080i = ("1080i", "1080i")
        r1080p = ("1080p", "1080p")
        r2160p = ("2160p", "2160p")
        Other = ("Other", "Other")

    class SourceChoices(models.TextChoices):
        Bluray = ("Blu-ray", "Blu-ray")
        DVD = ("DVD", "DVD")
        WEB = ("WEB", "WEB")
        HDDVD = ("HD-DVD", "HD-DVD")
        HDTV = ("HDTV", "HDTV")
        TV = ("TV", "TV")
        VHS = ("VHS", "VHS")
        Other = ("Other", "Other")

    class TrumpableReasons(models.IntegerChoices):
        NO_ENGLISH_SUBS = 14
        HARDCODED_SUBS = 4

    objects: models.manager.Manager

    Id = models.AutoField(primary_key=True)

    # Announcement
    AnnouncementSourceName = models.TextField(blank=True, default="")
    AnnouncementId = models.TextField(blank=True, default="")
    ReleaseName = models.TextField(blank=True, default="")

    # For PTP
    Type = models.TextField(blank=True, default="Feature Film")
    ImdbId = models.TextField(blank=True, default="")
    Directors = models.TextField(blank=True, default="")
    Title = models.TextField(blank=True, default="")
    Year = models.TextField(blank=True, default="")
    MovieDescription = models.TextField(blank=True, default="")
    CoverArtUrl = models.TextField(blank=True, default="")
    YouTubeId = models.TextField(blank=True, default="")
    MetacriticUrl = models.TextField(blank=True, default="")
    RottenTomatoesUrl = models.TextField(blank=True, default="")
    Codec = models.TextField(blank=True, default="")
    CodecOther = models.TextField(blank=True, default="")
    Container = models.TextField(blank=True, default="")
    ContainerOther = models.TextField(blank=True, default="")
    ResolutionType = models.TextField(blank=True, default="")
    Resolution = models.TextField(blank=True, default="")
    Source = models.TextField(blank=True, default="")
    SourceOther = models.TextField(blank=True, default="")
    RemasterTitle = models.TextField(blank=True, default="")
    RemasterYear = models.TextField(blank=True, default="")

    # Other
    JobStartMode = models.IntegerField(default=JobStartMode.Automatic)
    JobRunningState = models.IntegerField(
        choices=JobState.choices, default=JobState.WaitingForStart
    )
    FinishedJobPhase = models.IntegerField(default=0)
    Tags = models.TextField(blank=True, default="")
    ErrorMessage = models.TextField(blank=True, default="")
    PtpId = models.TextField(blank=True, default="")
    PtpTorrentId = models.TextField(blank=True, default="")
    InternationalTitle = models.TextField(blank=True, default="")
    Nfo = models.TextField(blank=True, default="")
    SourceTorrentFilePath = models.TextField(blank=True, default="")
    SourceTorrentInfoHash = models.TextField(blank=True, default="")
    UploadTorrentCreatePath = models.TextField(blank=True, default="")
    UploadTorrentFilePath = models.TextField(blank=True, default="")
    UploadTorrentInfoHash = models.TextField(blank=True, default="")
    ReleaseDownloadPath = models.TextField(blank=True, default="")
    ReleaseUploadPath = models.TextField(blank=True, default="")
    ReleaseNotes = models.TextField(blank=True, default="")
    Screenshots = models.TextField(blank=True, default="")
    LastModificationTime = models.DateTimeField(auto_now=True)
    Size = models.IntegerField(default=0)
    Subtitles = models.JSONField(blank=True, default=list)  # CSV of subtitle IDs
    IncludedFiles = models.TextField(blank=True, default="")
    DuplicateCheckCanIgnore = models.IntegerField(default=0)
    ScheduleTimeUtc = models.DateTimeField(default=timezone.now, null=True)
    Trumpable = models.JSONField(blank=True, default=list)  # CSV of trump IDs
    SpecialRelease = models.BooleanField(default=False)
    # Release made by a scene group.
    SceneRelease = models.BooleanField(default=False)
    # If set, then it overrides the value returned by SourceBase.IsSingleFileTorrentNeedsDirectory.
    ForceDirectorylessSingleFileTorrent = models.BooleanField(default=False)
    # If this is set then the job will be the next processed job and the download will start regardless the number of maximum parallel downloads set for the source.
    StartImmediately = models.BooleanField(default=False)
    # Job will be stopped before uploading.
    StopBeforeUploading = models.BooleanField(default=False)
    OverrideScreenshots = models.BooleanField(default=False)
    PersonalRip = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        # <<< These are the required fields needed for an upload to PTP.
        super().__init__(*args, **kwargs)

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
        return []

    def SetDirectors(self, names):
        for name in names:
            if name.find(",") != -1:
                raise PtpUploaderException(
                    "Director name '%s' contains a comma." % name
                )

        self.Directors = ", ".join(list)

    def GetSubtitles(self):
        if self.Subtitles:
            return [s.trim for s in self.Subtitles.split(",")]
        return []

    def SetSubtitles(self, sub_ids: Iterator[str]):
        for sub_id in sub_ids:
            sub_id = sub_id.strip()
            if sub_id.find(",") != -1:
                raise PtpUploaderException(
                    "Language id '%s' contains a comma." % sub_id
                )

        self.Subtitles = ",".join(sub_ids)

    def IsPersonalRip(self):
        return self.PersonalRip

    def SetPersonalRip(self):
        self.PersonalRip = True

    def IsSceneRelease(self):
        return self.SceneRelease

    def SetSceneRelease(self):
        self.SceneRelease = True

    def IsHighDefinition(self):
        return (
            self.ResolutionType == "720p"
            or self.ResolutionType == "1080i"
            or self.ResolutionType == "1080p"
        )

    def IsStandardDefinition(self):
        return (not self.IsHighDefinition()) and (not self.IsUltraHighDefinition())

    def IsUltraHighDefinition(self):
        return self.ResolutionType == "4K" or self.ResolutionType == "2160p"

    def IsRemux(self):
        return "Remux" in str(self.RemasterTitle)

    def IsDvdImage(self):
        return self.Codec == "DVD5" or self.Codec == "DVD9"

    # See the description at the flag.
    def IsSpecialRelease(self):
        return self.SpecialRelease

    # See the description at the flag.
    def SetSpecialRelease(self):
        self.SpecialRelease = True

    # See the description at the flag.
    def IsForceDirectorylessSingleFileTorrent(self):
        return self.ForceDirectorylessSingleFileTorrent

    # See the description at the flag.
    def SetForceDirectorylessSingleFileTorrent(self):
        self.ForceDirectorylessSingleFileTorrent = True

    # See the description at the flag.
    def IsStartImmediately(self):
        return self.StartImmediately

    # See the description at the flag.
    def SetStartImmediately(self):
        self.StartImmediately = True

    def IsStopBeforeUploading(self):
        return self.StopBeforeUploading

    def IsTrumpableForNoEnglishSubtitles(self):
        return self.TrumpableReasons.NO_ENGLISH_SUBS in self.Trumpable

    def SetTrumpableForNoEnglishSubtitles(self):
        if self.TrumpableReasons.NO_ENGLISH_SUBS not in self.Trumpable:
            self.Trumpable += [self.TrumpableReasons.NO_ENGLISH_SUBS]

    def IsTrumpableForHardcodedSubtitles(self):
        return self.TrumpableReasons.HARDCODED_SUBS in self.Trumpable

    def SetTrumpableForHardcodedSubtitles(self):
        if self.TrumpableReasons.HARDCODED_SUBS not in self.Trumpable:
            self.Trumpable += [self.TrumpableReasons.HARDCODED_SUBS]

    def IsOverrideScreenshotsSet(self) -> bool:
        return self.OverrideScreenshots

    def SetOverrideScreenshots(self, override: bool):
        self.OverrideScreenshots = override

    # See the description at the flag.
    def SetStopBeforeUploading(self, stop: bool):
        self.StopBeforeUploading = stop

    def CanEdited(self):
        return self.JobRunningState not in [
            self.JobState.WaitingForStart,
            self.JobState.Scheduled,
            self.JobState.InProgress,
            self.JobState.InDownload,
            self.JobState.Finished,
        ]

    def IsReleaseNameEditable(self):
        return self.CanEdited() and not self.IsJobPhaseFinished(
            FinishedJobPhase.Download_CreateReleaseDirectory
        )

    def CanResumed(self):
        return self.CanEdited()

    def CanStopped(self):
        return self.JobRunningState in [
            self.JobState.WaitingForStart,
            self.JobState.Scheduled,
            self.JobState.InDownload,
            self.JobState.InProgress,
        ]

    def CanDeleted(self):
        return not self.CanStopped()

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

    def IsTorrentNeedsDuplicateChecking(self, torrentId):
        return torrentId > self.DuplicateCheckCanIgnore

    def IsZeroImdbId(self):
        return self.ImdbId == "0"

    def GetPtpTorrentId(self):
        return self.PtpTorrentId

    def HasImdbId(self):
        return len(self.ImdbId) > 0

    def SetZeroImdbId(self):
        self.ImdbId = "0"

    def HasPtpId(self):
        return len(self.PtpId) > 0

    def HasPtpTorrentId(self):
        return len(self.PtpTorrentId) > 0

    def IsSynopsisSet(self):
        return len(self.MovieDescription) > 0

    def IsReleaseNameSet(self):
        return len(self.ReleaseName) > 0

    def IsCodecSet(self):
        return len(self.Codec) > 0

    def IsContainerSet(self):
        return len(self.Container) > 0

    def IsSourceSet(self):
        return len(self.Source) > 0

    @property
    def Logger(self):
        return Logger(self.GetLogFilePath())

    @property
    def AnnouncementSource(self):
        return MyGlobals.SourceFactory.GetSource(self.AnnouncementSourceName)
