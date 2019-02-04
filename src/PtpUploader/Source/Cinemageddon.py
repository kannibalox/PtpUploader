from ..InformationSource.Imdb import Imdb
from ..Job.JobRunningState import JobRunningState
from .SourceBase import SourceBase

from ..Helper import DecodeHtmlEntities, GetSizeFromText, RemoveDisallowedCharactersFromPath, ValidateTorrentFile
from ..MyGlobals import MyGlobals
from ..PtpUploaderException import PtpUploaderException

import os
import re

class Cinemageddon(SourceBase):
    def __init__(self):
        SourceBase.__init__( self )

        self.Name = "cg"
        self.NameInSettings = "Cinemageddon"

    def IsEnabled(self):
        return len( self.Username ) > 0 and len( self.Password ) > 0

    def Login( self ):
        MyGlobals.Logger.info( "Logging in to Cinemageddon." )

        postData = { "username": self.Username, "password": self.Password }
        result = MyGlobals.session.post( "http://cinemageddon.net/takelogin.php", data = postData )
        result.raise_for_status()
        self.__CheckIfLoggedInFromResponse( result.text )

    def __CheckIfLoggedInFromResponse( self, response ):
        if response.find( 'action="takelogin.php"' ) != -1:
            raise PtpUploaderException( "Looks like you are not logged in to Cinemageddon. Probably due to the bad user name or password in settings." )

    def __ParsePage( self, logger, releaseInfo, html, parseForExternalCreateJob = False ):
        # Make sure we only get information from the description and not from the comments.
        descriptionEndIndex = html.find( '<p><a name="startcomments"></a></p>' )
        if descriptionEndIndex == -1:
            raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Description can't found on torrent page. Probably the layout of the site has changed." )

        description = html[ :descriptionEndIndex ]

        # We will use the torrent's name as release name.
        if not parseForExternalCreateJob:
            matches = re.search( r'href="download.php\?id=(\d+)&name=.+">(.+)\.torrent</a>', description )
            if matches is None:
                raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Can't get release name from torrent page." )

            releaseInfo.ReleaseName = DecodeHtmlEntities( matches.group( 2 ) )

        # Get source and format type
        sourceType = ""
        formatType = ""
        if ( not releaseInfo.IsSourceSet() ) or ( not releaseInfo.IsCodecSet() ):
            matches = None
            if parseForExternalCreateJob:
                matches = re.search( r'torrent details for "(.+) \[(\d+)/(.+)/(.+)\]"', description )
            else:
                matches = re.search( r"torrent details for &quot;(.+) \[(\d+)/(.+)/(.+)\]&quot;", description )

            if matches is None:
                raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Can't get release source and format type from torrent page." )

            sourceType = matches.group( 3 )
            formatType = matches.group( 4 )

            if '/' in sourceType and not releaseInfo.ResolutionType:
                sourceType, _, resolutionType = sourceType.partition( '/' )
                resolutionType.strip( 'p' )
                if resolutionType in ["720", "1080"]:
                    releaseInfo.ResolutionType = resolutionType

        # Get IMDb id.
        if ( not releaseInfo.HasImdbId() ) and ( not releaseInfo.HasPtpId() ):
            matches = re.search(r'<span id="torrent_imdb">(.*?)</span>', description).group(1).replace('t', '').split(' ')
            if not matches:
                raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "IMDb id can't be found on torrent page." )
            elif len(matches) > 1:
                raise PtpUploaderException( JobRunningState.Ignored_MissingInfo, "Multiple IMDb IDs found on page." )

            releaseInfo.ImdbId = matches[0]

        # Get size.
        # Two possible formats:
        # <tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align="left">1.46 GB (1,570,628,119 bytes)</td></tr>
        # <tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align=left>1.46 GB (1,570,628,119 bytes)</td></tr>
        matches = re.search( r"""<tr><td class="rowhead" valign="top" align="right">Size</td><td valign="top" align="?left"?>.+ \((.+ bytes)\)</td></tr>""", description )
        if matches is None:
            logger.warning( "Size not found on torrent page." )
        else:
            size = matches.group( 1 )
            releaseInfo.Size = GetSizeFromText( size )

        # Ignore XXX releases.
        if description.find( '>Type</td><td valign="top" align=left>XXX<' ) != -1:
            raise PtpUploaderException( JobRunningState.Ignored_Forbidden, "Marked as XXX." )

        self.__MapSourceAndFormatToPtp( releaseInfo, sourceType, formatType, html )

        # Make sure that this is not a wrongly categorized DVDR.
        if ( not releaseInfo.IsDvdImage() ) and ( re.search( r"\.vob</td>", description, re.IGNORECASE ) or re.search( r"\.iso</td>", description, re.IGNORECASE ) ):
            raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Wrongly categorized DVDR." )

    def __DownloadNfo( self, logger, releaseInfo ):
        url = "http://cinemageddon.net/details.php?id=%s&filelist=1" % releaseInfo.AnnouncementId
        logger.info( "Collecting info from torrent page '%s'." % url )

        result = MyGlobals.session.get( url )
        result.raise_for_status()
        response = result.text
        self.__CheckIfLoggedInFromResponse( response )

        self.__ParsePage( logger, releaseInfo, response )

    def __MapSourceAndFormatToPtp(self, releaseInfo, sourceType, formatType, html):
        sourceType = sourceType.lower()
        formatType = formatType.lower()


        if releaseInfo.IsSourceSet():
            releaseInfo.Logger.info( "Source '%s' is already set, not getting from the torrent page." % releaseInfo.Source )
        elif sourceType in [ "dvdrip", "dvd-r" ]:
            releaseInfo.Source = "DVD"
        elif sourceType == "vhsrip":
            releaseInfo.Source = "VHS"
        elif sourceType == "tvrip":
            releaseInfo.Source = "TV"
        elif sourceType in [ "webrip", "web-dl" ]:
            releaseInfo.Source = "WEB"
        else:
            raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Unsupported source type '%s'." % sourceType )

        if releaseInfo.IsCodecSet():
            releaseInfo.Logger.info( "Codec '%s' is already set, not getting from the torrent page." % releaseInfo.Codec )
        elif formatType == "x264":
            releaseInfo.Codec = "x264"
        elif formatType == "xvid":
            releaseInfo.Codec = "XviD"
        elif formatType == "divx":
            releaseInfo.Codec = "DivX"
        elif formatType == "dvd-r":
            if releaseInfo.Size > 4700000000:
                releaseInfo.Codec = "DVD9"
            else:
                releaseInfo.Codec = "DVD5"
        else:
            raise PtpUploaderException( JobRunningState.Ignored_NotSupported, "Unsupported format type '%s'." % formatType )

        # Adding BDrip support would be problematic because there is no easy way to decide if it is HD or SD.
        # Maybe we could use the resolution and file size. But what about the oversized and upscaled releases?

        if releaseInfo.IsResolutionTypeSet():
            releaseInfo.Logger.info( "Resolution type '%s' is already set, not getting from the torrent page." % releaseInfo.ResolutionType )
        elif releaseInfo.IsDvdImage():
            if re.search( r'Standard +: NTSC', html ):
                releaseInfo.ResolutionType = 'NTSC'
            elif re.search( r'Standard +: PAL', html ):
                releaseInfo.ResolutionType = 'PAL'
            else:
                releaseInfo.Logger.info( "DVD detected but could not find resolution" )
        else:
            releaseInfo.ResolutionType = "Other"

        if releaseInfo.IsDvdImage() and not releaseInfo.Container:
            if re.search( r"\.vob</td>", html, re.IGNORECASE ):
                releaseInfo.Container = "VOB IFO"
            elif re.search( r"\.iso</td>", html, re.IGNORECASE ):
                releaseInfo.Container = "ISO"
            else:
                releaseInfo.Logger.info( "DVD detected but could not find container" )

    def PrepareDownload(self, logger, releaseInfo):
        if releaseInfo.IsUserCreatedJob():
            self.__DownloadNfo( logger, releaseInfo )
        else:
            # TODO: add filtering support for Cinemageddon
            # In case of automatic announcement we have to check the release name if it is valid.
            # We know the release name from the announcement, so we can filter it without downloading anything (yet) from the source.
            #if not ReleaseFilter.IsValidReleaseName( releaseInfo.ReleaseName ):
            #    logger.info( "Ignoring release '%s' because of its name." % releaseInfo.ReleaseName )
            #    return None
            self.__DownloadNfo( logger, releaseInfo )

    def ParsePageForExternalCreateJob( self, logger, releaseInfo, html ):
        self.__ParsePage( logger, releaseInfo, html, parseForExternalCreateJob = True )

    def DownloadTorrent(self, logger, releaseInfo, path):
        url = "http://cinemageddon.net/download.php?id=%s" % releaseInfo.AnnouncementId
        logger.info( "Downloading torrent file from '%s' to '%s'." % ( url, path ) )

        result = MyGlobals.session.get( url )
        result.raise_for_status()
        response = result.content
        self.__CheckIfLoggedInFromResponse( response )

        # The number of maximum simultaneous downloads is limited on Cinemageddon.
        if response.find( "<h2>Max Torrents Reached</h2>" ) != -1:
            raise PtpUploaderException( "Maximum torrents reached on CG." )

        with open( path, "wb" ) as fh:
            fh.write( response )

        ValidateTorrentFile( path )

    # Because some of the releases on CG do not contain the full name of the movie, we have to rename them because of the uploading rules on PTP.
    # The new name will be formatted like this: Movie Name Year
    def GetCustomUploadPath(self, logger, releaseInfo):
        # TODO: if the user forced a release name, then let it upload by that name.
        if releaseInfo.IsZeroImdbId():
            raise PtpUploaderException( "Uploading to CG with zero IMDb ID is not yet supported." % text )

        # If the movie already exists on PTP then the IMDb info is not populated in ReleaseInfo.
        if len( releaseInfo.InternationalTitle ) <= 0 or len( releaseInfo.Year ) <= 0:
            imdbInfo = Imdb.GetInfo( logger, releaseInfo.GetImdbId() )
            if len( releaseInfo.InternationalTitle ) <= 0:
                releaseInfo.InternationalTitle = imdbInfo.Title
            if len( releaseInfo.Year ) <= 0:
                releaseInfo.Year = imdbInfo.Year

        if len( releaseInfo.InternationalTitle ) <= 0:
            raise PtpUploaderException( "Can't rename release because international title is empty." )

        if releaseInfo.Year:
            raise PtpUploaderException( "Can't rename release because year is empty." )

        name = "%s (%s) %s %s" % ( releaseInfo.InternationalTitle, releaseInfo.Year, releaseInfo.Source, releaseInfo.Codec )
        name = RemoveDisallowedCharactersFromPath( name )

        logger.info( "Upload directory will be named '%s' instead of '%s'." % ( name, releaseInfo.ReleaseName ) )

        newUploadPath = releaseInfo.GetReleaseUploadPath()
        newUploadPath = os.path.dirname( newUploadPath )
        newUploadPath = os.path.join( newUploadPath, name )
        return newUploadPath

    def IncludeReleaseNameInReleaseDescription(self):
        return False

    def GetIdFromUrl(self, url):
        result = re.match( r".*cinemageddon\.net/details.php\?id=(\d+).*", url )
        if result is None:
            return ""
        else:
            return result.group( 1 )

    def GetUrlFromId(self, id):
        return "http://cinemageddon.net/details.php?id=" + id
