import json
import re
import time
import traceback

from PtpUploader.MyGlobals import MyGlobals
from PtpUploader.PtpMovieSearchResult import PtpMovieSearchResult
from PtpUploader.PtpUploaderException import *
from PtpUploader.Settings import Settings


class Ptp:
    AntiCsrfToken: str

    @staticmethod
    def __LoginInternal():
        if not Settings.PtpUserName:
            raise PtpUploaderInvalidLoginException(
                "Couldn't log in to PTP. Your user name is not specified."
            )

        if not Settings.PtpPassword:
            raise PtpUploaderInvalidLoginException(
                "Couldn't log in to PTP. Your password is not specified."
            )

        # Get the pass key from the announce URL.
        passKey = re.match(
            r"https?://please\.passthepopcorn\.me:?\d*/(.+)/announce",
            Settings.PtpAnnounceUrl,
        )
        if passKey is None:
            raise PtpUploaderInvalidLoginException(
                "Couldn't log in to PTP. Pass key not found in the announce URL."
            )
        passKey = passKey.group(1)

        MyGlobals.Logger.info("Logging in to PTP.")

        if "passthepopcorn.me" in MyGlobals.session.cookies.list_domains():
            response = MyGlobals.session.get("https://passthepopcorn.me/upload.php")
            Ptp.CheckIfLoggedInFromResponse(response, response.text)
            Ptp.AntiCsrfToken = re.search(
                r'data-AntiCsrfToken="(.*)"', response.text
            ).group(1)
        else:
            postData = {
                "username": Settings.PtpUserName,
                "password": Settings.PtpPassword,
                "passkey": passKey,
                "keeplogged": "1",
            }
            response = MyGlobals.session.post(
                "https://passthepopcorn.me/ajax.php?action=login", data=postData
            ).text

            jsonLoad = None
            try:
                jsonLoad = json.loads(response)
            except (Exception, ValueError) as e:
                raise PtpUploaderInvalidLoginException(
                    "Got exception while loading JSON login response from PTP. Response: '%s'."
                    % response
                ) from e

            if jsonLoad is None:
                raise PtpUploaderInvalidLoginException(
                    "Got bad JSON response from PTP while trying to log in. Response: '%s'."
                    % response
                )

            if jsonLoad["Result"] != "Ok":
                raise PtpUploaderInvalidLoginException(
                    "Failed to login to PTP. Probably due to the bad user name, password or pass key."
                )

            Ptp.AntiCsrfToken = jsonLoad["AntiCsrfToken"]
            MyGlobals.SaveCookies()

    @staticmethod
    def Login():
        maximumTries = 1

        while True:
            try:
                Ptp.__LoginInternal()
                return
            except PtpUploaderInvalidLoginException:
                raise
            except Exception:
                if maximumTries > 1:
                    maximumTries -= 1
                    time.sleep(30)  # Wait 30 seconds and retry.
                else:
                    raise

    @staticmethod
    def __CheckIfLoggedInFromResponseLogResponse(result, responseBody):
        MyGlobals.Logger.info("MSG: %s" % result.reason)
        MyGlobals.Logger.info("CODE: %s" % result.status_code)
        MyGlobals.Logger.info("URL: %s" % result.url)
        MyGlobals.Logger.info("HEADERS: %s" % result.headers)
        MyGlobals.Logger.info("STACK: %s" % traceback.format_stack())
        MyGlobals.Logger.info("RESPONSE BODY: %s" % responseBody)

    @staticmethod
    def CheckIfLoggedInFromResponse(result, responseBody):
        if responseBody.find("""<a href="login.php?act=recover">""") != -1:
            Ptp.__CheckIfLoggedInFromResponseLogResponse(result, responseBody)
            raise PtpUploaderException(
                "Looks like you are not logged in to PTP. Probably due to the bad user name or password."
            )

    # PTP expects 7 character long IMDb IDs.
    # E.g.: it can't find movie with IMDb ID 59675, only with 0059675. (IMDb redirects to the latter.)
    @staticmethod
    def NormalizeImdbIdForPtp(imdbId):
        return imdbId.rjust(7, "0")

    # ptpId must be a valid id
    # returns with PtpMovieSearchResult
    @staticmethod
    def GetMoviePageOnPtp(logger, ptpId):
        logger.info("Getting movie page for PTP id '%s'." % ptpId)

        result = MyGlobals.session.get(
            "https://passthepopcorn.me/torrents.php?id=%s&json=1" % ptpId
        )
        response = result.text
        Ptp.CheckIfLoggedInFromResponse(result, response)

        if response.find("<h2>Error 404</h2>") != -1:
            raise PtpUploaderException("Movie with PTP id '%s' doesn't exists." % ptpId)

        return PtpMovieSearchResult(ptpId, response)

    # imdbId: IMDb id. Eg.: 0137363 for http://www.imdb.com/title/tt0137363/
    # returns with PtpMovieSearchResult
    @staticmethod
    def GetMoviePageOnPtpByImdbId(logger, imdbId):
        logger.info("Trying to find movie with IMDb id '%s' on PTP." % imdbId)

        result = MyGlobals.session.get(
            "https://passthepopcorn.me/torrents.php?imdb=%s&json=1"
            % Ptp.NormalizeImdbIdForPtp(imdbId)
        )
        response = result.text
        Ptp.CheckIfLoggedInFromResponse(result, response)

        # If there is a movie: result.url = https://passthepopcorn.me/torrents.php?id=28577
        # If there is no movie: result.url = https://passthepopcorn.me/torrents.php?imdb=1535492
        match = re.match(r".*?passthepopcorn\.me/torrents\.php\?id=(\d+)", result.url)
        if match is not None:
            ptpId = match.group(1)
            url = result.url
            url = url.replace("&json=1", "")
            logger.info(
                "Movie with IMDb id '%s' exists on PTP at '%s'." % (imdbId, url)
            )
            return PtpMovieSearchResult(ptpId, response)
        elif (
            response.find("<h2>Error 404</h2>") != -1
        ):  # For some deleted movies PTP return with this error.
            logger.info(
                "Movie with IMDb id '%s' doesn't exists on PTP. (Got error 404.)"
                % imdbId
            )
            return PtpMovieSearchResult(ptpId="", moviePageJsonText=None)
        elif response.find("<h2>Your search did not match anything.</h2>") != -1:
            logger.info("Movie with IMDb id '%s' doesn't exists on PTP." % imdbId)
            return PtpMovieSearchResult(ptpId="", moviePageJsonText=None)
        else:  # Multiple movies with the same IMDb id.
            raise PtpUploaderException(
                "There are multiple movies on PTP with IMDb id '%s'." % imdbId
            )

    @staticmethod
    def __UploadMovieGetParamsCommon(releaseInfo, releaseDescription):
        paramList = {
            "submit": "true",
            "type": releaseInfo.Type,
            "remaster_year": releaseInfo.RemasterYear,
            "remaster_title": releaseInfo.RemasterTitle,
            "codec": "Other",  # Sending the codec as custom.
            "other_codec": releaseInfo.Codec,
            "container": "Other",  # Sending the container as custom.
            "other_container": releaseInfo.Container,
            "resolution": releaseInfo.ResolutionType,
            "other_resolution": releaseInfo.Resolution,
            "source": "Other",  # Sending the source as custom.
            "other_source": releaseInfo.Source,
            "release_desc": releaseDescription,
            "nfo_text": releaseInfo.Nfo,
            "AntiCsrfToken": Ptp.AntiCsrfToken,
        }

        # personal rip only needed if it is specified
        if releaseInfo.IsPersonalRip():
            paramList.update({"internalrip": "on"})

        # scene only needed if it is specified
        if releaseInfo.IsSceneRelease():
            paramList.update({"scene": "on"})
        # other category is only needed if it is specified
        if releaseInfo.IsSpecialRelease():
            paramList.update({"special": "on"})
        # remaster is only needed if it is specified
        if len(releaseInfo.RemasterYear) > 0 or len(releaseInfo.RemasterTitle) > 0:
            paramList.update({"remaster": "on"})
        # Trumpable for no English subtitles is only needed if it is specified.
        for t_id in releaseInfo.Trumpable.split(","):
            if t_id in ["14", "4"]:
                paramList.update({"trumpable[]": t_id})
        subtitles = releaseInfo.GetSubtitles()
        for subtitle in subtitles:
            paramList.update({"subtitles[]": subtitle})
        return paramList

    @staticmethod
    def __UploadMovieGetParamsForAddFormat(ptpId):
        groupId = ("groupid", ptpId)
        return [groupId]

    @staticmethod
    def __UploadMovieGetParamsForNewMovie(releaseInfo):
        params = {
            "title": releaseInfo.Title,
            "year": releaseInfo.Year,
            "image": releaseInfo.CoverArtUrl,
            "tags": releaseInfo.Tags,
            "album_desc": releaseInfo.MovieDescription,
            "trailer": releaseInfo.YouTubeId,
        }

        # Add the IMDb ID.
        if releaseInfo.ImdbId == "0":
            params.update({"imdb": "0"})
        else:
            params.update({"imdb": Ptp.NormalizeImdbIdForPtp(releaseInfo.ImdbId)})
        # Add the directors.
        # These needs to be added in order because of the "importance" field follows them.
        for d in releaseInfo.GetDirectors():
            params.update({"artist[]": d})
            params.update({"importance[]": "1"})

        return params

    # Returns with the auth key.
    @staticmethod
    def UploadMovie(logger, releaseInfo, torrentPath, releaseDescription):
        url = ""
        paramList = Ptp.__UploadMovieGetParamsCommon(releaseInfo, releaseDescription)

        # We always use HTTPS for uploading because if "Force HTTPS" is enabled in the profile then the HTTP upload is not working.
        if releaseInfo.PtpId:
            logger.info(
                "Uploading torrent '%s' to PTP as a new format for 'https://passthepopcorn.me/torrents.php?id=%s'."
                % (torrentPath, releaseInfo.PtpId)
            )
            url = "https://passthepopcorn.me/upload.php?groupid=%s" % releaseInfo.PtpId
            paramList.update(Ptp.__UploadMovieGetParamsForAddFormat(releaseInfo.PtpId))
        else:
            logger.info("Uploading torrent '%s' to PTP as a new movie." % torrentPath)
            url = "https://passthepopcorn.me/upload.php"
            paramList.update(Ptp.__UploadMovieGetParamsForNewMovie(releaseInfo))

        # Add the torrent file, passing a fake string for the filename, since it's not necessary anyway
        with open(torrentPath, "rb") as torrentHandle:
            files = {
                "file_input": (
                    "placeholder.torrent",
                    torrentHandle,
                    "application/x-bittorent",
                )
            }
            result = MyGlobals.session.post(url, data=paramList, files=files)
        response = result.text
        Ptp.CheckIfLoggedInFromResponse(result, response)

        # If the repsonse contains our announce url then we are on the upload page and the upload wasn't successful.
        if response.find(Settings.PtpAnnounceUrl) != -1:
            # Get the error message.
            # <div class="alert alert--error text--center">No torrent file uploaded, or file is empty.</div>
            errorMessage = ""
            match = re.search(
                r"""<div class="alert alert--error.*?>(.+?)</div>""", response
            )
            if match is not None:
                errorMessage = match.group(1)

            raise PtpUploaderException(
                "Upload to PTP failed: '%s' (%s). (We are still on the upload page.)"
                % (errorMessage, result.status_code)
            )

        # URL format in case of successful upload: https://passthepopcorn.me/torrents.php?id=9329&torrentid=91868
        match = re.match(
            r".*?passthepopcorn\.me/torrents\.php\?id=(\d+)&torrentid=(\d+)", result.url
        )
        if match is None:
            raise PtpUploaderException(
                "Upload to PTP failed: result URL '%s' (%s) is not the expected one."
                % (result.url, result.status_code)
            )

        ptpId = match.group(1)
        releaseInfo.PtpTorrentId = match.group(2)

        if not releaseInfo.PtpId:
            releaseInfo.PtpId = ptpId

    @staticmethod
    def SendPrivateMessage(userId, subject, message):
        MyGlobals.Logger.info("Sending private message on PTP.")

        # We need to load the send message page for the authentication key.
        result = MyGlobals.session.get(
            "https://passthepopcorn.me/inbox.php?action=compose&to=%s" % userId
        )
        response = result.text
        Ptp.CheckIfLoggedInFromResponse(result, response)

        matches = re.search(
            r"""<input type="hidden" name="auth" value="(.+)" />""", response
        )
        if not matches:
            MyGlobals.Logger.info("Authorization key couldn't be found.")
            return

        auth = matches.group(1)

        # Send the message.
        # We always use HTTPS for sending message because if "Force HTTPS" is enabled in the profile then the HTTP message sending is not working.

        postData = {
            "toid": userId,
            "subject": subject,
            "body": message,
            "auth": auth,
            "action": "takecompose",
            "AntiCsrfToken": Ptp.AntiCsrfToken,
        }

        result = MyGlobals.session.post("https://passthepopcorn.me/inbox.php", postData)
        response = result.text
        Ptp.CheckIfLoggedInFromResponse(result, response)
