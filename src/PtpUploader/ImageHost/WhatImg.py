from MyGlobals import MyGlobals
from PtpUploaderException import PtpUploaderException
from Settings import Settings

import os
import re

class WhatImg:
	@staticmethod
	def __Login( logger ):
		postData = { "username": Settings.WhatImgUsername, "password": Settings.WhatImgPassword }
		response = MyGlobals.session.post( "https://whatimg.com/users.php?act=login-d", data = postData )

		# Throw exception in case of bad requests (4xx or 5xx).
		response.raise_for_status()

		responseText = response.text

		if responseText.find( "You have been successfully logged in." ) == -1:
			raise PtpUploaderException( "Looks like you are not logged in to WhatIMG. Probably due to the bad user name or password in settings." )

	@staticmethod
	def Upload( logger, imagePath = None, imageUrl = None ):
		WhatImg.__Login( logger )

		response = None

		if imagePath is None: # Rehost image from url.
			postData = { "upload_to": "0", "private_upload": "1", "upload_type": "url-standard", "userfile[]": imageUrl }
			response = MyGlobals.session.post( "https://whatimg.com/upload.php", data = postData )
		else: # Upload image from file.
			with open( imagePath, "rb" ) as file:
				fileName = os.path.basename( imagePath )
				files = { "userfile[]": ( fileName, file ) }
				postData = { "upload_to": "0", "private_upload": "1", "upload_type": "standard" }
				response = MyGlobals.session.post( "https://whatimg.com/upload.php", data = postData, files = files )

		# Throw exception in case of bad requests (4xx or 5xx).
		response.raise_for_status()

		responseText = response.text

		# <a href="http://whatimg.com/viewer.php?file=fjez5.jpg">
		matches = re.search( r"""<a href="https?://whatimg.com/viewer\.php\?file=(.+?)">""", responseText )
		if matches is None:
			if responseText.find( "Sorry, but uploading is restricted to registered users." ) == -1:
				raise PtpUploaderException( "WhatIMG embed code not found." )
			else:
				raise PtpUploaderException( "Logged out from WhatIMG while uploading." )

		imageCode = matches.group( 1 )
		return "http://whatimg.com/i/" + imageCode