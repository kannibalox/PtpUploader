class TagList:
	def __init__(self, list):
		self.List = list

	def IsContainsTag(self, tag):
		return tag in self.List

	def __IsMatchesAt(self, startIndex, tags):
		for i in range( len( tags.List ) ): 
			if self.List[ startIndex + i ] != tags.List[ i ]:
				return False
			
		return True

	def IsContainsTags(self, tags):
		for i in range( len( self.List ) ):
			if ( i + len( tags.List ) ) > len( self.List ):
				return False

			if self.__IsMatchesAt( i, tags ):
				return True

		return False
	
	def __repr__(self):
		return str( ' '.join( self.List ) )