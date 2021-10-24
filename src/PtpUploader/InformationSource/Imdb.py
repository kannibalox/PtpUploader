from imdb import IMDb


class ImdbInfo:
    def __init__(self):
        self.Title: str = ""
        self.Year: str = ""
        self.PosterUrl: str = ""
        self.Plot: str = ""
        self.IsSeries: bool = False
        self.ImdbRating: str = ""
        self.ImdbVoteCount: str = ""


class Imdb:
    @staticmethod
    def GetInfo(logger, imdbId: str) -> ImdbInfo:
        logger.info("Getting IMDb info for IMDb id '%s'." % imdbId)

        # We don't care if this fails. It gives only extra information.
        imdbInfo = ImdbInfo()
        try:
            ia = IMDb()
            movie = ia.get_movie(imdbId.strip("t"))
            imdbInfo.Title = movie["title"]
            imdbInfo.Year = str(movie["year"])
            imdbInfo.ImdbRating = movie["rating"]
            imdbInfo.ImdbVoteCount = movie["votes"]
            imdbInfo.PosterUrl = movie["full-size cover url"]
            imdbInfo.Plot = movie["plot"][0]
        except Exception:
            logger.exception(
                "Got exception while trying to get IMDb info by IMDb id '%s'." % imdbId
            )

        return imdbInfo
