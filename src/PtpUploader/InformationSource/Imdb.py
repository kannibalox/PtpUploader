class ImdbInfo:
    def __init__(self):
        self.Title = ""
        self.Year = ""
        self.PosterUrl = ""
        self.Plot = ""
        self.IsSeries = False
        self.ImdbRating = ""
        self.ImdbVoteCount = ""

class Imdb:
    @staticmethod
    def __GetInfoInternal(imdbId):
        imdbInfo = ImdbInfo()
        soup = bs4(requests.get('https://www.imdb.com/title/tt{}/'.format(imdbId)).text, "html.parser")

        if "TV Episode" in soup.find('title').text or "TV Series" in soup.find('title').text:
            imdbInfo.IsSeries = True
        else:
            imdbInfo.IsSeries = False
        if imdbInfo.IsSeries:
            title_str = soup.find(class_='title_wrapper').find('h1').text
            match = re.search(r'(.*) \((\d+)\)', title_str)
            imdbInfo.Title = match.group(1)
            imdbInfo.Year = match.group(2)
        else:
            imdbInfo.Title = soup.find(class_='title_wrapper').find('h1').find(text=True)
            imdbInfo.Year = soup.find(class_='title_wrapper').find('h1').find('span').text.strip('()')
        imdbInfo.ImdbRating = soup.find(itemprop="ratingValue").text
        imdbInfo.ImdbVoteCount = soup.find(itemprop="ratingCount").text.replace(',', '')
        imdbInfo.PosterUrl = re.sub( r"\._V1_.*\.jpg", "._V1_SY768_.jpg", soup.find(class_="poster").find('img')['src'])
        imdbInfo.Plot = ''
        if soup.find(id="titleStoryLine") is not None:
            imdbInfo.Plot = soup.find(id="titleStoryLine").find('div').text.strip()
        else:
            plot_soup = bs4(requests("https://www.imdb.com/title/tt{}/plotsummary".format(imdbId)).text)
            imdbInfo.Plot = plot_soup.find(id="plot-summaries-content").find('li').text
        return imdbInfo
        
    @staticmethod
    def GetInfo(logger, imdbId):
        logger.info( "Getting IMDb info for IMDb id '%s'." % imdbId );
        
        # We don't care if this fails. It gives only extra information.
        try:
            imdbInfo = Imdb.__GetInfoInternal( imdbId )
            return imdbInfo
        except Exception:
            logger.exception( "Got exception while trying to get IMDb info by IMDb id '%s'." % imdbId );

        return ImdbInfo()
