class TagList:
	def __init__(self, list):
		self.List = list

	def IsContainsTag(self, tag):
		return tag in self.List

	def __IsMatchesAt(self, startIndex, tags):
		if ( startIndex + len( tags ) ) > len( self.List ):
			return False

		for i in range( len( tags ) ): 
			if self.List[ startIndex + i ] != tags[ i ]:
				return False
			
		return True

	def IsContainsTags(self, tags):
		for i in range( len( self.List ) ):
			if self.__IsMatchesAt( i, tags ):
				return True

		return False
	
	def RemoveTagsFromEndIfPossible(self, tags):
		if len( self.List ) <= 0 or len( tags ) <= 0 or len( tags ) > len( self.List ):
			return False

		index = len( self.List ) - len( tags )
		if self.__IsMatchesAt( index, tags ):
			self.List = self.List[ : index ] 
			return True
		
		return False
	
	def __repr__(self):
		return str( ' '.join( self.List ) )