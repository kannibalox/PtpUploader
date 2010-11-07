from Source.Cinemageddon import Cinemageddon;
from Source.Gft import Gft;
from Source.SourceFactory import SourceFactory;

from AnnouncementWatcher import *;
from Globals import Globals;
from ImageUploader import ImageUploader;
from MakeTorrent import MakeTorrent;
from MediaInfo import MediaInfo;
from Ptp import Ptp;
from PtpUploaderException import PtpUploaderException;
from PtpUploadInfo import PtpUploadInfo;
from ReleaseExtractor import ReleaseExtractor;
from ReleaseInfo import ReleaseInfo;
from Rtorrent import Rtorrent;
from ScreenshotMaker import ScreenshotMaker;
from Settings import Settings;

import os;
import time;

def WaitForAnnouncement():
	# We could use Pyinotify for getting notifications about directory changes but it is Linux only, and that half minute delay does not really matters.

	while True:
		# Check if there is a new announcement in the queue.
		announcement = AnnouncementWatcher.GetAnnouncement();
		if announcement:
			return announcement;
		
		time.sleep( 30 ); # Sleep 30 seconds between polling directory for changes.

def CheckAnnouncement(announcement):
	Globals.Logger.info( "Working on announcement from '%s' with id '%s' and name '%s'." % ( announcement.AnnouncementSourceName, announcement.AnnouncementId, announcement.ReleaseName ) );

	source = SourceFactory.GetSource( announcement );
	if source is None:
		Globals.Logger.error( "Unknown announcement source: '%s'." % announcement.AnnouncementSourceName );
		return None;

	# We need the IMDb id.
	releaseInfo = source.PrepareDownload( announcement );
	if len( releaseInfo.GetImdbId() ) < 1:
		Globals.Logger.error( "IMDb id can't be found." );
		return None;

	# Make sure the source is providing a name.
	if len( releaseInfo.Announcement.ReleaseName ) < 1:
		Globals.Logger.error( "Release name is empty." );
		return None;		

	# TODO: this is temporary here. We should support it everywhere.
	# If we are not logged in here that could mean that nothing interesting has been announcened for a while. 
	Ptp.Login();

	# If this is an automatic announcement then we have to check if is it already on PtP.
	if not announcement.IsManualAnnouncement:
		movieOnPtpResult = Ptp.GetMoviePageOnPtp( releaseInfo.GetImdbId() );
		if movieOnPtpResult.IsReleaseExists( releaseInfo ):
			Globals.Logger.info( "Release '%s' already exists on PTP." % announcement.ReleaseName );
			return None;

	releaseInfo.Source = source;
	return releaseInfo;
	
def Download(rtorrent, releaseInfo):
	if releaseInfo.Announcement.IsManualDownload:
		Globals.Logger.info( "Manual download is specified for release '%s', download skipped, going to next phase." % releaseInfo.Announcement.ReleaseName );
		return;
	
	# Make release root directory.
	releaseRootPath = releaseInfo.GetReleaseRootPath();
	Globals.Logger.info( "Creating release root directory at '%s'." % releaseRootPath );
	
	if os.path.exists( releaseRootPath ):
		raise PtpUploaderException( "Release root directory '%s' already exists." % releaseRootPath );	
			
	os.makedirs( releaseRootPath );
	
	# Download the torrent file.
	torrentName = releaseInfo.Announcement.AnnouncementSourceName + " " + releaseInfo.Announcement.ReleaseName + ".torrent";
	torrentPath = os.path.join( releaseRootPath, torrentName );
	releaseInfo.Source.DownloadTorrent( releaseInfo, torrentPath );

	# Download the torrent.
	rtorrent.AddTorrentAndWaitTillDownloadFinishes( torrentPath, releaseInfo.GetReleaseDownloadPath() );

