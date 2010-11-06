from AnnouncementWatcher import *;
from Globals import Globals;
from Gft import Gft;
from ImageUploader import ImageUploader;
from MakeTorrent import MakeTorrent;
from MediaInfo import MediaInfo;
from NfoParser import NfoParser;
from Ptp import Ptp;
from PtpUploaderException import PtpUploaderException;
from PtpUploadInfo import PtpUploadInfo;
from ReleaseFilter import ReleaseFilter;
from ReleaseInfo import ReleaseInfo;
from Rtorrent import Rtorrent;
from SceneRelease import SceneRelease;
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

	if announcement.AnnouncementSourceName != "gft" and announcement.AnnouncementSourceName != "manual":
		Globals.Logger.error( "Unknown announcement source: '%s'." % announcement.AnnouncementSourceName );
		return None; 

	nfoText = None;
	
	if announcement.IsManualAnnouncement:
		if announcement.IsManualDownload:
			# If this is a manual download then we have to read the NFO from the directory of the already downloaded release.
			nfoText = NfoParser.GetNfoFile( ReleaseInfo.GetReleaseDownloadPathFromRelaseName( announcement.ReleaseName ) );
		else:
			# Download the NFO and get the release name.
			nfoText = Gft.DownloadNfo( announcement, getReleaseName = True, checkPretime = False );
	else:
		# In case of automatic announcement we have to check the release name if it is valid.
		# We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source. 
		if not ReleaseFilter.IsValidReleaseName( announcement.ReleaseName ):
			Globals.Logger.info( "Ignoring release '%s' because of its name." % announcement.ReleaseName );
			return None;

		# Download the NFO.
		nfoText = Gft.DownloadNfo( announcement );
	
	# Check if the NFO contains an IMDb id.
	imdbId = NfoParser.GetImdbId( nfoText );
	if imdbId is None:
		Globals.Logger.error( "IMDb id can't be found in NFO." );
		return None;

	releaseInfo = ReleaseInfo( announcement, imdbId );

	# TODO: this is temporary here. We should support it everywhere.
	# If we are not logged in here that could mean that nothing interesting has been announcened for a while. 
	Ptp.Login();

	# If this is an automatic announcement then we have to check if is it already on PtP.
	if not announcement.IsManualAnnouncement:
		movieOnPtpResult = Ptp.GetMoviePageOnPtp( imdbId );
		if movieOnPtpResult.IsReleaseExists( releaseInfo ):
			Globals.Logger.info( "Release '%s' already exists on PTP." % announcement.ReleaseName );
			return None;

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
	Gft.DownloadTorrent( releaseInfo, torrentPath );

	# Download the torrent.
	rtorrent.AddTorrentAndWaitTillDownloadFinishes( torrentPath, releaseInfo.GetReleaseDownloadPath() );

def Upload(rtorrent, releaseInfo):
	# Create the upload path.
	uploadPath = releaseInfo.GetReleaseUploadPath();
	Globals.Logger.info( "Creating upload path at '%s'." % uploadPath );	
	os.makedirs( uploadPath );
	
	# Extract the release.
	sceneRelease = SceneRelease( releaseInfo.GetReleaseDownloadPath() );
	sceneRelease.Extract( uploadPath );

	ptpUploadInfo = PtpUploadInfo( releaseInfo );

	# Get the list of videos.
	videoFiles = ScreenshotMaker.GetVideoFilesSorted( uploadPath );
	if len( videoFiles ) == 0:
		raise PtpUploaderException( "Upload path '%s' doesn't contains any video files." % uploadPath );
	
	# Get the media info.
	mediaInfos = MediaInfo.ReadAndParseMediaInfos( videoFiles );
	ptpUploadInfo.GetDataFromMediaInfo( mediaInfos[ 0 ] );

	# Take and upload screenshots.
	screenshotPath = os.path.join( releaseInfo.GetReleaseRootPath(), "screenshot.png" );
	uploadedScreenshots = ScreenshotMaker.TakeAndUploadScreenshots( videoFiles[ 0 ], screenshotPath, mediaInfos[ 0 ].DurationInSec );

	ptpUploadInfo.FormatReleaseDescription( releaseInfo, sceneRelease.Nfo, uploadedScreenshots, mediaInfos );

	# Make the torrent.
	# We save it into a separate folder to make sure it won't end up in the upload somehow. :)
	uploadTorrentName = "PTP " + releaseInfo.Announcement.ReleaseName + ".torrent";
	uploadTorrentPath = os.path.join( releaseInfo.GetReleaseRootPath(), uploadTorrentName );
	MakeTorrent.Make( uploadPath, uploadTorrentPath );

	movieOnPtpResult = Ptp.GetMoviePageOnPtp( releaseInfo.ImdbId );

	# If this is an automatic announcement then we have to check (again) if is it already on PTP.
	if ( not releaseInfo.Announcement.IsManualAnnouncement ) and movieOnPtpResult.IsReleaseExists( releaseInfo ):
		Globals.Logger.info( "Somebody has already uploaded the release '%s' to PTP while we were working on it. Skipping upload." % releaseInfo.Announcement.ReleaseName );
		return;

	# If this move has no page yet on PTP then fill out the required info (title, year, etc.).
	if movieOnPtpResult.PtpId is None:
		Ptp.FillImdbInfo( ptpUploadInfo );
		# Rehost image from IMDb to an image hoster.
		if len( ptpUploadInfo.CoverArtUrl ) > 0:
			ptpUploadInfo.CoverArtUrl = ImageUploader.Upload( imageUrl = ptpUploadInfo.CoverArtUrl );

	# Add torrent without hash checking.
	rtorrent.AddTorrentSkipHashCheck( uploadTorrentPath, uploadPath );

	Ptp.UploadMovie( ptpUploadInfo, uploadTorrentPath, movieOnPtpResult.PtpId );
	
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
	Gft.Login();
	Ptp.Login();
	rtorrent = Rtorrent();

	Work( rtorrent );
	
if __name__ == '__main__':
	Main();