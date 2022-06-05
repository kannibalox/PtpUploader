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
        self.Raw = None


class Imdb:
    @staticmethod
    def GetInfo(logger, imdbId: str) -> ImdbInfo:
        logger.info("Getting IMDb info for IMDb id '%s'." % imdbId)

        # We don't care if this fails. It gives only extra information.
        imdbInfo = ImdbInfo()
        try:
            ia = IMDb()
            movie = ia.get_movie(imdbId.strip("t"))
            imdbInfo.Raw = movie
            if "title" in movie:
                imdbInfo.Title = movie["title"]
            if "year" in movie:
                imdbInfo.Year = str(movie["year"])
            if "rating" in movie:
                imdbInfo.ImdbRating = movie["rating"]
            if "votes" in movie:
                imdbInfo.ImdbVoteCount = movie["votes"]
            if "full-size cover url" in movie:
                imdbInfo.PosterUrl = movie["full-size cover url"]
            if "plot" in movie:
                imdbInfo.Plot = movie["plot"][0]
        except Exception:
            logger.exception(
                "Got exception while trying to get IMDb info by IMDb id '%s'." % imdbId
            )

        return imdbInfo
