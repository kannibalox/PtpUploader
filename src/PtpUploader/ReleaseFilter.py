from Settings import Settings;

class ReleaseFilter:
	@staticmethod
	def IsInAllow(name):
		if len( Settings.AllowRelease ) == 0:
			return True
		
		for allow in Settings.AllowRelease:
			if name.find( allow ) != -1:
				return True
			
		return False

	@staticmethod
	def IsInIgnore(name):
		for ignore in Settings.IgnoreRelease:
			if name.find( ignore ) != -1:
				return True
			
		return False
	
	# This would be nicer with regular expressions but those would need a better (YAML for example) Settings.ini file for easier reading.
	# Returns with None if it is invalid name.
	# Returns with the group name if it is a valid name.
	@staticmethod
	def IsValidReleaseName(name):
		name = name.lower()

		if not ReleaseFilter.IsInAllow( name ):
			return None

		if ReleaseFilter.IsInIgnore( name ):
			return None
		
		name = name.replace( ".", " " )
		name = name.replace( "-", " " )
		parts = name.split( " " )
		if len( parts ) <= 1:
			return None
		
		releaserGroup = parts[ -1 ]; # Last part is the group name. Eg.: Mirrors 2 2010 480p BRRip XviD AC3-ViSiON
		if releaserGroup in Settings.IgnoreReleaserGroup:
			return None
				
		for part in parts:
			if part in Settings.IgnoreReleaseTag:
				return None
		
		return releaserGroup