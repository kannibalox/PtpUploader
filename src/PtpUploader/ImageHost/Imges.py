from PtpUploaderException import PtpUploaderException
from Settings import Settings

import poster
import simplejson as json

import os
import re
import urllib
import urllib2
import uuid

class Imges:
        RequiredHttpHeader = { "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:18.0) Gecko/20100101 Firefox/18.0" }

        @staticmethod
        def Upload(logger, imagePath = None, imageUrl = None):
                if imageUrl is None:
                        return Imges.__UploadInternal( logger, imagePath, imageUrl )

                # Get image extension from the URL and fall back to Imges.link's rehosting if it's not JPG or PNG.
                fileName, extension = os.path.splitext( imageUrl )
                extension = extension.lower()
                if ( extension != ".jpg" and extension != ".jpeg" and extension != ".png" ):
                        return Imges.__UploadInternal( logger, imagePath, imageUrl )

                # Get a random name for the temporary file.
                imagePath = os.path.join( Settings.GetTemporaryPath(), str( uuid.uuid1() ) + extension )

                # Download image.
                response = urllib2.urlopen( imageUrl )
                response = response.read()
                f = open( imagePath, "wb" )
                f.write( response )
                f.close()

                try:
                        return Imges.__UploadInternal( logger, imagePath, None )
                finally:
                        os.remove( imagePath )

        @staticmethod
        def __UploadInternal(logger, imagePath = None, imageUrl = None):
                response = None

                if imagePath is None: # Rehost image from url.
                        encodedData = urllib.urlencode( { "source": imageUrl } )
                        headers = { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": str( len( encodedData ) ) }
                        headers.update( Imges.RequiredHttpHeader )
                        request = urllib2.Request( "https://imges.link/ptpapi/1/upload/?key=UUuotnQ9TqmFYwvWPZRJe8GpVRyeK2otfmCXn9a7ZUcGfEYrBU&format=json&", encodedData, headers )
                        result = urllib2.urlopen( request )
                        response = result.read()
                else: # Upload image from file.
                        opener = poster.streaminghttp.register_openers()
                        datagen, headers = poster.encode.multipart_encode( [ poster.encode.MultipartParam.from_file( "source", imagePath ) ] )
                        headers.update( Imges.RequiredHttpHeader )
                        request = urllib2.Request( "https://imges.link/ptpapi/1/upload/?key=UUuotnQ9TqmFYwvWPZRJe8GpVRyeK2otfmCXn9a7ZUcGfEYrBU&format=json&", datagen, headers )
                        result = opener.open( request )
                        response = result.read()

                # Response is JSON.
                jsonLoad = None
                try:
                        jsonLoad = json.loads( response )
                except ( Exception, ValueError ):
                        logger.exception( "Got exception while loading JSON response from imges.link. Response: '%s'." % response )
                        raise

                if ( jsonLoad is None ) or len( jsonLoad ) == 1:
                        raise PtpUploaderException( "Got bad JSON response from imges.link. Response: '%s'." % response )

                jsonLoad = jsonLoad[ "image" ]
                imageCode = jsonLoad[ "name" ]
                if ( imageCode is None ) or len( imageCode ) == 0:
                        raise PtpUploaderException( "Got bad JSON response from imges.link: no image code." )

                imageExtension = jsonLoad[ "extension" ]
                if ( imageExtension is None ) or len( imageExtension ) == 0:
                        raise PtpUploaderException( "Got bad JSON response from imges.link: no extension." )

                imageUrl = jsonLoad[ "url" ]
                if ( imageUrl is None ) or len( imageUrl ) == 0:        
                        raise PtpUploaderException( "Got bad JSON response from imges.link: no extension." )

                # return "https://imges.link/images/" + imageCode + "." + imageExtension
                return imageUrl
