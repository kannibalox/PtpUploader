from Job.JobRunningState import JobRunningState
from InformationSource.Imdb import Imdb
from InformationSource.MoviePoster import MoviePoster

from Database import Database
from Ptp import Ptp
from PtpImdbInfo import PtpImdbInfo, PtpZeroImdbInfo
from PtpUploaderException import *

class CheckAnnouncement:
	def __init__(self, releaseInfo):
		self.ReleaseInfo = releaseInfo

	def __PrepareDownload(self):
		self.ReleaseInfo.JobRunningState = JobRunningState.InProgress
		
		result = self.ReleaseInfo.AnnouncementSource.PrepareDownload( self.ReleaseInfo.Logger, self.ReleaseInfo )
		if result is None:
			return False
		return True

	def __ValidateReleaseInfo(self):
		# Make sure we have IMDb or PTP id.
		if ( not self.ReleaseInfo.HasImdbId() ) and ( not self.ReleaseInfo.HasPtpId() ):
			self.ReleaseInfo.Logger.error( "IMDb or PTP id must be specified." )
			return False
	
		# Make sure the source is providing a name.
		self.ReleaseInfo.ReleaseName = self.ReleaseInfo.ReleaseName.strip()
		if len( self.ReleaseInfo.ReleaseName ) <= 0:
			self.ReleaseInfo.Logger.error( "Name of the release is not specified." )
			return False

		# Make sure the source is providing release quality information.
		if len( self.ReleaseInfo.Quality ) <= 0:
			self.ReleaseInfo.Logger.error( "Quality of the release is not specified." )
			return False

		# Make sure the source is providing release source information.
		if len( self.ReleaseInfo.Source ) <= 0:
			self.ReleaseInfo.Logger.error( "Source of the release is not specified." )
			return False

		# Make sure the source is providing release codec information.
		if len( self.ReleaseInfo.Codec ) <= 0:
			self.ReleaseInfo.Logger.error( "Codec of the release is not specified." )
			return False

		# Make sure the source is providing release resolution type information.
		if len( self.ReleaseInfo.ResolutionType ) <= 0:
			self.ReleaseInfo.Logger.error( "Resolution type of the release is not specified." )
			return False		

		# HD XviDs are not allowed.
		if self.ReleaseInfo.Quality == "High Definition" and ( self.ReleaseInfo.Codec == "XviD" or self.ReleaseInfo.Codec == "DivX" ):
			raise PtpUploaderException( "Forbidden combination of quality '%s' and codec '%s'." % ( self.ReleaseInfo.Quality, self.ReleaseInfo.Codec ) )
		
		return True
	
	def __CheckIfExistsOnPtpInternal(self, movieOnPtpResult):
		existingRelease = movieOnPtpResult.IsReleaseExists( self.ReleaseInfo )
		if existingRelease is not None:
			self.ReleaseInfo.Logger.info( "Release '%s' already exists on PTP. Skipping upload because of format '%s'." % ( self.ReleaseInfo.ReleaseName, existingRelease ) )
			return False
		return True

	def __CheckIfExistsOnPtp(self):
		# TODO: this is temporary here. We should support it everywhere.
		# If we are not logged in here that could mean that nothing interesting has been announcened for a while. 
		Ptp.Login()

		# This could be before the Ptp.Login() line, but this way we can hopefully avoid some logging out errors.
		if self.ReleaseInfo.IsZeroImdbId():
			self.ReleaseInfo.Logger.info( "IMDb ID is set zero, ignoring the check for existing release." )
			return True

		if self.ReleaseInfo.HasPtpId():
			# If this is not a forced upload then we have to check if is it already on PTP.
			if not self.ReleaseInfo.IsForceUpload():
				movieOnPtpResult = Ptp.GetMoviePageOnPtp( self.ReleaseInfo.Logger, self.ReleaseInfo.GetPtpId() )
				return self.__CheckIfExistsOnPtpInternal( movieOnPtpResult )
		else:
			# Try to get a PTP ID.
			movieOnPtpResult = Ptp.GetMoviePageOnPtpByImdbId( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )
			self.ReleaseInfo.PtpId = movieOnPtpResult.PtpId

			# If this is not a forced upload then we have to check if is it already on PTP.
			if not self.ReleaseInfo.IsForceUpload():
				return self.__CheckIfExistsOnPtpInternal( movieOnPtpResult )

		return True
	
	def __FillOutDetailsForNewMovieByPtpApi(self):
		# If already has a page on PTP then we don't have to do anything here.
		if self.ReleaseInfo.HasPtpId():
			return True

		ptpImdbInfo = None
		if self.ReleaseInfo.IsZeroImdbId():
			ptpImdbInfo = PtpZeroImdbInfo()
		else:
			ptpImdbInfo = PtpImdbInfo( self.ReleaseInfo.GetImdbId() )

		# Title
		if len( self.ReleaseInfo.Title ) > 0:
			self.ReleaseInfo.Logger.info( "Title '%s' is already set, not getting from PTP's movie info." % self.ReleaseInfo.Title )
		else:
			self.ReleaseInfo.Title = ptpImdbInfo.GetTitle()
			if len( self.ReleaseInfo.Title ) <= 0: 
				self.ReleaseInfo.Logger.error( "Movie title is not set."  )
				return False
			
		# Year
		if len( self.ReleaseInfo.Year ) > 0:
			self.ReleaseInfo.Logger.info( "Year '%s' is already set, not getting from PTP's movie info." % self.ReleaseInfo.Year )
		else:
			self.ReleaseInfo.Year = ptpImdbInfo.GetYear()
			if len( self.ReleaseInfo.Year ) <= 0: 
				self.ReleaseInfo.Logger.error( "Movie year is not set."  )
				return False

		# Movie description
		if len( self.ReleaseInfo.MovieDescription ) > 0:
			self.ReleaseInfo.Logger.info( "Movie description is already set, not getting from PTP's movie info." )
		else:
			self.ReleaseInfo.MovieDescription = ptpImdbInfo.GetMovieDescription()
			
		# Tags
		if len( self.ReleaseInfo.Tags ) > 0:
			self.ReleaseInfo.Logger.info( "Tags '%s' are already set, not getting from PTP's movie info." % self.ReleaseInfo.Tags )
		else:
			self.ReleaseInfo.Tags = ptpImdbInfo.GetTags()
			if len( self.ReleaseInfo.Tags ) <= 0:
				self.ReleaseInfo.Logger.error( "At least one tag must be specified for a movie."  )
				return False
			
		# Cover art URL
		if self.ReleaseInfo.IsCoverArtUrlSet():
			self.ReleaseInfo.Logger.info( "Cover art URL '%s' is already set, not getting from PTP's movie info." % self.ReleaseInfo.CoverArtUrl )
		else:
			self.ReleaseInfo.CoverArtUrl = ptpImdbInfo.GetCoverArtUrl()
			
		# Directors
		if len( self.ReleaseInfo.Directors ) > 0:
			self.ReleaseInfo.Logger.info( "Director '%s' is already set, not getting from PTP's movie info." % self.ReleaseInfo.Directors )
		else:
			self.ReleaseInfo.SetDirectors( ptpImdbInfo.GetDirectors() )			
			if len( self.ReleaseInfo.Directors ) <= 0:
				self.ReleaseInfo.Logger.error( """The director of the movie is not set. Use "None Listed" (without the quotes) if there is no director.""" )
				return False
			
		# Ignore adult movies (if force upload is not set).
		if "adult" in self.ReleaseInfo.Tags:
			if self.ReleaseInfo.IsForceUpload():
				self.ReleaseInfo.Logger.info( "Movie's genre is adult, but continuing due to force upload." )
			else:
				self.ReleaseInfo.Logger.info( "Ignoring release '%s' because its genre is adult." % self.ReleaseInfo.ReleaseName )
				return False

		return True

	# Uses IMDb and The Internet Movie Poster DataBase. 
	def __FillOutDetailsForNewMovieByExternalSources(self):
		if self.ReleaseInfo.HasPtpId() or self.ReleaseInfo.IsZeroImdbId():
			return True

		imdbInfo = Imdb.GetInfo( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )

		# Ignore series (if force upload is not set).
		if imdbInfo.IsSeries:
			if self.ReleaseInfo.IsForceUpload():
				self.ReleaseInfo.Logger.info( "The release is a series, but continuing due to force upload." )
			else:
				self.ReleaseInfo.Logger.info( "Ignoring release '%s' because it is a series." % self.ReleaseInfo.ReleaseName )
				return False

		# PTP returns with the original title, IMDb's iPhone API returns with the international English title.
		self.ReleaseInfo.InternationalTitle = imdbInfo.Title
		if self.ReleaseInfo.Title != self.ReleaseInfo.InternationalTitle and len( self.ReleaseInfo.InternationalTitle ) > 0 and self.ReleaseInfo.Title.find( " AKA " ) == -1:
			self.ReleaseInfo.Title += " AKA " + self.ReleaseInfo.InternationalTitle

		if len( self.ReleaseInfo.MovieDescription ) <= 0:
			self.ReleaseInfo.MovieDescription = imdbInfo.Plot 

		if not self.ReleaseInfo.IsCoverArtUrlSet():
			self.ReleaseInfo.CoverArtUrl = imdbInfo.PosterUrl
			if not self.ReleaseInfo.IsCoverArtUrlSet():
				self.ReleaseInfo.CoverArtUrl = MoviePoster.Get( self.ReleaseInfo.Logger, self.ReleaseInfo.GetImdbId() )
	
		return True
	
	def Work(self):
		self.ReleaseInfo.Logger.info( "Working on announcement from '%s' with id '%s' and name '%s'." % ( self.ReleaseInfo.AnnouncementSource.Name, self.ReleaseInfo.AnnouncementId, self.ReleaseInfo.ReleaseName ) )

		if not self.__PrepareDownload():
			return False
		if not self.__ValidateReleaseInfo():
			return False
		if not self.__CheckIfExistsOnPtp():
			return False
		if not self.__FillOutDetailsForNewMovieByPtpApi():
			return False
		if not self.__FillOutDetailsForNewMovieByExternalSources():
			return False
		
		return True

	@staticmethod
	def DoWork(releaseInfo): 
		try:
			checkAnnouncement = CheckAnnouncement( releaseInfo )
			return checkAnnouncement.Work()
		except Exception, e:
			releaseInfo.JobRunningState = JobRunningState.Failed
			Database.DbSession.commit()
			
			e.Logger = releaseInfo.Logger
			raise