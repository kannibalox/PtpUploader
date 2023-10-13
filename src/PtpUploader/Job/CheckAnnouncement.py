import datetime
import logging
import os
import threading

from django.utils import timezone

from PtpUploader import Ptp
from PtpUploader.InformationSource.Imdb import Imdb
from PtpUploader.InformationSource.MoviePoster import MoviePoster
from PtpUploader.Job.FinishedJobPhase import FinishedJobPhase
from PtpUploader.Job.WorkerBase import WorkerBase
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpImdbInfo import PtpImdbInfo, PtpZeroImdbInfo
from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.ReleaseInfo import ReleaseInfo
from PtpUploader.Settings import Settings


logger = logging.getLogger(__name__)


class CheckAnnouncement(WorkerBase):
    def __init__(self, release_id: int, stop_requested: threading.Event):
        super().__init__(release_id, stop_requested)
        self.Phases = [
            self.__CheckAnnouncementSource,
            self.__PrepareDownload,
            self.__CheckSizeLimit,
            self.__ValidateReleaseInfo,
            self.__CheckSchedule,
            self.__CheckIfExistsOnPtp,
            self.__FillOutDetailsForNewMovieByPtpApi,
            self.__FillOutDetailsForNewMovieByExternalSources,
            self.__CheckSynopsis,
            self.__CheckCoverArt,
            self.__CheckImdbRatingAndVoteCount,
            self.__StopAutomaticJobBeforeDownloadingTorrentFile,
        ]

        # Instead of this if, it would be possible to make a totally generic downloader system through SourceBase.
        if self.ReleaseInfo.AnnouncementSourceName == "file":
            self.Phases.append(self.__DetectSceneReleaseFromFileList)
            self.Phases.append(self.__AddToPendingDownloads)
        else:
            self.Phases.extend(
                [
                    self.__CreateReleaseDirectory,
                    self.__DownloadTorrentFile,
                    self.__StopAutomaticJobIfThereAreMultipleVideosBeforeDownloading,
                    self.__DetectSceneReleaseFromFileList,
                    self.__DownloadTorrent,
                    self.__AddToPendingDownloads,
                ]
            )

        self.TorrentClient = Settings.GetTorrentClient()

    def __CheckSchedule(self):
        # User jobs skip the schedule check
        if self.ReleaseInfo.IsUserCreatedJob():
            return
        if self.ReleaseInfo.ScheduleTime == datetime.datetime.fromtimestamp(
            0, timezone.get_default_timezone()
        ):
            delay = self.ReleaseInfo.AnnouncementSource.AutomaticJobStartDelay
            if not delay:
                return
            self.ReleaseInfo.ScheduleTime = timezone.now() + datetime.timedelta(
                minutes=delay
            )
            self.ReleaseInfo.JobRunningState = ReleaseInfo.JobState.Scheduled
            self.ReleaseInfo.ErrorMessage = ""
            self.ReleaseInfo.save()
            raise PtpUploaderException(ReleaseInfo.JobState.Scheduled, "")

    def __CheckAnnouncementSource(self):
        self.ReleaseInfo.logger().info(
            "Working on announcement from '%s' with id '%s' and name '%s'."
            % (
                self.ReleaseInfo.AnnouncementSourceName,
                self.ReleaseInfo.AnnouncementId,
                self.ReleaseInfo.ReleaseName,
            )
        )

        self.ReleaseInfo.JobStartTimeUtc = datetime.datetime.utcnow()
        self.ReleaseInfo.JobRunningState = ReleaseInfo.JobState.InProgress
        self.ReleaseInfo.ErrorMessage = ""
        self.ReleaseInfo.save()

        if (
            self.ReleaseInfo.AnnouncementSource is None
            and self.ReleaseInfo.AnnouncementId is not None
        ):
            source, source_id = MyGlobals.SourceFactory.GetSourceAndIdByUrl(
                self.ReleaseInfo.AnnouncementId
            )
            if source is not None:
                self.ReleaseInfo.AnnouncementSourceName = source.Name
                self.ReleaseInfo.AnnouncementId = source_id
                self.ReleaseInfo.save()
        if self.ReleaseInfo.AnnouncementSource is None:
            raise PtpUploaderException(
                "Announcement source '%s' is unknown."
                % self.ReleaseInfo.AnnouncementSourceName
            )

        if not self.ReleaseInfo.AnnouncementSource.IsEnabled():
            raise PtpUploaderException(
                "Announcement source '%s' is disabled."
                % self.ReleaseInfo.AnnouncementSourceName
            )

    def __PrepareDownload(self):
        self.ReleaseInfo.AnnouncementSource.PrepareDownload(
            self.ReleaseInfo.logger(), self.ReleaseInfo
        )

    def __CheckSizeLimit(self):
        if (
            (not self.ReleaseInfo.IsUserCreatedJob())
            and Settings.SizeLimitForAutoCreatedJobs > 0.0
            and self.ReleaseInfo.Size > Settings.SizeLimitForAutoCreatedJobs
        ):
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored, "Ignored because of its size."
            )

    def __ValidateReleaseInfo(self):
        # Make sure we have IMDb or PTP id.
        if (not self.ReleaseInfo.ImdbId) and (not self.ReleaseInfo.PtpId):
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_MissingInfo,
                "IMDb or PTP id must be specified.",
            )

        # Make sure the source is providing a name.
        self.ReleaseInfo.ReleaseName = self.ReleaseInfo.ReleaseName.strip()
        if len(self.ReleaseInfo.ReleaseName) <= 0:
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_MissingInfo,
                "Name of the release is not specified.",
            )

        # Make sure the source is providing release source information.
        if len(self.ReleaseInfo.Source) <= 0:
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_MissingInfo,
                "Source of the release is not specified.",
            )

        # Make sure the source is providing release codec information.
        if len(self.ReleaseInfo.Codec) <= 0:
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_MissingInfo,
                "Codec of the release is not specified.",
            )

        # Make sure the source is providing release resolution type information.
        if len(self.ReleaseInfo.ResolutionType) <= 0:
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_MissingInfo,
                "Resolution type of the release is not specified.",
            )

        # HD XviDs are not allowed.
        if (not self.ReleaseInfo.IsStandardDefinition()) and (
            self.ReleaseInfo.Codec in ["XviD", "DivX"]
        ):
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_Forbidden,
                f"HD {self.ReleaseInfo.Codec}s are not allowed.",
            )

        # HD XviDs are not allowed.
        if (not self.ReleaseInfo.IsStandardDefinition()) and (
            self.ReleaseInfo.Source in ["DVD", "VHS"]
        ):
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_Forbidden,
                f"HD {self.ReleaseInfo.Source} rips are not allowed.",
            )

        # We only support VOB IFO container for DVD images.
        if self.ReleaseInfo.IsDvdImage() and self.ReleaseInfo.Container != "VOB IFO":
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_NotSupported,
                "Only VOB IFO container is supported for DVD images.",
            )

    def __CheckIfExistsOnPtp(self):
        # TODO: this is temporary here. We should support it everywhere.
        # If we are not logged in here that could mean that nothing interesting has been announcened for a while.
        Ptp.Login()

        # This could be before the Ptp.Login() line, but this way we can hopefully avoid some logging out errors.
        if self.ReleaseInfo.IsZeroImdbId():
            self.ReleaseInfo.logger().info(
                "IMDb ID is set zero, ignoring the check for existing release."
            )
            return

        movieOnPtpResult = None

        if self.ReleaseInfo.PtpId:
            movieOnPtpResult = Ptp.GetMoviePageOnPtp(
                self.ReleaseInfo.logger(), self.ReleaseInfo.PtpId
            )

            # If IMDb ID is not set, then store it, because it is needed for renaming releases coming from Cinemageddon and Cinematik.
            if (not self.ReleaseInfo.ImdbId) and len(movieOnPtpResult.ImdbId) > 0:
                self.ReleaseInfo.ImdbId = movieOnPtpResult.ImdbId
        else:
            # Try to get a PTP ID.
            movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId(
                self.ReleaseInfo.logger(), self.ReleaseInfo.ImdbId
            )
            self.ReleaseInfo.PtpId = movieOnPtpResult.PtpId

        existingRelease = movieOnPtpResult.IsReleaseExists(self.ReleaseInfo)
        if (
            existingRelease is not None
            and int(existingRelease["Id"]) > self.ReleaseInfo.DuplicateCheckCanIgnore
        ):
            raise PtpUploaderException(
                ReleaseInfo.JobState.Ignored_AlreadyExists,
                "Already exists on PTP: '%s'." % existingRelease["FullTitle"],
            )

        self.ReleaseInfo.ImdbRating = movieOnPtpResult.ImdbRating
        self.ReleaseInfo.ImdbVoteCount = movieOnPtpResult.ImdbVoteCount

    def __FillOutDetailsForNewMovieByPtpApi(self):
        # If already has a page on PTP then we don't have to do anything here.
        if self.ReleaseInfo.PtpId:
            return

        ptpImdbInfo = None
        if self.ReleaseInfo.IsZeroImdbId():
            ptpImdbInfo = PtpZeroImdbInfo()
        else:
            ptpImdbInfo = PtpImdbInfo(self.ReleaseInfo.ImdbId)

        # Title
        if len(self.ReleaseInfo.Title) > 0:
            self.ReleaseInfo.logger().info(
                "Title '%s' is already set, not getting from PTP's movie info."
                % self.ReleaseInfo.Title
            )
        else:
            self.ReleaseInfo.Title = ptpImdbInfo.GetTitle()
            if len(self.ReleaseInfo.Title) <= 0:
                raise PtpUploaderException(
                    ReleaseInfo.JobState.Ignored_MissingInfo, "Movie title is not set."
                )

        # Year
        if len(self.ReleaseInfo.Year) > 0:
            self.ReleaseInfo.logger().info(
                "Year '%s' is already set, not getting from PTP's movie info."
                % self.ReleaseInfo.Year
            )
        else:
            self.ReleaseInfo.Year = ptpImdbInfo.GetYear()
            if len(self.ReleaseInfo.Year) <= 0:
                raise PtpUploaderException(
                    ReleaseInfo.JobState.Ignored_MissingInfo, "Movie year is not set."
                )

        # Movie description
        if len(self.ReleaseInfo.MovieDescription) > 0:
            self.ReleaseInfo.logger().info(
                "Movie description is already set, not getting from PTP's movie info."
            )
        else:
            self.ReleaseInfo.MovieDescription = ptpImdbInfo.GetMovieDescription()

        # Tags
        if len(self.ReleaseInfo.Tags) > 0:
            self.ReleaseInfo.logger().info(
                "Tags '%s' are already set, not getting from PTP's movie info."
                % self.ReleaseInfo.Tags
            )
        else:
            self.ReleaseInfo.Tags = ptpImdbInfo.GetTags()
            if len(self.ReleaseInfo.Tags) <= 0:
                raise PtpUploaderException(
                    ReleaseInfo.JobState.Ignored_MissingInfo,
                    "At least one tag must be specified for a movie.",
                )

        # Cover art URL
        if self.ReleaseInfo.CoverArtUrl:
            self.ReleaseInfo.logger().info(
                "Cover art URL '%s' is already set, not getting from PTP's movie info."
                % self.ReleaseInfo.CoverArtUrl
            )
        else:
            self.ReleaseInfo.CoverArtUrl = ptpImdbInfo.GetCoverArtUrl()

        # Ignore adult movies (if force upload is not set).
        if "adult" in self.ReleaseInfo.Tags:
            if self.ReleaseInfo.IsForceUpload():
                self.ReleaseInfo.logger().info(
                    "Movie's genre is adult, but continuing due to force upload."
                )
            else:
                raise PtpUploaderException(
                    ReleaseInfo.JobState.Ignored_Forbidden, "Genre is adult."
                )

    # Uses IMDb and The Internet Movie Poster DataBase.
    def __FillOutDetailsForNewMovieByExternalSources(self):
        if self.ReleaseInfo.PtpId or self.ReleaseInfo.IsZeroImdbId():
            return

        imdbInfo = Imdb.GetInfo(self.ReleaseInfo.logger(), self.ReleaseInfo.ImdbId)

        # Ignore series (if force upload is not set).
        if imdbInfo.IsSeries:
            if self.ReleaseInfo.IsForceUpload():
                self.ReleaseInfo.logger().info(
                    "The release is a series, but continuing due to force upload."
                )
            else:
                raise PtpUploaderException(
                    ReleaseInfo.JobState.Ignored_Forbidden, "It is a series."
                )

        # PTP returns with the original title, IMDb's iPhone API returns with the international English title.
        self.ReleaseInfo.InternationalTitle = imdbInfo.Title
        if (
            self.ReleaseInfo.Title != self.ReleaseInfo.InternationalTitle
            and len(self.ReleaseInfo.InternationalTitle) > 0
            and self.ReleaseInfo.Title.find(" AKA ") == -1
        ):
            self.ReleaseInfo.Title += " AKA " + self.ReleaseInfo.InternationalTitle

        if len(self.ReleaseInfo.MovieDescription) <= 0:
            self.ReleaseInfo.MovieDescription = imdbInfo.Plot

        if not self.ReleaseInfo.CoverArtUrl:
            self.ReleaseInfo.CoverArtUrl = imdbInfo.PosterUrl
            if not self.ReleaseInfo.CoverArtUrl:
                self.ReleaseInfo.CoverArtUrl = MoviePoster.Get(
                    self.ReleaseInfo.logger(), self.ReleaseInfo.ImdbId
                )

        self.ReleaseInfo.ImdbRating = imdbInfo.ImdbRating
        self.ReleaseInfo.ImdbVoteCount = imdbInfo.ImdbVoteCount

    def __CheckSynopsis(self):
        if (
            Settings.StopIfSynopsisIsMissing
            and Settings.StopIfSynopsisIsMissing.lower() == "before_downloading"
        ):
            self.ReleaseInfo.AnnouncementSource.CheckSynopsis(logger, self.ReleaseInfo)

    def __CheckCoverArt(self):
        if (
            Settings.StopIfCoverArtIsMissing
            and Settings.StopIfCoverArtIsMissing.lower() == "before_downloading"
        ):
            self.ReleaseInfo.AnnouncementSource.CheckCoverArt(logger, self.ReleaseInfo)

    def __IsAllowedImdbRating(self):
        if Settings.StopIfImdbRatingIsLessThan == 0:
            return True

        if len(self.ReleaseInfo.ImdbRating) <= 0:
            return False

        return float(self.ReleaseInfo.ImdbRating) >= float(
            Settings.StopIfImdbRatingIsLessThan
        )

    def __IsAllowedImdbVoteCount(self):
        if Settings.StopIfImdbVoteCountIsLessThan == 0:
            return True

        if len(self.ReleaseInfo.ImdbVoteCount) <= 0:
            return False

        return int(self.ReleaseInfo.ImdbVoteCount) >= int(
            Settings.StopIfImdbVoteCountIsLessThan
        )

    def __CheckImdbRatingAndVoteCount(self):
        # Only applies to automatically created jobs.
        if self.ReleaseInfo.IsUserCreatedJob():
            return

        if not self.__IsAllowedImdbRating():
            raise PtpUploaderException(
                "Ignored because of IMDb rating: %s." % (self.ReleaseInfo.ImdbRating)
            )

        if not self.__IsAllowedImdbVoteCount():
            raise PtpUploaderException(
                "Ignored because of IMDb vote count: %s."
                % (self.ReleaseInfo.ImdbVoteCount)
            )

    def __StopAutomaticJobBeforeDownloadingTorrentFile(self):
        if (
            self.ReleaseInfo.IsUserCreatedJob()
            or self.ReleaseInfo.AnnouncementSource.StopAutomaticJob
            != "before_downloading"
        ):
            return

        raise PtpUploaderException("Stopping before downloading torrent file.")

    def __CreateReleaseDirectory(self):
        if self.ReleaseInfo.IsJobPhaseFinished(
            FinishedJobPhase.Download_CreateReleaseDirectory
        ):
            logger.info(
                "Release root path creation phase has been reached previously, not creating it again."
            )
            return

        releaseRootPath = self.ReleaseInfo.GetReleaseRootPath()
        self.ReleaseInfo.logger().info(
            "Creating release root directory at '%s'." % releaseRootPath
        )

        if os.path.exists(releaseRootPath):
            raise PtpUploaderException(
                "Release root directory '%s' already exists." % releaseRootPath
            )

        os.makedirs(releaseRootPath)

        self.ReleaseInfo.SetJobPhaseFinished(
            FinishedJobPhase.Download_CreateReleaseDirectory
        )
        self.ReleaseInfo.save()

    def __DownloadTorrentFile(self):
        if self.ReleaseInfo.SourceTorrentFilePath:
            self.ReleaseInfo.logger().info(
                "Source torrent file path is set, not downloading the file again."
            )
            return

        torrentName = (
            self.ReleaseInfo.AnnouncementSource.Name
            + " "
            + self.ReleaseInfo.ReleaseName
            + ".torrent"
        )
        sourceTorrentFilePath = os.path.join(
            self.ReleaseInfo.GetReleaseRootPath(), torrentName
        )
        self.ReleaseInfo.AnnouncementSource.DownloadTorrent(
            self.ReleaseInfo.logger(), self.ReleaseInfo, sourceTorrentFilePath
        )

        # Local variable is used temporarily to make sure that SourceTorrentFilePath is only gets stored in the database if DownloadTorrent succeeded.
        self.ReleaseInfo.SourceTorrentFilePath = sourceTorrentFilePath
        self.ReleaseInfo.save()

    def __StopAutomaticJobIfThereAreMultipleVideosBeforeDownloading(self):
        if (
            self.ReleaseInfo.IsUserCreatedJob()
            or self.ReleaseInfo.AnnouncementSource.StopAutomaticJobIfThereAreMultipleVideos
            != "beforedownloading"
        ):
            return

        self.ReleaseInfo.AnnouncementSource.CheckForMultipleFiles(self.ReleaseInfo)

    def __DetectSceneReleaseFromFileList(self):
        if self.ReleaseInfo.SceneRelease:
            return

        self.ReleaseInfo.AnnouncementSource.DetectSceneRelease(self.ReleaseInfo)

    def __DownloadTorrent(self):
        if len(self.ReleaseInfo.SourceTorrentInfoHash) > 0:
            self.ReleaseInfo.logger().info(
                "Source torrent info hash is set, not starting torent again."
            )
        else:
            self.TorrentClient.CleanTorrentFile(
                self.ReleaseInfo.logger(), self.ReleaseInfo.SourceTorrentFilePath
            )
            self.ReleaseInfo.SourceTorrentInfoHash = self.TorrentClient.AddTorrent(
                logger,
                self.ReleaseInfo.SourceTorrentFilePath,
                self.ReleaseInfo.GetReleaseDownloadPath(),
            )
            self.ReleaseInfo.JobRunningState = ReleaseInfo.JobState.InDownload
            self.ReleaseInfo.save()

    def __AddToPendingDownloads(self):
        self.ReleaseInfo.JobRunningState = ReleaseInfo.JobState.InDownload
        self.ReleaseInfo.save()
