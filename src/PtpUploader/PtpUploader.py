from InformationSource.Imdb import Imdb
from InformationSource.MoviePoster import MoviePoster
from Source.SourceFactory import SourceFactory
from Tool.MakeTorrent import MakeTorrent
from Tool.MediaInfo import MediaInfo
from Tool.Rtorrent import Rtorrent
from Tool.ScreenshotMaker import ScreenshotMaker

from AnnouncementWatcher import *
from Globals import Globals
from ImageUploader import ImageUploader
from Ptp import Ptp
from PtpUploaderException import PtpUploaderException
from PtpUploadInfo import PtpUploadInfo
from ReleaseExtractor import ReleaseExtractor
from ReleaseInfo import ReleaseInfo
from Settings import Settings

import os
import time

class PtpUploader:
	def __init__(self):
		self.SourceFactory = SourceFactory()
		self.PendingAnnouncements = AnnouncementWatcher.GetPendingAnnouncements( self.SourceFactory ) # Contains Announcement
		self.PendingDownloads = [] # Contains ReleaseInfo
		self.Rtorrent = Rtorrent()

	def __IsSourceAvailable(self, source):
		runningDownloads = 0
		for releaseInfo in self.PendingDownloads:
			if releaseInfo.Announcement.Source.Name == source.Name:
				runningDownloads += 1
		
		return runningDownloads < source.MaximumParallelDownloads

	def __GetAnnouncementToProcess(self):
		announcementToHandle = None
		
		# First check if we can process anything from the pending announcments.
		for announcementIndex in range( len( self.PendingAnnouncements ) ):
			if self.__IsSourceAvailable( self.PendingAnnouncements[ announcementIndex ].Source ):
				announcementToHandle = self.PendingAnnouncements.pop( announcementIndex )
				announcementToHandle.MoveToProcessed()
				break

		if announcementToHandle:
			return announcementToHandle

		# Get new announcements, check if we can process anything from it, and add the others to the pending list. 		
		newAnnouncements = AnnouncementWatcher.GetNewAnnouncements( self.SourceFactory )
		for announcementIndex in range( len( newAnnouncements ) ):
			announcement = newAnnouncements[ announcementIndex ]
			if ( not announcementToHandle ) and self.__IsSourceAvailable( announcement.Source ):
				announcementToHandle = announcement
				announcementToHandle.MoveToProcessed()
			else:
				announcement.MoveToPending()
				self.PendingAnnouncements.append( announcement )				

		return announcementToHandle 

	def __CheckAnnouncementInternal(self, announcement):
		logger = announcement.Logger
		logger.info( "Working on announcement from '%s' with id '%s' and name '%s'." % ( announcement.Source.Name, announcement.AnnouncementId, announcement.ReleaseName ) );

		releaseInfo = announcement.Source.PrepareDownload( logger, announcement );
		if releaseInfo is None:
			return None;
		
		# Make sure we have the IMDb id.
		if len( releaseInfo.GetImdbId() ) <= 0:
			logger.error( "IMDb id can't be found." );
			return None;
	
		# Make sure the source is providing a name.
		if len( releaseInfo.Announcement.ReleaseName ) <= 0:
			logger.error( "Name of the release is not specified." );
			return None;		

		# Make sure the source is providing release quality information.
		if len( releaseInfo.PtpUploadInfo.Quality ) <= 0:
			logger.error( "Quality of the release is not specified." );
			return None;		

		# Make sure the source is providing release source information.
		if len( releaseInfo.PtpUploadInfo.Source ) <= 0:
			logger.error( "Source of the release is not specified." );
			return None;		

		# Make sure the source is providing release codec information.
		if len( releaseInfo.PtpUploadInfo.Codec ) <= 0:
			logger.error( "Codec of the release is not specified." );
			return None;		

		# Make sure the source is providing release resolution type information.
		if len( releaseInfo.PtpUploadInfo.ResolutionType ) <= 0:
			logger.error( "Resolution type of the release is not specified." );
			return None;		
	
		# TODO: this is temporary here. We should support it everywhere.
		# If we are not logged in here that could mean that nothing interesting has been announcened for a while. 
		Ptp.Login();

		movieOnPtpResult = Ptp.GetMoviePageOnPtp( logger, releaseInfo.GetImdbId() );

		# If this is an automatic announcement then we have to check if is it already on PTP.
		if not announcement.IsManualAnnouncement:
			existingRelease = movieOnPtpResult.IsReleaseExists( releaseInfo )
			if existingRelease is not None:
				logger.info( "Release '%s' already exists on PTP. Skipping upload because of format '%s'." % ( announcement.ReleaseName, existingRelease ) );
				return None;

		# If this movie has no page yet on PTP then fill out the required info (title, year, etc.).
		if movieOnPtpResult.PtpId is None:
			Ptp.FillImdbInfo( logger, releaseInfo.PtpUploadInfo )
			
			imdbInfo = Imdb.GetInfo( logger, releaseInfo.GetImdbId() )
	
			if imdbInfo.IsSeries:
				logger.info( "Ignoring release '%s' because it is a series." % announcement.ReleaseName )
				return None
			
			if "adult" in releaseInfo.PtpUploadInfo.Tags:
				logger.info( "Ignoring release '%s' because its genre is adult." % announcement.ReleaseName )
				return None
				
			# PTP return with the original title, IMDb's iPhone API returns with the international English title.
			if releaseInfo.PtpUploadInfo.Title != imdbInfo.Title and len( imdbInfo.Title ) > 0:
				releaseInfo.PtpUploadInfo.Title += " AKA " + imdbInfo.Title 		
	
			if len( releaseInfo.PtpUploadInfo.MovieDescription ) <= 0:
				releaseInfo.PtpUploadInfo.MovieDescription = imdbInfo.Plot 

			if len( releaseInfo.PtpUploadInfo.CoverArtUrl ) <= 0:
				releaseInfo.PtpUploadInfo.CoverArtUrl = imdbInfo.PosterUrl 
				if len( releaseInfo.PtpUploadInfo.CoverArtUrl ) <= 0:
					releaseInfo.PtpUploadInfo.CoverArtUrl = MoviePoster.Get( logger, releaseInfo.GetImdbId() ) 
	
		return releaseInfo;

	def __CheckAnnouncement(self, announcement):
		try:
			return self.__CheckAnnouncementInternal( announcement )
		except Exception, e:
			e.Logger = announcement.Logger
			raise

	def __DownloadInternal(self, releaseInfo):
		logger = releaseInfo.Announcement.Logger
		
		if releaseInfo.Announcement.IsManualDownload:
			logger.info( "Manual download is specified for release '%s', download skipped, going to next phase." % releaseInfo.Announcement.ReleaseName )
			self.PendingDownloads.append( releaseInfo )
			return
		
		# Make release root directory.
		releaseRootPath = releaseInfo.GetReleaseRootPath();
		logger.info( "Creating release root directory at '%s'." % releaseRootPath )
		
		if os.path.exists( releaseRootPath ):
			raise PtpUploaderException( "Release root directory '%s' already exists." % releaseRootPath )	
				
		os.makedirs( releaseRootPath )
		
		# Download the torrent file.
		torrentName = releaseInfo.Announcement.Source.Name + " " + releaseInfo.Announcement.ReleaseName + ".torrent"
		torrentPath = os.path.join( releaseRootPath, torrentName )
		releaseInfo.Announcement.Source.DownloadTorrent( logger, releaseInfo, torrentPath )
	
		# Start downloading the torrent.
		releaseInfo.SourceTorrentInfoHash = self.Rtorrent.AddTorrent( logger, torrentPath, releaseInfo.GetReleaseDownloadPath() )
		self.PendingDownloads.append( releaseInfo )
		
	def __Download(self, releaseInfo):
		try:
			self.__DownloadInternal( releaseInfo )
		except Exception, e:
			e.Logger = releaseInfo.Announcement.Logger
			raise

	def __GetFinishedDownloadToProcess(self):
		if len( self.PendingDownloads ) > 0:
			print "Pending downloads: %s" % len( self.PendingDownloads )
		
		# TODO: can we use a multicast RPC call get all the statuses in one call?
		for downloadIndex in range( len( self.PendingDownloads ) ):
			releaseInfo = self.PendingDownloads[ downloadIndex ]
			logger = releaseInfo.Announcement.Logger
			if releaseInfo.Announcement.IsManualDownload or self.Rtorrent.IsTorrentFinished( logger, releaseInfo.SourceTorrentInfoHash ):
				return self.PendingDownloads.pop( downloadIndex )
			
		return None
	
	def __UploadInternal(self, releaseInfo):
		logger = releaseInfo.Announcement.Logger
		
		# Create the upload path.
		uploadPath = releaseInfo.GetReleaseUploadPath();
		logger.info( "Creating upload path at '%s'." % uploadPath );	
		os.makedirs( uploadPath );
	
		# Extract the release.
		releaseInfo.Announcement.Source.ExtractRelease( logger, releaseInfo )
		videoFiles, totalFileCount = ReleaseExtractor.ValidateDirectory( uploadPath )
		if len( videoFiles ) < 1:
			raise PtpUploaderException( "Upload path '%s' doesn't contains any video files." % uploadPath );
		
		# Get the media info.
		videoFiles = ScreenshotMaker.SortVideoFiles( videoFiles );
		mediaInfos = MediaInfo.ReadAndParseMediaInfos( logger, videoFiles );
		releaseInfo.PtpUploadInfo.GetDataFromMediaInfo( mediaInfos[ 0 ] );
	
		# Take and upload screenshots.
		screenshotPath = os.path.join( releaseInfo.GetReleaseRootPath(), "screenshot.png" );
		uploadedScreenshots = ScreenshotMaker.TakeAndUploadScreenshots( logger, videoFiles[ 0 ], screenshotPath, mediaInfos[ 0 ].DurationInSec );

		releaseDescriptionFilePath = os.path.join( releaseInfo.GetReleaseRootPath(), "release description.txt" )
		releaseInfo.PtpUploadInfo.FormatReleaseDescription( logger, releaseInfo, uploadedScreenshots, mediaInfos, releaseDescriptionFilePath )
	
		# Make the torrent.
		# We save it into a separate folder to make sure it won't end up in the upload somehow. :)
		uploadTorrentName = "PTP " + releaseInfo.Announcement.ReleaseName + ".torrent";
		uploadTorrentPath = os.path.join( releaseInfo.GetReleaseRootPath(), uploadTorrentName );
		# Make torrent with the parent directory's name included if there is more than one file or requested by the source (it is a scene release).
		if totalFileCount > 1 or releaseInfo.Announcement.Source.IsSingleFileTorrentNeedsDirectory():
			MakeTorrent.Make( logger, uploadPath, uploadTorrentPath );
		else: # Create the torrent including only the single video file.
			MakeTorrent.Make( logger, videoFiles[ 0 ], uploadTorrentPath );
	
		movieOnPtpResult = Ptp.GetMoviePageOnPtp( logger, releaseInfo.GetImdbId() );
	
		# If this is an automatic announcement then we have to check (again) if is it already on PTP.
		if not releaseInfo.Announcement.IsManualAnnouncement:
			existingRelease = movieOnPtpResult.IsReleaseExists( releaseInfo )
			if existingRelease is not None:
				logger.info( "Somebody has already uploaded the release '%s' to PTP while we were working on it. Skipping upload because of format '%s'." % ( releaseInfo.Announcement.ReleaseName, existingRelease ) )
				return
			
		# If this movie has no page yet on PTP then we will need the cover, so we rehost the image to an image hoster.
		if ( movieOnPtpResult.PtpId is None ) and len( releaseInfo.PtpUploadInfo.CoverArtUrl ) > 0:
			releaseInfo.PtpUploadInfo.CoverArtUrl = ImageUploader.Upload( imageUrl = releaseInfo.PtpUploadInfo.CoverArtUrl );

		# Add torrent without hash checking.
		self.Rtorrent.AddTorrentSkipHashCheck( logger, uploadTorrentPath, uploadPath );
	
		Ptp.UploadMovie( logger, releaseInfo.PtpUploadInfo, uploadTorrentPath, movieOnPtpResult.PtpId );
		
		logger.info( "'%s' has been successfully uploaded to PTP." % releaseInfo.Announcement.ReleaseName );

	def __Upload(self, releaseInfo):
		try:
			self.__UploadInternal( releaseInfo )
		except Exception, e:
			e.Logger = releaseInfo.Announcement.Logger
			raise

	# Returns true, if an announcement or a download has been processed.
	def __WorkInternal(self):
		# If there is a finished download, then upload it.
		releaseInfo = self.__GetFinishedDownloadToProcess()
		if releaseInfo:
			self.__Upload( releaseInfo )
			return True

		# If there is a new announcement, then check and start downloading it.
		announcement = self.__GetAnnouncementToProcess()
		if announcement:
			releaseInfo = self.__CheckAnnouncement( announcement )
			if releaseInfo:
				self.__Download( releaseInfo )
			
			return True
				
		return False
	
	def Work(self):
		Globals.Logger.info( "Entering into the main loop." );
		
		while True:
			try:
				if not self.__WorkInternal():
					time.sleep( 30 ); # Sleep 30 seconds, if there was not any work to do in this run.
			except Exception, e:
				logger = Globals.Logger
				if hasattr( e, "Logger" ):
					logger = e.Logger

				logger.exception( "Caught exception in the main loop. Trying to continue." )