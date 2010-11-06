# Inner exceptions will be only supported in Python 3000... 

class PtpUploaderException(Exception):
	def __init__(self, message):
		Exception.__init__( self, message );