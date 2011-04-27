# bencode has been moved to pyrobase in newer versions of pyrocore.
try:
	from pyrocore.util import bencode
except ImportError:
	from pyrobase import bencode