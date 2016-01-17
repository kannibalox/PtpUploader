from Settings import Settings

class SevenZip:
    @staticmethod
    def Extract(archivePath, destinationPath):
        args = [ Settings.SevenZipPath, 'x', '-o', destinationPath, archivePath ]
