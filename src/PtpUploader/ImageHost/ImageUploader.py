from ImageHost.PtpImg import PtpImg
from ImageHost.WhatImg import WhatImg

from PtpUploaderException import PtpUploaderException
from Settings import Settings

class ImageUploader:
	@staticmethod
	def Upload(logger, imagePath = None, imageUrl = None):
		if ( imagePath is None ) and ( imageUrl is None ):
			raise PtpUploaderException( "ImageUploader error: both image path and image url are None." )
				
		if ( imagePath is not None ) and ( imageUrl is not None ):
			raise PtpUploaderException( "ImageUploader error: both image path and image url are given." )	

		# TODO: fall back to secondary host if the upload to ptpimg wasn't successful. Also start a 1 hour countdown and doesn't use ptpimg till it gets to 0.
		
		if Settings.ImageHost == "ptpimg.me":
			return PtpImg.Upload( logger, imagePath, imageUrl )
		elif Settings.ImageHost == "whatimg":
			return WhatImg.Upload( logger, imagePath, imageUrl )
		elif Settings.ImageHost == "imges.link":
			return Imges.Upload( logger, imagePath, imageUrl )

		raise PtpUploaderException( "Unknown image host: '%s'." % Settings.ImageHost )
