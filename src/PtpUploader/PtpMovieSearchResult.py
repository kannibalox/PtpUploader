from Helper import GetSizeFromText
from PtpUploaderException import PtpUploaderException

import re

class PtpMovieSearchResultItem:
	def __init__(self, fullTitle, codec, container, source, resolution, sizeText):
		self.FullTitle = fullTitle
		self.Codec = codec
		self.Container = container
		self.Source = source
		self.Resolution = resolution
		self.SizeText = sizeText
		self.Size = GetSizeFromText( sizeText )
		
	def __repr__(self):
		return "%s | %s" % ( self.FullTitle, self.SizeText ) 

# Notes:
# - We treat HD-DVD and Blu-ray as same quality.
# - We treat DVD and Blu-ray rips equally in the standard definition category.
# - We treat H.264 and x264 equally because of the uploading rules: "MP4 can only be trumped by MKV if the use of that container causes problems with video or audio".
# - We treat XviD and DivX equally because of the uploading rules: "DivX may be trumped by XviD, if the latter improves on the quality of the former. In cases where the DivX is well distributed and the XviD offers no significant improvement in quality, the staff may decide to keep the former in order to preserve the availability of the movie."
# - We support the checking of possible co-existence for different sized SD XviD and SD x264 releases. (E.g.: an 1400 MB upload won't be treated as a duplicate of a 700 MB release.) 
class PtpMovieSearchResult:
	def __init__(self, ptpId, moviePageHtml):
		self.PtpId = ptpId;
		self.MoviePageHtml = moviePageHtml
		self.SdList = []
		self.HdList = []
		self.OtherList = []

	@staticmethod
	def __ReprHelper(text, list, name):
		if len( list ) > 0:
			if len( text ) > 0:
				text += "\n"
			
			text += name + "\n"
			for item in list:
				text += str( item ) + "\n"
				
		return text

	def __repr__(self):
		self.__ParseMoviePage()
		result = PtpMovieSearchResult.__ReprHelper( "", self.SdList, "Standard Definition" )
		result = PtpMovieSearchResult.__ReprHelper( result, self.HdList, "High Definition" )
		return PtpMovieSearchResult.__ReprHelper( result, self.OtherList, "Other" )

	def __ParseMoviePageMakeItems(self, itemList, regexFindList):
		for regexFind in regexFindList:
			fullTitle = regexFind[ 0 ] 
			sizeText = regexFind[ 1 ]
			elements = fullTitle.split( " / " )
			if len( elements ) < 4:
				raise PtpUploaderException( "Unknown torrent format ('%s') on movie page 'https://passthepopcorn.me/torrents.php?id=%s'." % ( elements, self.PtpId ) )

			codec = elements[ 0 ]
			container = elements[ 1 ]
			source = elements[ 2 ]
			resolution = elements[ 3 ]
			itemList.append( PtpMovieSearchResultItem( fullTitle, codec, container, source, resolution, sizeText ) )

	def __ParseMoviePage(self):
		# We only parse the movie page if needed. And we only parse it once.
		html = self.MoviePageHtml
		if html is None:
			return
		else:
			self.MoviePageHtml = None

		# We divide the HTML into three sections: SD, HD and Other type torrents.
		# This is needed because we are using regular expressions and we have to know which section the torent belongs to.
		# We could use a HTML parser too, but this is faster and less resource hungry.

		# We have to sort the sections because we use the their start and end indexes in the regular expression.  	
		sortedSections = []
		sdIndex = html.find( 'class="edition_info"><strong>Standard Definition</strong>' )
		if sdIndex >= 0:
			sortedSections.append( ( sdIndex, self.SdList ) )
		hdIndex = html.find( 'class="edition_info"><strong>High Definition</strong>' )
		if hdIndex >= 0:
			sortedSections.append( ( hdIndex, self.HdList ) )
		otherIndex = html.find( 'class="edition_info"><strong>Other</strong>' )
		if otherIndex >= 0:
			sortedSections.append( ( otherIndex, self.OtherList ) )
			
		if len( sortedSections ) <= 0:
			raise PtpUploaderException( "Error! Movie page doesn't contain any torrents." );
			
		sortedSections.sort()

		# Well, the following regular expression is a bit long. :)
		# There are two variations for the address because the downloaded/seeding torrents are displayed differently: 
		# <a href="#" onclick="$('#torrent_37673').toggle(); show_description('35555', '62113'); return false;">XviD / AVI / DVD / 720x420</a>
		# <a href="#" onclick="$('#torrent_55714').toggle(); show_description('35555', '62113'); return false;"><span style="float:none;color:#E5B244;"><strong>XviD / AVI / DVD / 608x256 / Scene</strong></span></a>
		regEx = re.compile(
			"""<tr class="group_torrent" style="font-weight: normal;">"""\
			""".+?<a href="#" onclick="\$\('#torrent_\d+'\)\.toggle\(\);.+?">(?:<span style=".+?"><strong>)?(.+?)(?:</strong></span>)?</a>"""\
			""".+?</td>"""\
			""".+?<td class="nobr">(.+?)</td>"""\
			""".+?<td>.+?</td>"""\
			""".+?<td>.+?</td>"""\
			""".+?<td>.+?</td>"""\
			""".+?</tr>""", re.DOTALL )

		# Get the list of torrents for each section.
		for i in range( len( sortedSections ) ):
			section = sortedSections[ i ]
			currentIndex = section[ 0 ]
			currentList = section[ 1 ]
			
			endIndex = len( html )
			# If this is not the last item, we use the next item's start index for the end of the current range.
			if ( i + 1 ) < len( sortedSections ):
				nextSection = sortedSections[ i + 1 ]
				endIndex = nextSection[ 0 ]
	
			result = regEx.findall( html, currentIndex, endIndex )
			self.__ParseMoviePageMakeItems( currentList, result )

		# Just for absolute safety we compare the number of results with number of results produced by this subset of the regular expression.
		result = re.findall( """<a href="#" onclick="\$\('#torrent_\d+'\)\.toggle\(\);""", html )
		if ( not result ) or len( result ) == 0 or len( result ) != ( len( self.SdList ) + len( self.HdList ) + len( self.OtherList ) ):
			raise PtpUploaderException( "Unknown torrent format on movie page 'https://passthepopcorn.me/torrents.php?id=%s'." % self.PtpId )

	@staticmethod
	def __GetListOfMatches(list, codecs, sources = None, resolutions = None):
		result= []
		for item in list:
			if ( item.Codec in codecs ) \
				and ( ( sources is None ) or ( item.Source in sources ) ) \
				and ( ( resolutions is None ) or ( item.Resolution in resolutions ) ): 
				result.append( item )

		return result
	
	@staticmethod
	def __IsInList(list, codecs, sources = None, resolutions = None):
		existingReleases = PtpMovieSearchResult.__GetListOfMatches( list, codecs, sources, resolutions )
		if len( existingReleases ) > 0:
			return existingReleases[ 0 ]
		else:
			return None 
	
	@staticmethod
	def __IsFineSource(source):
		return source == "DVD" or source == "Blu-ray" or source == "HD-DVD"

	def __IsHdFineSourceReleaseExists(self, releaseInfo):
		if ( releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD" ) and releaseInfo.ResolutionType == "1080p":
			return PtpMovieSearchResult.__IsInList( self.HdList, [ "x264", "H.264" ], [ "Blu-ray", "HD-DVD" ], [ "1080p" ] )
		elif ( releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD" ) and releaseInfo.ResolutionType == "720p":
			return PtpMovieSearchResult.__IsInList( self.HdList, [ "x264", "H.264" ], [ "Blu-ray", "HD-DVD" ], [ "720p" ] )
		
		raise PtpUploaderException( "Can't check whether the release '%s' exist on PTP because its type is unsupported." % releaseInfo.ReleaseName );

	@staticmethod
	def __CanCoExist(existingReleases, releaseInfo, minimumSizeDifferenceToCoExist):
		if len( existingReleases ) <= 0:
			return None
		elif len( existingReleases ) >= 2:
			return existingReleases[ 0 ]

		existingRelease = existingReleases[ 0 ]

		# If size is not set, we can't compare.
		if releaseInfo.Size == 0 or existingRelease.Size == 0:
			return existingRelease

		# If the current release is significantly larger than the existing one then we don't treat it as a duplicate.
		if releaseInfo.Size > ( existingRelease.Size + minimumSizeDifferenceToCoExist ):
			return None
		else:
			return existingRelease

	# From the rules:
	# "In general terms, 1CD (700MB) and 2CD (1400MB) XviD rips may always co-exist, same as 2CD (1400MB) and 3CD (2100MB) in the case of longer movies (2 hours+). Those sizes should only be used as general indicators as many rips may fall above or below them."
	# "Along with two AVI rips, two x264 of varying qualities may coexist."
	# "PAL and NTSC may co-exist, as may DVD5 and DVD9." 
	def __IsSdFineSourceReleaseExists(self, releaseInfo):
		# 600 MB seems like a good choice. Comparing by size ratio wouldn't be too effective.
		minimumSizeDifferenceToCoExist = 600 * 1024 * 1024
		
		if releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD" or releaseInfo.Source == "DVD":
			if releaseInfo.Codec == "x264" or releaseInfo.Codec == "H.264":
				list = PtpMovieSearchResult.__GetListOfMatches( self.SdList, [ "x264", "H.264" ], [ "Blu-ray", "HD-DVD", "DVD" ] )
				return PtpMovieSearchResult.__CanCoExist( list, releaseInfo, minimumSizeDifferenceToCoExist )
			elif releaseInfo.Codec == "XviD" or releaseInfo.Codec == "DivX":
				list = PtpMovieSearchResult.__GetListOfMatches( self.SdList, [ "XviD", "DivX" ], [ "Blu-ray", "HD-DVD", "DVD" ] )
				return PtpMovieSearchResult.__CanCoExist( list, releaseInfo, minimumSizeDifferenceToCoExist )
			elif releaseInfo.IsDvdImage() and ( releaseInfo.ResolutionType == "NTSC" or releaseInfo.ResolutionType == "PAL" ):
				return PtpMovieSearchResult.__IsInList( self.SdList, [ releaseInfo.Codec ], [ "DVD" ], [ releaseInfo.ResolutionType ] )

		raise PtpUploaderException( "Can't check whether the release '%s' exist on PTP because its type is unsupported." % releaseInfo.ReleaseName );
		
	def __IsSdNonFineSourceReleaseExists(self, releaseInfo):
		# List is ordered by quality. DVD/HD-DVD/Blu-ray is not needed in the list because these have been already checked in IsReleaseExists.
		sourceByQuality = [ "CAM", "TS", "VHS", "TV", "DVD-Screener", "TC", "HDTV", "R5" ]
		
		if releaseInfo.Source not in sourceByQuality: 
			raise PtpUploaderException( "Unsupported source '%s'." % releaseInfo.Source );

		if releaseInfo.Codec == "DivX" or releaseInfo.Codec == "XviD" or releaseInfo.Codec == "H.264" or releaseInfo.Codec == "x264":
			# We check if there is anything with same or better quality.
			sourceIndex = sourceByQuality.index( releaseInfo.Source )
			checkAgainstSources = sourceByQuality[ sourceIndex: ]	
			return PtpMovieSearchResult.__IsInList( self.SdList, [ "DivX", "XviD", "x264", "H.264" ], checkAgainstSources )

		raise PtpUploaderException( "Can't check whether the release '%s' exist on PTP because its type is unsupported." % releaseInfo.ReleaseName );

	def IsMoviePageExists(self):
		return len( self.PtpId ) > 0

	def IsReleaseExists(self, releaseInfo):
		if not self.IsMoviePageExists():
			return None

		# We can't check if a special release is duplicate or not, but only manually edited jobs can be special releases so we allow them without checking.
		if releaseInfo.IsSpecialRelease():
			return None

		self.__ParseMoviePage()

		# If source is not DVD/HD-DVD/Blu-ray then we check if there is a release with any proper quality sources.
		# If there is, we won't add this lower quality release.
		if not PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
			for item in self.SdList:
				if PtpMovieSearchResult.__IsFineSource( item.Source ):
					return item
	
			for item in self.HdList:
				if PtpMovieSearchResult.__IsFineSource( item.Source ):
					return item

		if releaseInfo.IsHighDefinition():
			if PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
				return self.__IsHdFineSourceReleaseExists( releaseInfo )
		elif releaseInfo.IsStandardDefinition():
			if PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
				return self.__IsSdFineSourceReleaseExists( releaseInfo )
			else:
				return self.__IsSdNonFineSourceReleaseExists( releaseInfo )
			
		raise PtpUploaderException( "Can't check whether the release '%s' exists on PTP because its type is unsupported." % releaseInfo.ReleaseName );