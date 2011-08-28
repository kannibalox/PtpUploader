from Tool.Unrar import Unrar

from Helper import GetFileListFromTorrent
from Settings import Settings

import simplejson as json

import os

class IncludedFileItemState:
	DefaultIgnore     = 0
	DefaultInclude    = 1
	DefaultIncludeRar = 2
	Ignore            = 3
	Include           = 4

class IncludedFileItem:
	def __init__(self, name):
		self.Name = name # Path separator is always a "/".
		self.State = self.__GetDefaultState()

	def __GetDefaultState(self):
		path = self.Name.lower()
		
		# Ignore special root directories.
		# !sample is used in HDBits releases.
		if path.startswith( "proof/" ) or path.startswith( "sample/" ) or path.startswith( "!sample/" ):
			return IncludedFileItemState.DefaultIgnore

		name = os.path.basename( path )
		if Settings.IsFileOnIgnoreList( name ):
			return IncludedFileItemState.DefaultIgnore

		if Settings.HasValidVideoExtensionToUpload( name ) or Settings.HasValidAdditionalExtensionToUpload( name ):
			return IncludedFileItemState.DefaultInclude
		elif Unrar.IsFirstRar( name ):
			return IncludedFileItemState.DefaultIncludeRar
		else:
			return IncludedFileItemState.DefaultIgnore

	def IsDefaultIgnored(self):
		return self.State == IncludedFileItemState.DefaultIgnore

	def IsIgnored(self):
		return self.IsDefaultIgnored() or self.State == IncludedFileItemState.Ignore

	def IsDefaultIncluded(self):
		return self.State == IncludedFileItemState.DefaultInclude or self.State == IncludedFileItemState.DefaultIncludeRar

	def IsIncluded(self):
		return self.IsDefaultIncluded() or self.State == IncludedFileItemState.Include

	def IsCustomized(self):
		return self.State == IncludedFileItemState.Ignore or self.State == IncludedFileItemState.Include

class IncludedFileList:
	def __init__(self):
		self.Files = [] # Contains IncludedFileItems.

	def __GetFile(self, path):
		pathLower = path.lower()
		for file in self.Files:
			if file.Name.lower() == pathLower:
				return file

		return None

	def IsIgnored(self, path):
		file = self.__GetFile( path )
		return file and file.IsIgnored()

	def IsIncluded(self, path):
		file = self.__GetFile( path )
		return file and file.IsIncluded()

	def FromTorrent(self, torrentFilePath):
		self.Files = []
		fileList = GetFileListFromTorrent( torrentFilePath )
		for file in fileList:
			self.Files.append( IncludedFileItem( file ) )

	def __FromDirectoryInternal(self, path, baseRelativePath):
		entries = os.listdir( path )
		for entry in entries:
			absolutePath = os.path.join( path, entry )
			relativePath = entry
			if len( baseRelativePath ) > 0:
				relativePath = baseRelativePath + u"/" + entry
			
			if os.path.isdir( absolutePath ):
				self.__FromDirectoryInternal( absolutePath, relativePath )
			elif os.path.isfile( absolutePath ):
				self.Files.append( IncludedFileItem( relativePath ) )
						
	def FromDirectory(self, path):
		self.Files = []
		self.__FromDirectoryInternal( path, u"" )

	def ApplyCustomizationFromJson(self, jsonString):
		if len( jsonString ) <= 0:
			return

		# Key contains the path, value contains the include state (as bool).		
		dictionary = json.loads( jsonString )
		for path, include in dictionary.items():
			file = self.__GetFile( path )
			if file is None:
				file = IncludedFileItem( path )
				self.Files.append( file )

			# Only set new state if it differs from the default state.
			if include:
				if not file.IsDefaultIncluded():
					file.State = IncludedFileItemState.Include
			else:
				if not file.IsDefaultIgnored():
					file.State = IncludedFileItemState.Ignore