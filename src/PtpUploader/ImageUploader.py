from PtpUploaderException import PtpUploaderException;
from Settings import Settings;

import poster;
import simplejson as json;

import urllib;
import urllib2;

class ImageUploader:
	@staticmethod
	def PtpImgUpload(logger, imagePath = None, imageUrl = None):
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
		jsonLoad = None
		try:
			jsonLoad = json.loads( response );
		except Exception:
			logger.error( "Got exception while loading JSON response from ptpimg.me. Response: '%s'." % response )
			raise

		if ( jsonLoad is None ) or len( jsonLoad ) != 1:
			raise PtpUploaderException( "Got bad JSON response from ptpimg.me. Response: '%s'." % response );
		
		jsonLoad = jsonLoad[ 0 ];
		imageCode = jsonLoad[ "code" ];
		if ( imageCode is None ) or len( imageCode ) == 0:
			raise PtpUploaderException( "Got bad JSON response from ptpimg.me: no image code." );

		imageExtension = jsonLoad[ "ext" ];
		if ( imageExtension is None ) or len( imageExtension ) == 0:
			raise PtpUploaderException( "Got bad JSON response from ptpimg.me: no extension." );

		return "http://ptpimg.me/" + imageCode + "." + imageExtension;
	
	def ImageShackUpload(imagePath = None, imageUrl = None):
		# Key is from the official ImageShackUploader. Was lazy to register one. Sorry. :)
		opener = poster.streaminghttp.register_openers()
		data = { "public" : "yes", "rembar": "1", "key": "BXT1Z35V8f6ee0522939d8d7852dbe67b1eb9595" }
		
		if imagePath is None: # Rehost image from url.
			data[ "url" ] = imageUrl
		else: # Upload image from file. 
			data[ "fileupload" ] = open( imagePath, "rb" )
	
		datagen, headers = poster.encode.multipart_encode( data );
		request = urllib2.Request( "http://imageshack.us/upload_api.php", datagen, headers )
		result = opener.open( request )
		response = result.read();
		
		# Response is XML but we won't bother parsing it. A simple regular expression will do.
		match = re.search( r"<image_link>(.+?)</image_link>", response )
		if match is None:
			raise PtpUploaderException( "Got unexpected response from ImageShack. Response: '%s'." % response )

		return match.group( 1 )

	# Based on the imgur API documentation:
	# http://api.imgur.com/resources_anon
	@staticmethod
	def ImgurUpload(logger, imagePath = None, imageUrl = None):
		# Our registered key. Don't use in other programs. :)
		key = "da0a59f9e801a075d5b8b8a40a3204d1"

		datagen = None;
		headers = None;
		if imagePath is None: # Rehost image from url.
			datagen, headers = poster.encode.multipart_encode( { "key": key, "image": imageUrl } );
		else: # Upload image from file.
			datagen, headers = poster.encode.multipart_encode( { "key": key, "image": open( imagePath, "rb" ) } );
		
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
	def Upload(logger, imagePath = None, imageUrl = None):
		if ( imagePath is None ) and ( imageUrl is None ):
			raise PtpUploaderException( "ImageUploader.Update error: both image path and image url are None." );
				
		if ( imagePath is not None ) and ( imageUrl is not None ):
			raise PtpUploaderException( "ImageUploader.Update error: both image path and image url are given." );			

		# TODO: fall back to ImageShack or imgur if the upload to ptpimg wasn't successful. Also start a 1 hour countdown and doesn't use ptpimg till it gets to 0.
		
		if Settings.ImageHost == "ptpimg.me":
			return ImageUploader.PtpImgUpload( logger, imagePath, imageUrl )
		elif Settings.ImageHost == "imageshack":
			return ImageUploader.ImageShackUpload( logger, imagePath, imageUrl )
		elif Settings.ImageHost == "imgur":
			return ImageUploader.ImgurUpload( logger, imagePath, imageUrl )

		raise PtpUploaderException( "Unknown image host: '%'." % Settings.ImageHost )