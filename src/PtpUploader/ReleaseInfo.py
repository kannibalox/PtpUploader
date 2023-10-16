import datetime
import logging
import os

from pathlib import Path
from typing import Iterator, List

from django.db import models
from django.utils import timezone
from unidecode import unidecode

from PtpUploader.Job.FinishedJobPhase import FinishedJobPhase
from PtpUploader.Job.JobStartMode import JobStartMode
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings, config
from PtpUploader.release_extractor import find_allowed_files


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

    class TypeChoices(models.TextChoices):
        feature = ("Feature Film", "Feature Film")
        short = ("Short Film", "Short Film")
        miniseries = ("Miniseries", "Miniseries")
        standup = ("Stand-up Comedy", "Stand-up Comedy")
        concert = ("Concert", "Concert")
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
        __empty__ = "---"

    class ContainerChoices(models.TextChoices):
        AVI = ("AVI", "AVI")
        MPG = ("MPG", "MPG")
        MKV = ("MKV", "MKV")
        MP4 = ("MP4", "MP4")
        VOB_IFO = ("VOB IFO", "VOB IFO")
        ISO = ("ISO", "ISO")
        M2TS = ("m2ts", "m2ts")
        Other = ("Other", "Other")
        __empty__ = "---"

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
        __empty__ = "---"

    class SourceChoices(models.TextChoices):
        Bluray = ("Blu-ray", "Blu-ray")
        DVD = ("DVD", "DVD")
        WEB = ("WEB", "WEB")
        HDDVD = ("HD-DVD", "HD-DVD")
        HDTV = ("HDTV", "HDTV")
        TV = ("TV", "TV")
        VHS = ("VHS", "VHS")
        Other = ("Other", "Other")
        __empty__ = "---"

    class TrumpableReasons(models.IntegerChoices):
        NO_ENGLISH_SUBS = 14
        HARDCODED_SUBS = 4

    objects: models.manager.Manager  # helps to find some typing errors

    Id = models.AutoField(primary_key=True)

    # Announcement
    AnnouncementSourceName = models.TextField(blank=True, default="")
    AnnouncementId = models.TextField(blank=True, default="")
    ReleaseName = models.TextField(blank=True, default="")

    # For PTP
    Type = models.TextField(
        blank=True, default=TypeChoices.feature, choices=TypeChoices.choices
    )
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
    Screenshots = models.JSONField(blank=True, default=dict)
    # Mediainfo is pretty quick even for large files, BDInfo can be much rougher (and
    # produces less data), so let's cache it.
    BdInfo = models.JSONField(blank=True, default=dict)
    LastModificationTime = models.DateTimeField(auto_now=True)
    Size = models.BigIntegerField(default=0)
    Subtitles = models.JSONField(blank=True, default=list)  # CSV of subtitle IDs
    IncludedFiles = models.TextField(
        blank=True, default=""
    )  # Deprecated, to be removed at a later date
    # A list of include files, relative to the upload path
    IncludedFileList = models.JSONField(blank=True, default=list)
    DuplicateCheckCanIgnore = models.IntegerField(default=0)
    ScheduleTime = models.DateTimeField(
        default=datetime.datetime.fromtimestamp(0, timezone.get_default_timezone()),
        null=True,
    )
    Trumpable: List[int] = models.JSONField(
        blank=True, default=list
    )  # CSV of trump IDs
    SpecialRelease = models.BooleanField(default=False)
    # Release made by a scene group.
    SceneRelease = models.BooleanField(default=False)
    # If set, then it overrides the value returned by
    # SourceBase.IsSingleFileTorrentNeedsDirectory
    ForceDirectorylessSingleFileTorrent = models.BooleanField(default=False)
    # If this is set then the job will be the next processed job and
    # the download will start regardless the number of maximum
    # parallel downloads set for the source.
    StartImmediately = models.BooleanField(default=False)
    # Job will be stopped before uploading.
    StopBeforeUploading = models.BooleanField(default=False)
    OverrideScreenshots = models.BooleanField(default=False)
    PersonalRip = models.BooleanField(default=False)

    def __init__(self, *args, **kwargs):
        # <<< These are the required fields needed for an upload to PTP.
        super().__init__(*args, **kwargs)

        self.SceneAccessDownloadUrl = ""  # Temporary store for FunFile.
        self.ImdbRating = ""  # Not saved in the database.
        self.ImdbVoteCount = ""  # Not saved in the database.
        self.JobStartTimeUtc = datetime.datetime.utcnow()
        self.__logger = None  # Holds a dedicated logger when needed

    def IsUserCreatedJob(self):
        return self.JobStartMode in [JobStartMode.Manual, JobStartMode.ManualForced]

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

        self.Directors = ", ".join(names)

    def SetSubtitles(self, sub_ids: Iterator[int]):
        self.Subtitles = sub_ids

    def IsSceneRelease(self):
        return self.SceneRelease

    def SetSceneRelease(self):
        self.SceneRelease = True

    def IsHighDefinition(self):
        return self.ResolutionType in ["720p", "1080i", "1080p"]

    def IsStandardDefinition(self):
        return (not self.IsHighDefinition()) and (not self.IsUltraHighDefinition())

    def IsUltraHighDefinition(self):
        return self.ResolutionType in ["4K", "2160p"]

    def IsRemux(self):
        return "Remux" in str(self.RemasterTitle)

    def IsDvdImage(self):
        return self.Codec in ["DVD5", "DVD9"]

    def IsBlurayImage(self):
        return str(self.Codec).startswith("BD")

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

    def SetIncludedFileList(self, overwrite=False):
        if self.SourceIsAFile():
            self.IncludedFileList = [self.GetReleaseUploadPath()]
            return
        if self.IncludedFileList and not overwrite:
            return
        fileList = []
        relPath = Path(self.GetReleaseUploadPath())
        vids, addtls = find_allowed_files(relPath)
        fileList.extend([str(v.relative_to(relPath)) for v in vids])
        fileList.extend([str(a.relative_to(relPath)) for a in addtls])
        self.IncludedFileList = fileList

    def VideosFiles(self):
        if self.SourceIsAFile():
            return self.GetReleaseUploadPath()
        self.SetIncludedFileList()
        for f in self.IncludedFileList:
            if Path(f).suffix.lower().strip(".") in config.uploader.video_files:
                yield Path(self.GetReleaseUploadPath(), f)

    def AdditionalFiles(self):
        if self.SourceIsAFile():
            return self.GetReleaseUploadPath()
        self.SetIncludedFileList()
        for f in self.IncludedFileList:
            if Path(f).suffix.lower().strip(".") in config.uploader.additional_files:
                yield Path(self.GetReleaseUploadPath(), f)

    def CanDeleted(self):
        return not self.CanStopped()

    def IsJobPhaseFinished(self, jobPhase):
        return (self.FinishedJobPhase & jobPhase) != 0

    def SetJobPhaseFinished(self, jobPhase):
        self.FinishedJobPhase |= jobPhase

    # Eg.: "working directory/release/Dark.City.1998.Directors.Cut.720p.BluRay.x264-SiNNERS/"
    def GetReleaseRootPath(self):
        return Path(Settings.WorkingPath, "release", self.ReleaseName)

    def SourceIsAFile(self):
        return Path(self.GetReleaseDownloadPath()).is_file()

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
        return os.path.join(
            self.GetReleaseRootPath(), "upload", unidecode(self.ReleaseName)
        )

    def resetTorrentCreated(self):
        tfile = Path(self.UploadTorrentFilePath)
        if tfile.is_file():
            tfile.unlink()
        self.UploadTorrentFilePath = ""
        self.UploadTorrentCreatePath = ""

    def IsZeroImdbId(self):
        return self.ImdbId == "0"

    @property
    def AnnouncementSource(self):
        return MyGlobals.SourceFactory.GetSource(self.AnnouncementSourceName)

    def logger(self, logger=None):
        if self.__logger is None:
            if logger is None:
                logger = logging.getLogger(f"PtpUploader.ReleaseInfo.Release{self.Id}")
            self.__logger = logging.LoggerAdapter(logger, {"release_id": self.Id})
        return self.__logger
