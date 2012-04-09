from Helper import GetSizeFromText
from NfoParser import NfoParser
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
# - We support the checking of possible co-existence for different sized SD XviDs. (E.g.: an 1400 MB upload won't be treated as a duplicate of a 700 MB release.) 
class PtpMovieSearchResult:
	def __init__(self, ptpId, moviePageHtml):
		self.PtpId = ptpId;
		self.MoviePageHtml = None
		self.ImdbId = ""
		self.SdList = []
		self.HdList = []
		self.OtherList = []

		if moviePageHtml is not None:
			# Do not search in the comments.
			startOfComments = moviePageHtml.find( """<div class="linkbox"><a name="comments"></a>""" )
			if startOfComments == -1:
				raise PtpUploaderException( "Can't find the start of the comments. Probably the layout of PTP has changed." )

			# Can't assign directly to MoviePageHtml because __repr__ calls __ParseMoviePage which sets MoviePageHtml to None before the GetImdbId line. (When debugging.)
			moviePageHtml = moviePageHtml[ :startOfComments ]
			self.MoviePageHtml = moviePageHtml
			self.ImdbId = NfoParser.GetImdbId( moviePageHtml )

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
			# Remove bold from trumpable and freeleech texts.
			# Remove coloring that mark seeded and downloaded torrents.
			# x264 / MKV / DVD / 716x432 / <strong class="ti_fl">Freeleech (13h27m left) </strong>
			# x264 / MP4 / DVD / 720x400 / <strong class="ti_fl">Freeleech (22h17m left) </strong> / <strong class="ti_rp" style="color:Red">Reported</strong>
			# <span class="tc_uploads" style="float:none;color:Purple"><strong>x264 / MKV / DVD / 716x432 / <strong class="ti_fl">Freeleech (13h27m left) </strong></strong></span>
			fullTitle = regexFind[ 0 ]
			fullTitle = re.sub( """<strong.*?>""", "", fullTitle )
			fullTitle = re.sub( """</strong>""", "", fullTitle )
			fullTitle = re.sub( """<span.*?>""", "", fullTitle )
			fullTitle = re.sub( """</span>""", "", fullTitle )

			# This regular expression could be in the long regular expression below, done this way for compatiblity.
			sizeText = regexFind[ 1 ]
			sizeMatch = re.match( """<span style="float: left;" title="(.+? bytes)">.+</span>""", sizeText )
			if sizeMatch is not None:
				sizeText = sizeMatch.group( 1 )

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
		sdMatch = re.search( """class="edition_info"><strong>.+?</strong> - Standard Definition""", html )
		if ( sdMatch is not None ) and ( sdMatch.start() > 0 ):
			sortedSections.append( ( sdMatch.start(), self.SdList ) )
		hdMatch = re.search( """class="edition_info"><strong>.+?</strong> - High Definition""", html )
		if ( hdMatch is not None ) and ( hdMatch.start() > 0 ):
			sortedSections.append( ( hdMatch.start(), self.HdList ) )
		otherMatch = re.search( """class="edition_info"><strong>.+?</strong> - Other""", html )
		if ( otherMatch is not None ) and ( otherMatch.start() > 0 ):
			sortedSections.append( ( otherMatch.start(), self.OtherList ) )
			
		if len( sortedSections ) <= 0:
			raise PtpUploaderException( "Error! Movie page doesn't contain any torrents." );
			
		sortedSections.sort()

		# Well, the following regular expression is a bit long. :)
		# There are variations for the address because the normal, downloaded/seeding, freeleech and reported torrents. Few examples:
		# <a href="#" onclick="$('#torrent_37673').toggle(); show_description('35555', '62113'); return false;">XviD / AVI / DVD / 720x420</a>
		# <a href="#" onclick="$('#torrent_55714').toggle(); show_description('35555', '62113'); return false;"><span style="float:none;color:#E5B244;"><strong>XviD / AVI / DVD / 608x256 / Scene</strong></span></a>
		# <a href="#" onclick="$('#torrent_125279').toggle(); show_description('14181', '125279'); return false;"><span class="tc_uploads" style="float:none;color:Purple"><strong>x264 / MKV / DVD / 716x432 / <strong class="ti_fl">Freeleech (13h27m left) </strong></strong></span></a>
		regEx = re.compile(
			"""<tr class="group_torrent" style="font-weight: normal;">"""\
			""".+?<a href="#" onclick="\$\('#torrent_\d+'\)\.toggle\(\);.+?">(.+?)</a>"""\
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
			if ( ( codecs is None ) or ( item.Codec in codecs ) ) \
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
		
		raise PtpUploaderException( "Can't check whether the release exist on PTP because its type is unsupported." )

	def __IsHdNonFineSourceReleaseExists(self, releaseInfo):
		# List is ordered by quality. HD DVD/Blu-ray is not needed in the list because these have been already checked in IsReleaseExists.
		# RC = Region C ("Russian" Blu-ray).
		sourceByQuality = [ "HDTV", "RC" ]
		
		if releaseInfo.Source not in sourceByQuality: 
			raise PtpUploaderException( "Unsupported source '%s'." % releaseInfo.Source );

		# We check if there is anything with same or better quality.
		sourceIndex = sourceByQuality.index( releaseInfo.Source )
		checkAgainstSources = sourceByQuality[ sourceIndex: ]	

		if releaseInfo.ResolutionType == "1080p":
			return PtpMovieSearchResult.__IsInList( self.HdList, [ "x264", "H.264" ], checkAgainstSources, [ "1080p" ] )
		elif releaseInfo.ResolutionType == "720p":
			return PtpMovieSearchResult.__IsInList( self.HdList, [ "x264", "H.264" ], checkAgainstSources, [ "720p" ] )
		
		raise PtpUploaderException( "Can't check whether the release exist on PTP because its type is unsupported." )

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
	# "PAL and NTSC may co-exist, as may DVD5 and DVD9." 
	def __IsSdFineSourceReleaseExists(self, releaseInfo):
		# 600 MB seems like a good choice. Comparing by size ratio wouldn't be too effective.
		minimumSizeDifferenceToCoExist = 600 * 1024 * 1024
		
		if releaseInfo.Source == "Blu-ray" or releaseInfo.Source == "HD-DVD" or releaseInfo.Source == "DVD":
			if releaseInfo.Codec == "x264" or releaseInfo.Codec == "H.264":
				# We can't check to co-existence for SD x264s, because the co-existence rule is quality based.
				return PtpMovieSearchResult.__IsInList( self.SdList, [ "x264", "H.264" ], [ "Blu-ray", "HD-DVD", "DVD" ] )
			elif releaseInfo.Codec == "XviD" or releaseInfo.Codec == "DivX":
				list = PtpMovieSearchResult.__GetListOfMatches( self.SdList, [ "XviD", "DivX" ], [ "Blu-ray", "HD-DVD", "DVD" ] )
				return PtpMovieSearchResult.__CanCoExist( list, releaseInfo, minimumSizeDifferenceToCoExist )
			elif releaseInfo.IsDvdImage():
				if releaseInfo.ResolutionType == "NTSC" or releaseInfo.ResolutionType == "PAL":
					return PtpMovieSearchResult.__IsInList( self.SdList, [ releaseInfo.Codec ], [ "DVD" ], [ releaseInfo.ResolutionType ] )
				else:
					raise PtpUploaderException( "Can't check whether the DVD image exist on PTP because resolution (NTSC or PAL) is not set." )

		raise PtpUploaderException( "Can't check whether the release exist on PTP because its type is unsupported." )
		
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

		raise PtpUploaderException( "Can't check whether the release exist on PTP because its type is unsupported." )

	def IsMoviePageExists(self):
		return len( self.PtpId ) > 0

	def IsReleaseExists(self, releaseInfo):
		if not self.IsMoviePageExists():
			return None

		# We can't check if a special release is duplicate or not, but only manually edited jobs can be special releases so we allow them without checking.
		if releaseInfo.IsSpecialRelease():
			return None

		self.__ParseMoviePage()

		# If source is not DVD/HD-DVD/Blu-ray then we check if there is a release with any proper quality (retail) sources.
		# If there is, we won't add this lower quality release.
		if not PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
			if releaseInfo.IsHighDefinition():
				# If HD retail release already exists, then we don't allow a pre-retail HD release.
				for item in self.HdList:
					if PtpMovieSearchResult.__IsFineSource( item.Source ):
						return item

				# If SD release with retail HD source already exists, then we don't allow a pre-retail HD release.
				# E.g.: if a Blu-ray sourced SD XviD exists, then we don't allow a 720p HDTV rip.
				list = PtpMovieSearchResult.__GetListOfMatches( self.SdList, None, [ "Blu-ray", "HD-DVD" ] )
				if len( list ) > 0:
					return list[ 0 ]
			elif releaseInfo.IsStandardDefinition():
				# If either SD or HD retail release already exists, then we don't allow a pre-retail SD release.

				for item in self.SdList:
					if PtpMovieSearchResult.__IsFineSource( item.Source ):
						return item
	
				for item in self.HdList:
					if PtpMovieSearchResult.__IsFineSource( item.Source ):
						return item
			else:
				raise PtpUploaderException( "Can't check whether the release exists on PTP because its type is unsupported." );

		if releaseInfo.IsHighDefinition():
			if PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
				return self.__IsHdFineSourceReleaseExists( releaseInfo )
			else:
				return self.__IsHdNonFineSourceReleaseExists( releaseInfo )
		elif releaseInfo.IsStandardDefinition():
			if PtpMovieSearchResult.__IsFineSource( releaseInfo.Source ):
				return self.__IsSdFineSourceReleaseExists( releaseInfo )
			else:
				return self.__IsSdNonFineSourceReleaseExists( releaseInfo )
			
		raise PtpUploaderException( "Can't check whether the release exists on PTP because its type is unsupported." )

def UnitTest():
	def IsReleaseExists( searchResult, expectedResult, searchResultItem ):
		from ReleaseInfo import ReleaseInfo
		releaseInfo = ReleaseInfo()
		releaseInfo.Codec = searchResultItem.Codec
		releaseInfo.Container = searchResultItem.Container
		releaseInfo.Source = searchResultItem.Source
		releaseInfo.ResolutionType = searchResultItem.Resolution
		releaseInfo.Size = searchResultItem.Size
		result = searchResult.IsReleaseExists( releaseInfo )
		if result is None:
			if expectedResult:
				print "Unexpected result"
		else:
			if not expectedResult:
				print "Unexpected result"

	# Same size.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "DVD", "1x1", "700 MB" ) )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1x1", "700 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "720p", "4500 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1080p", "8000 MB" ) )

		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "XviD", "AVI", "Blu-ray", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "720p", "4500 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1080p", "8000 MB" ) )

	# Under size.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "DVD", "1x1", "1400 MB" ) )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1x1", "1400 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "720p", "6500 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1080p", "12500 MB" ) )

		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "XviD", "AVI", "Blu-ray", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "720p", "4500 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1080p", "8000 MB" ) )

	# Over size.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "DVD", "1x1", "700 MB" ) )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1x1", "700 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "720p", "4500 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1080p", "8000 MB" ) )

		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "XviD", "AVI", "Blu-ray", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "720p", "6500 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1080p", "12500 MB" ) )

	# No pre-retail if retail exists.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "DVD", "1x1", "700 MB" ) )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "DVD", "1x1", "700 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "720p", "4500 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1080p", "8000 MB" ) )

		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "XviD", "AVI", "VHS", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "DVD-Screener", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "HDTV", "720p", "6500 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "RC", "1080p", "12500 MB" ) )

	# SD pre-retail is not allowed if HD retail exists.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "720p", "4500 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "1080p", "8000 MB" ) )

		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "XviD", "AVI", "R5", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "DVD-Screener", "1x1", "1400 MB" ) )

	# HD pre-retail is allowed if only non-HD sourced retail SD exists.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "DVD", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "HDTV", "720p", "6500 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "RC", "1080p", "12500 MB" ) )

	# HD pre-retail is not allowed if HD sourced retail SD exists.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "Blu-ray", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "HDTV", "720p", "6500 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "RC", "1080p", "12500 MB" ) )

	# Only one pre-retail is allowed per category regardless of size.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "R5", "1x1", "700 MB" ) )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "R5", "1x1", "700 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "RC", "720p", "4500 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "RC", "1080p", "8000 MB" ) )

		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "XviD", "AVI", "R5", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "R5", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "RC", "720p", "6500 MB" ) )
		IsReleaseExists( searchResult, True, PtpMovieSearchResultItem( "", "x264", "MKV", "RC", "1080p", "12500 MB" ) )

	# Pre-retail trumping other pre-retail.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "CAM", "1x1", "700 MB" ) )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "TV", "1x1", "700 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "HDTV", "720p", "4500 MB" ) )

		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "XviD", "AVI", "DVD-Screener", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "R5", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "RC", "720p", "4500 MB" ) )

	# Retail trumping pre-retail.
	if True:
		searchResult = PtpMovieSearchResult( "1", None )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "XviD", "AVI", "CAM", "1x1", "1400 MB" ) )
		searchResult.SdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "TV", "1x1", "1400 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "HDTV", "720p", "6500 MB" ) )
		searchResult.HdList.append( PtpMovieSearchResultItem( "", "x264", "MKV", "HDTV", "720p", "12500 MB" ) )

		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "XviD", "AVI", "DVD", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "XviD", "AVI", "DVD", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "DVD", "1x1", "700 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "DVD", "1x1", "1400 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "720p", "4500 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "Blu-ray", "720p", "6500 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "1080p", "8500 MB" ) )
		IsReleaseExists( searchResult, False, PtpMovieSearchResultItem( "", "x264", "MKV", "HD-DVD", "1080p", "12500 MB" ) )

if __name__ == "__main__":
	UnitTest()