def Upload(rtorrent, releaseInfo):
	# Create the upload path.
	uploadPath = releaseInfo.GetReleaseUploadPath();
	Globals.Logger.info( "Creating upload path at '%s'." % uploadPath );	
	os.makedirs( uploadPath );

	# Extract the release.
	releaseInfo.Source.ExtractRelease( releaseInfo )
	videoFiles, totalFileCount = ReleaseExtractor.ValidateDirectory( uploadPath )
	if len( videoFiles ) < 1:
		raise PtpUploaderException( "Upload path '%s' doesn't contains any video files." % uploadPath );
	
	# Get the media info.
	videoFiles = ScreenshotMaker.SortVideoFiles( videoFiles );
	mediaInfos = MediaInfo.ReadAndParseMediaInfos( videoFiles );
	releaseInfo.PtpUploadInfo.GetDataFromMediaInfo( mediaInfos[ 0 ] );

	# Take and upload screenshots.
	screenshotPath = os.path.join( releaseInfo.GetReleaseRootPath(), "screenshot.png" );
	uploadedScreenshots = ScreenshotMaker.TakeAndUploadScreenshots( videoFiles[ 0 ], screenshotPath, mediaInfos[ 0 ].DurationInSec );

	releaseInfo.PtpUploadInfo.FormatReleaseDescription( releaseInfo, uploadedScreenshots, mediaInfos );

	# Make the torrent.
	# We save it into a separate folder to make sure it won't end up in the upload somehow. :)
	uploadTorrentName = "PTP " + releaseInfo.Announcement.ReleaseName + ".torrent";
	uploadTorrentPath = os.path.join( releaseInfo.GetReleaseRootPath(), uploadTorrentName );
	# Make torrent with the parent directory's name included if there is more than one file or requested by the source (it is a scene release).
	if totalFileCount > 1 or releaseInfo.Source.IsSingleFileTorrentNeedsDirectory():
		MakeTorrent.Make( uploadPath, uploadTorrentPath );
	else: # Create the torrent including only the single video file.
		MakeTorrent.Make( videoFiles[ 0 ], uploadTorrentPath );

	movieOnPtpResult = Ptp.GetMoviePageOnPtp( releaseInfo.GetImdbId() );

	# If this is an automatic announcement then we have to check (again) if is it already on PTP.
	if ( not releaseInfo.Announcement.IsManualAnnouncement ) and movieOnPtpResult.IsReleaseExists( releaseInfo ):
		Globals.Logger.info( "Somebody has already uploaded the release '%s' to PTP while we were working on it. Skipping upload." % releaseInfo.Announcement.ReleaseName );
		return;

	# If this movie has no page yet on PTP then fill out the required info (title, year, etc.).
	if movieOnPtpResult.PtpId is None:
		Ptp.FillImdbInfo( releaseInfo.PtpUploadInfo );
		# Rehost image from IMDb to an image hoster.
		if len( releaseInfo.PtpUploadInfo.CoverArtUrl ) > 0:
			releaseInfo.PtpUploadInfo.CoverArtUrl = ImageUploader.Upload( imageUrl = releaseInfo.PtpUploadInfo.CoverArtUrl );

	# Add torrent without hash checking.
	rtorrent.AddTorrentSkipHashCheck( uploadTorrentPath, uploadPath );

	Ptp.UploadMovie( releaseInfo.PtpUploadInfo, uploadTorrentPath, movieOnPtpResult.PtpId );
	
	Globals.Logger.info( "'%s' has been successfully uploaded to PTP." % releaseInfo.Announcement.ReleaseName );

def Work(rtorrent):
	Globals.Logger.info( "Entering into the main loop." );
	
	while True:
		try:
			announcement = WaitForAnnouncement(); 
			releaseInfo = CheckAnnouncement( announcement );
			if releaseInfo:
				Download( rtorrent, releaseInfo );
				Upload( rtorrent, releaseInfo );
				Globals.Logger.info( "Continuing." );
		except PtpUploaderException:
			Globals.Logger.exception( "Caught PtpUploaderException exception in the main loop. Continuing." );
		except Exception:
			Globals.Logger.exception( "Caught exception in the main loop. Trying to continue." );

def Main():
	Settings.LoadSettings();
	Globals.InitializeGlobals( Settings.WorkingPath );
	Globals.Logger.info( "PtpUploader v0.1 by TnS" );
	
	if len( Settings.CinemageddonUserName ) > 0 and len( Settings.CinemageddonPassword ) > 0:
		Cinemageddon.Login();
	
	if len( Settings.GftUserName ) > 0 and len( Settings.GftPassword ) > 0:
		Gft.Login();
		
	Ptp.Login();
	rtorrent = Rtorrent();
	Work( rtorrent );
	
if __name__ == '__main__':
	Main();