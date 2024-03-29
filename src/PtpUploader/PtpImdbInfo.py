import json
import re

from PtpUploader import Ptp
from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpUploaderException import *


class PtpImdbInfo:
    def __init__(self, imdbId):
        self.ImdbId = imdbId
        self.JsonResponse = ""
        self.JsonMovie = None

    def __LoadmdbInfo(self):
        # Already loaded
        if self.JsonMovie is not None:
            return

        # Get IMDb info through PTP's ajax API used by the site when the user presses the auto fill button.
        result = MyGlobals.session.get(
            "https://passthepopcorn.me/ajax.php?action=torrent_info&imdb=%s"
            % Ptp.NormalizeImdbIdForPtp(self.ImdbId)
        )
        self.JsonResponse = result.text
        Ptp.CheckIfLoggedInFromResponse(result, self.JsonResponse)

        # The response is JSON.
        # [{"title":"Devil's Playground","plot":"As the world succumbs to a zombie apocalypse, Cole a hardened mercenary, is chasing the one person who can provide a cure. Not only to the plague but to Cole's own incumbent destiny. DEVIL'S PLAYGROUND is a cutting edge British horror film that features zombies portrayed by free runners for a terrifyingly authentic representation of the undead","art":false,"year":"2010","director":[{"imdb":"1654324","name":"Mark McQueen","role":null}],"tags":"action, horror","writers":[{"imdb":"1057010","name":"Bart Ruspoli","role":" screenplay"}]}]

        jsonResult = json.loads(self.JsonResponse)
        if len(jsonResult) != 1:
            raise PtpUploaderException(
                "Bad PTP movie info JSON response: array length is not one.\nFull response:\n%s"
                % self.JsonResponse
            )
        if not jsonResult[0]:
            raise PtpUploaderException(
                "Bad PTP movie info JSON response: no movie info. Perhaps the IMDb ID has been moved?"
            )
        self.JsonMovie = jsonResult[0]

    def GetTitle(self):
        self.__LoadmdbInfo()
        title = self.JsonMovie["title"]
        if (title is None) or len(title) == 0:
            raise PtpUploaderException(
                "Bad PTP movie info JSON response: title is empty.\nFull response:\n%s"
                % self.JsonResponse
            )
        return title

    def GetYear(self):
        self.__LoadmdbInfo()
        year = self.JsonMovie["year"]
        if (year is None) or len(year) == 0:
            raise PtpUploaderException(
                "Bad PTP movie info JSON response: year is empty.\nFull response:\n%s"
                % self.JsonResponse
            )
        return year

    def GetMovieDescription(self):
        self.__LoadmdbInfo()
        movieDescription = self.JsonMovie["plot"]
        if movieDescription is None:
            return ""
        return movieDescription

    def GetTags(self):
        self.__LoadmdbInfo()
        tags = self.JsonMovie["tags"]
        if tags is None:
            raise PtpUploaderException(
                "Bad PTP movie info JSON response: tags key doesn't exists.\nFull response:\n%s"
                % self.JsonResponse
            )
        return tags

    def GetCoverArtUrl(self):
        self.__LoadmdbInfo()
        coverArtUrl = self.JsonMovie["art"]
        if coverArtUrl is None:
            raise PtpUploaderException(
                "Bad PTP movie info JSON response: art key doesn't exists.\nFull response:\n%s"
                % self.JsonResponse
            )

        # It may be false... Eg.: "art": false
        if isinstance(coverArtUrl, str):
            # Maximize height in 768 pixels.
            # Example links:
            # http://ia.media-imdb.com/images/M/MV5BMTM2MjE0NTcwNl5BMl5BanBnXkFtZTcwOTM0MDQ1NA@@._V1._SY317_CR1,0,214,317_.jpg
            # http://ia.media-imdb.com/images/M/MV5BMjEwNjQ5NDU4OF5BMl5BanBnXkFtZTYwOTI2NzA5._V1._SY317_CR1,0,214,317_.jpg
            # http://ia.media-imdb.com/images/M/MV5BMzE3NTMwOTk5OF5BMl5BanBnXkFtZTgwODcxNTE1NDE@._V1_UX182_CR0,0,182,268_AL_.jpg
            match = re.match(r"""(.+?\._V1).*\.jpg""", coverArtUrl)
            if match is None:
                return coverArtUrl
            else:
                return match.group(1) + "_SY768_.jpg"
        else:
            return ""


class PtpZeroImdbInfo:
    def __init__(self):
        pass

    def GetTitle(self):
        return ""

    def GetYear(self):
        return ""

    def GetMovieDescription(self):
        return ""

    def GetTags(self):
        return ""

    def GetCoverArtUrl(self):
        return ""
