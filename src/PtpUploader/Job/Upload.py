from Job.FinishedJobPhase import FinishedJobPhase
from Job.JobRunningState import JobRunningState
from Job.WorkerBase import WorkerBase
from Tool.MakeTorrent import MakeTorrent

from Database import Database
from IdxReader import IdxReader
from ImageHost.ImageUploader import ImageUploader
from MyGlobals import MyGlobals
from Ptp import Ptp
from PtpSubtitle import *
from PtpUploaderException import *
from ReleaseDescriptionFormatter import ReleaseDescriptionFormatter
from ReleaseExtractor import ReleaseExtractor
from Settings import Settings

import os
import subprocess

class Upload(WorkerBase):
	def __init__(self, jobManager, jobManagerItem, rtorrent):
		phases = [
			self.__StopAutomaticJobBeforeExtracting,
			self.__StopAutomaticJobIfThereAreMultipleVideosBeforeExtracting,
			self.__CreateUploadPath,
			self.__MakeIncludedFileList,
			self.__ExtractRelease,
			self.__ValidateExtractedRelease,
			self.__MakeReleaseDescription,
			self.__DetectSubtitles,
			self.__MakeTorrent,
			self.__CheckIfExistsOnPtp,
			self.__CheckCoverArt,
			self.__RehostPoster,
			self.__StopBeforeUploading,
			self.__StartTorrent,
			self.__UploadMovie,
			self.__ExecuteCommandOnSuccessfulUpload ]

		WorkerBase.__init__( self, phases, jobManager, jobManagerItem )
		
		self.Rtorrent = rtorrent
		self.IncludedFileList = None
		self.VideoFiles = []
		self.AdditionalFiles = []
		self.MainMediaInfo = None
		self.ReleaseDescription = u""
		self.AuthKey = u""

	def __StopAutomaticJobBeforeExtracting(self):
		if self.ReleaseInfo.IsUserCreatedJob() or self.ReleaseInfo.AnnouncementSource.StopAutomaticJob!= "beforeextracting":
			return

		raise PtpUploaderException( "Stopping before extracting." )

	def __StopAutomaticJobIfThereAreMultipleVideosBeforeExtracting(self):
		if self.ReleaseInfo.IsUserCreatedJob() or self.ReleaseInfo.AnnouncementSource.StopAutomaticJobIfThereAreMultipleVideos != "beforeextracting":
			return

		includedFileList = self.ReleaseInfo.AnnouncementSource.GetIncludedFileList( self.ReleaseInfo )
		self.ReleaseInfo.AnnouncementSource.CheckFileList( self.ReleaseInfo, includedFileList )

	def __CreateUploadPath(self):
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Upload_CreateUploadPath ):
			self.ReleaseInfo.Logger.info( "Upload path creation phase has been reached previously, not creating it again." )
			return

		uploadPath = self.ReleaseInfo.GetReleaseUploadPath()
		customUploadPath = self.ReleaseInfo.AnnouncementSource.GetCustomUploadPath( self.ReleaseInfo.Logger, self.ReleaseInfo )
		if len( customUploadPath ) > 0:
			uploadPath = customUploadPath
			self.ReleaseInfo.SetReleaseUploadPath( customUploadPath )

		self.ReleaseInfo.AnnouncementSource.CreateUploadDirectory( self.ReleaseInfo )

		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Upload_CreateUploadPath )
		Database.DbSession.commit()
		
	def __MakeIncludedFileList(self):
		self.IncludedFileList = self.ReleaseInfo.AnnouncementSource.GetIncludedFileList( self.ReleaseInfo )

		if len( self.ReleaseInfo.IncludedFiles ) > 0:
			self.ReleaseInfo.Logger.info( "There are %s files in the file list. Customized: '%s'." % ( len( self.IncludedFileList.Files ), self.ReleaseInfo.IncludedFiles ) )
		else:
			self.ReleaseInfo.Logger.info( "There are %s files in the file list." % ( len( self.IncludedFileList.Files ) ) )

		self.IncludedFileList.ApplyCustomizationFromJson( self.ReleaseInfo.IncludedFiles )

	def __ExtractRelease(self):
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Upload_ExtractRelease ):
			self.ReleaseInfo.Logger.info( "Extract release phase has been reached previously, not extracting release again." )
			return
		
		self.ReleaseInfo.AnnouncementSource.ExtractRelease( self.ReleaseInfo.Logger, self.ReleaseInfo, self.IncludedFileList )

		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Upload_ExtractRelease )
		Database.DbSession.commit()

	def __ValidateExtractedRelease(self):
		self.VideoFiles, self.AdditionalFiles = self.ReleaseInfo.AnnouncementSource.ValidateExtractedRelease( self.ReleaseInfo, self.IncludedFileList )

	def __GetMediaInfoContainer(self, mediaInfo):
		container = ""

		if mediaInfo.IsAvi():
			container = "AVI"
		elif mediaInfo.IsMkv():
			container = "MKV"
		elif mediaInfo.IsMp4():
			container = "MP4"
		elif mediaInfo.IsVob():
			container = "VOB IFO"
		
		if self.ReleaseInfo.IsContainerSet():
			if container != self.ReleaseInfo.Container:
				if self.ReleaseInfo.IsForceUpload():
					self.ReleaseInfo.Logger.info( "Container is set to '%s', detected MediaInfo container is '%s' ('%s'). Ignoring mismatch because of force upload." % ( self.ReleaseInfo.Container, container, mediaInfo.Container ) )
				else:
					raise PtpUploaderException( "Container is set to '%s', detected MediaInfo container is '%s' ('%s')." % ( self.ReleaseInfo.Container, container, mediaInfo.Container ) )
		else:
			if len( container ) > 0:
				self.ReleaseInfo.Container = container
			else:
				raise PtpUploaderException( "Unsupported container: '%s'." % mediaInfo.Container )

	def __GetMediaInfoCodec(self, mediaInfo):
		codec = ""

		if mediaInfo.IsX264():
			codec = "x264"
			if mediaInfo.IsAvi():
				raise PtpUploaderException( "X264 in AVI is not allowed." )
		elif mediaInfo.IsH264():
			codec = "H.264"
			if mediaInfo.IsAvi():
				raise PtpUploaderException( "H.264 in AVI is not allowed." )
		elif mediaInfo.IsXvid():
			codec = "XviD"
			if mediaInfo.IsMkv():
				raise PtpUploaderException( "XviD in MKV is not allowed." )
		elif mediaInfo.IsDivx():
			codec = "DivX"
			if mediaInfo.IsMkv():
				raise PtpUploaderException( "DivX in MKV is not allowed." )
		elif self.ReleaseInfo.IsDvdImage():
			# Codec type DVD5 and DVD9 can't be figured out from MediaInfo.
			codec = self.ReleaseInfo.Codec

		if self.ReleaseInfo.IsCodecSet():
			if codec != self.ReleaseInfo.Codec:
				if self.ReleaseInfo.IsForceUpload():
					self.ReleaseInfo.Logger.info( "Codec is set to '%s', detected MediaInfo codec is '%s' ('%s'). Ignoring mismatch because of force upload." % ( self.ReleaseInfo.Codec, codec, mediaInfo.Codec ) )
				else:
					raise PtpUploaderException( "Codec is set to '%s', detected MediaInfo codec is '%s' ('%s')." % ( self.ReleaseInfo.Codec, codec, mediaInfo.Codec ) )
		else:
			if len( codec ) > 0:
				self.ReleaseInfo.Codec = codec
			else:
				raise PtpUploaderException( "Unsupported codec: '%s'." % mediaInfo.Codec )

	def __GetMediaInfoResolution(self, mediaInfo):
		resolution = ""

		# Indicate the exact resolution for standard definition releases.
		# It is not needed for DVD images.
		if self.ReleaseInfo.IsStandardDefinition() and ( not self.ReleaseInfo.IsDvdImage() ):
			resolution = "%sx%s" % ( mediaInfo.Width, mediaInfo.Height )
			
		if len( self.ReleaseInfo.Resolution ) > 0:
			if resolution != self.ReleaseInfo.Resolution:
				if self.ReleaseInfo.IsForceUpload():
					self.ReleaseInfo.Logger.info( "Resolution is set to '%s', detected MediaInfo resolution is '%s' ('%sx%s'). Ignoring mismatch because of force upload." % ( self.ReleaseInfo.Resolution, resolution, mediaInfo.Width, mediaInfo.Height ) )
				else:
					raise PtpUploaderException( "Resolution is set to '%s', detected MediaInfo resolution is '%s' ('%sx%s')." % ( self.ReleaseInfo.Resolution, resolution, mediaInfo.Width, mediaInfo.Height ) )
		else:
			self.ReleaseInfo.Resolution = resolution

	def __MakeReleaseDescription(self):
		self.ReleaseInfo.AnnouncementSource.ReadNfo( self.ReleaseInfo )
		
		includeReleaseName = self.ReleaseInfo.AnnouncementSource.IncludeReleaseNameInReleaseDescription()
		outputImageDirectory = self.ReleaseInfo.AnnouncementSource.GetTemporaryFolderForImagesAndTorrent( self.ReleaseInfo )
		releaseDescriptionFormatter = ReleaseDescriptionFormatter( self.ReleaseInfo, self.VideoFiles, self.AdditionalFiles, outputImageDirectory )
		self.ReleaseDescription = releaseDescriptionFormatter.Format( includeReleaseName )
		self.MainMediaInfo = releaseDescriptionFormatter.GetMainMediaInfo()
		
		# To not waste the uploaded screenshots we commit them to the database because the following function calls can all throw exceptions.
		Database.DbSession.commit()

		self.__GetMediaInfoContainer( self.MainMediaInfo )
		self.__GetMediaInfoCodec( self.MainMediaInfo )
		self.__GetMediaInfoResolution( self.MainMediaInfo )

	# Returns with true if failed to detect the language.
	def __DetectSubtitlesAddOne(self, subtitleIds, languageName):
		id = MyGlobals.PtpSubtitle.GetId( languageName )
		if id is None:
			# TODO: show warning on the WebUI
			self.ReleaseInfo.Logger.warning( "Unknown subtitle language: '%s'." % languageName )
			return True

		id = str( id )
		if id not in subtitleIds:
			subtitleIds.append( id )

		return False

	def __DetectSubtitles(self):
		subtitleIds = self.ReleaseInfo.GetSubtitles()
		if len( subtitleIds ) > 0:
			self.ReleaseInfo.Logger.info( "Subtitle list is not empty. Skipping subtitle detection." )
			return

		self.ReleaseInfo.Logger.info( "Detecting subtitles." )

		# We can't do anything with DVD images.
		if self.ReleaseInfo.IsDvdImage():
			return

		containsUnknownSubtitle = False

		# Read from MediaInfo.
		for language in self.MainMediaInfo.Subtitles:
			containsUnknownSubtitle |= self.__DetectSubtitlesAddOne( subtitleIds, language )

		# Try to read from IDX with the same name as the main video file.
		idxPath, extension = os.path.splitext( self.MainMediaInfo.Path )
		idxPath += ".idx"
		if os.path.isfile( idxPath ):
			idxLanguages = IdxReader.GetSubtitleLanguages( idxPath )
			if len( idxLanguages ) > 0:
				for language in idxLanguages:
					containsUnknownSubtitle |= self.__DetectSubtitlesAddOne( subtitleIds, language )
			else:
				containsUnknownSubtitle = True

		# If everything went successfully so far, then check if there are any SRT files in the release.
		if not containsUnknownSubtitle:
			for file in self.AdditionalFiles:
				if file.lower().endswith( ".srt" ):
					# TODO: show warning on the WebUI
					containsUnknownSubtitle = True
					break

		if len( subtitleIds ) > 0:
			self.ReleaseInfo.SetSubtitles( subtitleIds )
		elif not containsUnknownSubtitle:
			self.ReleaseInfo.SetSubtitles( [ str( PtpSubtitleId.NoSubtitle ) ] )

	def __MakeTorrent(self):
		if self.ReleaseInfo.IsUploadTorrentFilePathSet():
			self.ReleaseInfo.Logger.info( "Upload torrent file path is set, not making torrent again." )
			return
		
		# We save it into a separate folder to make sure it won't end up in the upload somehow. :)
		uploadTorrentName = "PTP " + self.ReleaseInfo.ReleaseName + ".torrent"
		uploadTorrentFilePath = self.ReleaseInfo.AnnouncementSource.GetTemporaryFolderForImagesAndTorrent( self.ReleaseInfo )
		uploadTorrentFilePath = os.path.join( uploadTorrentFilePath, uploadTorrentName )

		# Make torrent with the parent directory's name included if there is more than one file or requested by the source (it is a scene release).
		totalFileCount = len( self.VideoFiles ) + len( self.AdditionalFiles )
		if totalFileCount > 1 or ( self.ReleaseInfo.AnnouncementSource.IsSingleFileTorrentNeedsDirectory( self.ReleaseInfo ) and not self.ReleaseInfo.IsForceDirectorylessSingleFileTorrent() ):
			MakeTorrent.Make( self.ReleaseInfo.Logger, self.ReleaseInfo.GetReleaseUploadPath(), uploadTorrentFilePath )
		else: # Create the torrent including only the single video file.
			MakeTorrent.Make( self.ReleaseInfo.Logger, self.MainMediaInfo.Path, uploadTorrentFilePath )
			
		# Local variable is used temporarily to make sure that UploadTorrentFilePath is only gets stored in the database if MakeTorrent.Make succeeded.
		self.ReleaseInfo.UploadTorrentFilePath = uploadTorrentFilePath
		Database.DbSession.commit()

	def __CheckIfExistsOnPtp(self):
		# TODO: this is temporary here. We should support it everywhere.
		# If we are not logged in here that could mean that the download took a lot of time and the user got logged out for some reason. 
		Ptp.Login()

		# This could be before the Ptp.Login() line, but this way we can hopefully avoid some logging out errors.
		if self.ReleaseInfo.IsZeroImdbId():
			self.ReleaseInfo.Logger.info( "IMDb ID is set zero, ignoring the check for existing release." )
			return

		movieOnPtpResult = None

		if self.ReleaseInfo.HasPtpId():
			movieOnPtpResult = Ptp.GetMoviePageOnPtp( self.ReleaseInfo.Logger, self.ReleaseInfo.GetPtpId() )
		else:
			movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )
			self.ReleaseInfo.PtpId = movieOnPtpResult.PtpId
		
		# Check (again) if is it already on PTP.
		existingRelease = movieOnPtpResult.IsReleaseExists( self.ReleaseInfo )
		if existingRelease is not None:
			raise PtpUploaderException( JobRunningState.DownloadedAlreadyExists, "Got uploaded to PTP while we were working on it. Skipping upload because of format '%s'." % existingRelease )

	def __CheckCoverArt(self):
		if Settings.StopIfCoverArtIsMissing.lower() == "beforeuploading":
			self.ReleaseInfo.AnnouncementSource.CheckCoverArt( self.ReleaseInfo.Logger, self.ReleaseInfo )

	def __RehostPoster(self):
		# If this movie has no page yet on PTP then we will need the cover, so we rehost the image to an image hoster.
		if self.ReleaseInfo.HasPtpId() or ( not self.ReleaseInfo.IsCoverArtUrlSet() ):
			return

		# Rehost the image only if not already on an image hoster.
		url = self.ReleaseInfo.CoverArtUrl
		if url.find( "ptpimg.me" ) != -1 or url.find( "whatimg.com" ) != -1:
			return

		self.ReleaseInfo.Logger.info( "Rehosting poster from '%s'." % url )
		self.ReleaseInfo.CoverArtUrl = ImageUploader.Upload( self.ReleaseInfo.Logger, imageUrl = url )
		self.ReleaseInfo.Logger.info( "Rehosted poster to '%s'." % self.ReleaseInfo.CoverArtUrl )

	def __StopBeforeUploading(self):
		if self.ReleaseInfo.IsStopBeforeUploading():
			raise PtpUploaderException( "Stopping before uploading." )

	def __StartTorrent(self):
		if len( self.ReleaseInfo.UploadTorrentInfoHash ) > 0:
			self.ReleaseInfo.Logger.info( "Upload torrent info hash is set, not starting torrent again." )
			return
		
		# Add torrent without hash checking.
		self.ReleaseInfo.UploadTorrentInfoHash = self.Rtorrent.AddTorrentSkipHashCheck( self.ReleaseInfo.Logger, self.ReleaseInfo.UploadTorrentFilePath, self.ReleaseInfo.GetReleaseUploadPath() )
		Database.DbSession.commit()

	def __UploadMovie(self):
		# This is not possible because finished jobs can't be restarted.
		if self.ReleaseInfo.IsJobPhaseFinished( FinishedJobPhase.Upload_UploadMovie ):
			self.ReleaseInfo.Logger.info( "Upload movie phase has been reached previously, not uploading it again." )
			return

		self.AuthKey = Ptp.UploadMovie( self.ReleaseInfo.Logger, self.ReleaseInfo, self.ReleaseInfo.UploadTorrentFilePath, self.ReleaseDescription )
		self.ReleaseInfo.Logger.info( "'%s' has been successfully uploaded to PTP." % self.ReleaseInfo.ReleaseName )

		self.ReleaseInfo.SetJobPhaseFinished( FinishedJobPhase.Upload_UploadMovie )
		self.ReleaseInfo.JobRunningState = JobRunningState.Finished
		Database.DbSession.commit()

	def __ExecuteCommandOnSuccessfulUpload(self):
		# Execute command on successful upload.
		if len( Settings.OnSuccessfulUpload ) <= 0:
			return

		uploadedTorrentUrl = "http://passthepopcorn.me/torrents.php?id=" + self.ReleaseInfo.PtpId
		command = Settings.OnSuccessfulUpload % { "releaseName": self.ReleaseInfo.ReleaseName, "uploadedTorrentUrl": uploadedTorrentUrl }
		
		# We don't care if this fails. Our upload is complete anyway. :)
		try: 
			subprocess.Popen( command, shell = True )
		except ( KeyboardInterrupt, SystemExit ):
			raise
		except Exception, e:
			logger.exception( "Got exception while trying to run command '%s' after successful upload." % command )