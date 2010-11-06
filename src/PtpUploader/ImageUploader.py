from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import poster;
import simplejson as json;

import urllib;
import urllib2;

class ImageUploader:
	@staticmethod
	def PtpImgUpload(imagePath = None, imageUrl = None):
		response = None;
		
		if imagePath is None: # Rehost image from url.
			encodedData = urllib.urlencode( { "urls": imageUrl } );
			headers = { "Content-Type": "application/x-www-form-urlencoded", "Content-Length": str( len( encodedData ) ) };
			request = urllib2.Request( "http://ptpimg.me?type=uploadv2&key=QT5LGz7ktGFVZpfFArVHCpEvDcC3qrUZrf0kP&uid=999999&url=c_h_e_c_k_p_o_s_t", encodedData, headers )
			result = urllib2.urlopen( request )
			response = result.read();
		else: # Upload image from file.
			opener = poster.streaminghttp.register_openers()
			datagen, headers = poster.encode.multipart_encode( [ poster.encode.MultipartParam.from_file( "uploadfile", imagePath ) ] );
			request = urllib2.Request( "http://ptpimg.me?type=uploadv3&key=QT5LGz7ktGFVZpfFArVHCpEvDcC3qrUZrf0kP", datagen, headers )
			result = opener.open( request )
			response = result.read();
		
		# Response is JSON.
		# [{"status":1,"code":"8qy8is","ext":"jpg"}]
		jsonLoad = json.loads( response );
		if ( jsonLoad is None ) or len( jsonLoad ) != 1:
			raise PtpUploaderException( "Got bad JSON response from ptpimg.me: '%s'." % response );
		
		jsonLoad = jsonLoad[ 0 ];
		imageCode = jsonLoad[ "code" ];
		if ( imageCode is None ) or len( imageCode ) == 0:
			raise PtpUploaderException( "Got bad JSON response from ptpimg.me: no image code." );

		imageExtension = jsonLoad[ "ext" ];
		if ( imageExtension is None ) or len( imageExtension ) == 0:
			raise PtpUploaderException( "Got bad JSON response from ptpimg.me: no extension." );

		return "http://ptpimg.me/" + imageCode + "." + imageExtension;
	
	# Based on the imgur API documentation:
	# http://api.imgur.com/resources_anon
	@staticmethod
	def ImgurUpload(imagePath = None, imageUrl = None):
		datagen = None;
		headers = None;
		if imagePath is None: # Rehost image from url.
			datagen, headers = poster.encode.multipart_encode( { "key": Settings.ImgurApiKey, "image": imageUrl } );
		else: # Upload image from file.
			datagen, headers = poster.encode.multipart_encode( { "key": Settings.ImgurApiKey, "image": open( imagePath, "rb" ) } );
		
		opener = poster.streaminghttp.register_openers()
		request = urllib2.Request( "http://api.imgur.com/2/upload.json", datagen, headers )
		result = opener.open( request )
		response = result.read();
		
		# Parse the response.
		jsonLoad = json.loads( response );
		upload = jsonLoad[ "upload" ];
		links = upload[ "links" ];
		link = links[ "original" ]
		if ( link is None ) or len( link ) == 0:
			raise PtpUploaderException( "Got bad JSON response from imgur: no image link." );
				
		return link;
	
	@staticmethod
	def Upload(imagePath = None, imageUrl = None):
		if ( imagePath is None ) and ( imageUrl is None ):
			raise PtpUploaderException( "ImageUploader.Update error: both image path and image url are None." );
				
		if ( imagePath is not None ) and ( imageUrl is not None ):
			raise PtpUploaderException( "ImageUploader.Update error: both image path and image url are given." );			

		# TODO: fall back to imgur if the upload to ptpimg wasn't successful. Also start a 1 hour countdown and doesn't use ptpimg till it gets to 0.  

		return ImageUploader.PtpImgUpload( imagePath, imageUrl );
		#return ImageUploader.ImgurUpload( imagePath, imageUrl );
