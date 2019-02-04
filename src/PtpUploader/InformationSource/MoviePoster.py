from ..MyGlobals import MyGlobals
from ..PtpUploaderException import PtpUploaderException

import re

class MoviePoster:
	# We use The Internet Movie Poster DataBase's embedding code to get the movie poster.
	@staticmethod
	def __GetFromMoviePosterDb(imdbId):
		url = "http://www.movieposterdb.com/embed.inc.php?movie_id=%s" % imdbId 
		result = MyGlobals.session.get( url )
		result.raise_for_status()
		response = result.text

		# Response looks like this:
		# document.write('<a target=\"_new\" href=\"http://www.movieposterdb.com/movie/0333766/Garden-State.html\"><img title=\"Garden State\" alt=\"Garden State\" style=\"width: 100px; height: 143px; border: 0px;\" src=\"http://www.movieposterdb.com/posters/08_11/2004/333766/t_333766_b9a6e423.jpg\" /></a>');
		match = re.search( r'src=\\"(.+)\\"', response )
		if match:
			url = match.group( 1 )
			url = url.replace( "/t_", "/l_" ) # Change thumbnail to full image.
			return url

		return ""

	@staticmethod
	def Get(logger, imdbId):
		logger.info( "Getting movie poster from The Internet Movie Poster DataBase for IMDb id '%s'." % imdbId );
		
		# We don't care if this fails. It gives only extra information.
		try:
			return MoviePoster.__GetFromMoviePosterDb( imdbId )
		except Exception:
			logger.exception( "Got exception while trying to get poster from The Internet Movie Poster DataBase by IMDb id '%s'." % imdbId );

		return ""
