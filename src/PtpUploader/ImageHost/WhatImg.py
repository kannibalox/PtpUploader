from MyGlobals import MyGlobals
from PtpUploaderException import PtpUploaderException
from Settings import Settings

import poster

import re
import urllib
import urllib2

class WhatImg:
	RequiredHttpHeader = { "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:18.0) Gecko/20100101 Firefox/18.0" }

	@staticmethod
	def __Login(logger):
		opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
		postData = urllib.urlencode( { "username": Settings.WhatImgUsername, "password": Settings.WhatImgPassword } )
		request = urllib2.Request( "https://whatimg.com/users.php?act=login-d", postData, WhatImg.RequiredHttpHeader );
		result = opener.open( request )
		response = result.read()

		if response.find( "You have been successfully logged in." ) == -1:
			raise PtpUploaderException( "Looks like you are not logged in to WhatIMG. Probably due to the bad user name or password in settings." )

	@staticmethod
	def Upload(logger, imagePath = None, imageUrl = None):
		WhatImg.__Login( logger )

		response = None

		if imagePath is None: # Rehost image from url.
			opener = urllib2.build_opener( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )
			postData = urllib.urlencode( { "upload_to": "0", "private_upload": "1", "upload_type": "url-standard", "userfile[]": imageUrl } )
			request = urllib2.Request( "https://whatimg.com/upload.php", postData, WhatImg.RequiredHttpHeader );
			result = opener.open( request )
			response = result.read()
		else: # Upload image from file.
			opener = poster.streaminghttp.register_openers()
			opener.add_handler( urllib2.HTTPCookieProcessor( MyGlobals.CookieJar ) )

			params = { "upload_to": "0", "private_upload": "1", "upload_type": "standard" }
			paramList = params.items()
			paramList.append( poster.encode.MultipartParam.from_file( "userfile[]", imagePath ) )
			datagen, headers = poster.encode.multipart_encode( paramList )

			headers.update( WhatImg.RequiredHttpHeader )
			request = urllib2.Request( "https://whatimg.com/upload.php", datagen, headers )
			result = opener.open( request )
			response = result.read()

		# <a href="http://whatimg.com/viewer.php?file=fjez5.jpg">
		matches = re.search( r"""<a href="https?://whatimg.com/viewer\.php\?file=(.+?)">""", response )
		if matches is None:
			if response.find( "Sorry, but uploading is restricted to registered users." ) == -1:
				raise PtpUploaderException( "WhatIMG embed code not found." )
			else:
				raise PtpUploaderException( "Logged out from WhatIMG while uploading." )

		imageCode = matches.group( 1 )
		return "http://whatimg.com/i/" + imageCode