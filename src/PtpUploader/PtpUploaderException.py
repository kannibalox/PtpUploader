# Inner exceptions will be only supported in Python 3000... 

class PtpUploaderException(Exception):
	def __init__(self, message):
		Exception.__init__( self, message );

# We handle this exception specially to make it unrecoverable.
# This is needed because to many login attempts with bad user name or password could result in temporary ban.		
class PtpUploaderInvalidLoginException(PtpUploaderException):
	def __init__(self, message):
		PtpUploaderException.__init__( self, message );