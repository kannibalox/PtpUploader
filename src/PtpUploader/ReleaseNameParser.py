from PtpUploaderException import PtpUploaderException
from Settings import Settings
from TagList import TagList

import re

class ReleaseNameParser:
	def __init__(self, name):
		originalName = name

		# Simply popping the last tag as a group name wouldn't work because of P2P releaes with multiple dashes in it:
		# Let Me In 2010 DVDRIP READNFO XViD-T0XiC-iNK
		name = name.lower()
		name, separator, self.Group = name.partition( "-" )
		if len( name ) <= 0:
			raise PtpUploaderException( "Release name '%s' is empty." % originalName )

		name = name.replace( ".", " " )
		self.Tags = TagList( name.split( " " ) )

		# This is not perfect (eg.: The Legend of 1900), but it doesn't matter if the real year will be included in the tags.
		self.TagsAfterYear = TagList( [] )
		for i in range( len( self.Tags.List ) ):
			if re.match( r"\d\d\d\d", self.Tags.List[ i ] ):
				self.TagsAfterYear.List = self.Tags.List[ i + 1: ]
				break

		self.Scene = self.Group in Settings.SceneReleaserGroup

	def GetSourceAndFormat(self, releaseInfo):
		if releaseInfo.IsCodecSet():
			releaseInfo.Logger.info( "Codec '%s' is already set, not getting from release name." % releaseInfo.Codec )			
		elif self.Tags.IsContainsTag( "xvid" ):
			releaseInfo.Codec = "XviD"
		elif self.Tags.IsContainsTag( "divx" ):
			releaseInfo.Codec = "DivX"
		elif self.Tags.IsContainsTag( "x264" ):
			releaseInfo.Codec = "x264"
		else:
			raise PtpUploaderException( "Can't figure out codec from release name '%s'." % releaseInfo.ReleaseName )

		if releaseInfo.IsSourceSet():
			releaseInfo.Logger.info( "Source '%s' is already set, not getting from release name." % releaseInfo.Source )			
		elif self.Tags.IsContainsTag( "dvdrip" ):
			releaseInfo.Source = "DVD"
		elif self.Tags.IsContainsTag( "bdrip" ) or self.Tags.IsContainsTag( "brrip" ) or self.Tags.IsContainsTag( "bluray" ):
			releaseInfo.Source = "Blu-ray"
		else:
			raise PtpUploaderException( "Can't figure out source from release name '%s'." % releaseInfo.ReleaseName )

		if releaseInfo.IsQualitySet() and releaseInfo.IsResolutionTypeSet():
			releaseInfo.Logger.info( "Quality '%s' and resolution type '%s' are already set, not getting from release name." % ( releaseInfo.Quality, releaseInfo.ResolutionType ) )
		if self.Tags.IsContainsTag( "720p" ):
			releaseInfo.Quality = "High Definition"
			releaseInfo.ResolutionType = "720p"
		elif self.Tags.IsContainsTag( "1080p" ):
			releaseInfo.Quality = "High Definition"
			releaseInfo.ResolutionType = "1080p"
		else:
			releaseInfo.Quality = "Standard Definition"
			releaseInfo.ResolutionType = "Other"

	@staticmethod
	def __IsTagListContainAnythingFromListOfTagList(tagList, listOfTagList):
		for listOfTagListElement in listOfTagList:
			if tagList.IsContainsTags( listOfTagListElement ):
				return True

		return False

	def IsAllowed(self):
		# TODO: write to log what caused the return 

		if self.Group in Settings.IgnoreReleaserGroup:
			return False
		
		if len( Settings.AllowReleaseTag ) > 0 and not ReleaseNameParser.__IsTagListContainAnythingFromListOfTagList( self.Tags, Settings.AllowReleaseTag ):
			return False

		if ReleaseNameParser.__IsTagListContainAnythingFromListOfTagList( self.Tags, Settings.IgnoreReleaseTag ):
			return False

		if len( self.TagsAfterYear.List ) > 0:
			if ReleaseNameParser.__IsTagListContainAnythingFromListOfTagList( self.TagsAfterYear, Settings.IgnoreReleaseTagAfterYear ):
				return False
		else:
			if ReleaseNameParser.__IsTagListContainAnythingFromListOfTagList( self.Tags, Settings.IgnoreReleaseTagAfterYear ):
				return False

		return True