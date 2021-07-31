from ..MyGlobals import MyGlobals
from ..PtpUploaderException import PtpUploaderException
from ..Settings import Settings

import os
import re
import uuid


class Picload:
    @staticmethod
    def __DownloadImage(logger, imageUrl):
        # Get image extension from the URL.
        fileName, extension = os.path.splitext(imageUrl)
        extension = extension.lower()
        if extension != ".jpg" and extension != ".jpeg" and extension != ".png":
            raise PtpUploaderException("Invalid image file extension.")

        # Download the image.
        result = MyGlobals.session.get(imageUrl)
        result.raise_for_status()
        response = result.content

        # Save the image with a random name.
        imagePath = os.path.join(
            Settings.GetTemporaryPath(), str(uuid.uuid1()) + extension
        )
        f = open(imagePath, "wb")
        f.write(response)
        f.close()

        return imagePath

    @staticmethod
    def __UploadImage(logger, imagePath):
        response = None

        with open(imagePath, "rb") as file:
            fileName, extension = os.path.splitext(imagePath)
            fileName = "up" + extension.lower()  # Don't keep the original file name.
            files = {"images[]": (fileName, file)}
            postData = {"type": "local"}
            response = MyGlobals.session.post(
                "http://upload.picload.org/upload.html", data=postData, files=files
            )

        # Throw exception in case of bad requests (4xx or 5xx).
        response.raise_for_status()

        responseText = response.text

        ## <input id="wrpowllImage" type="text" onclick="this.focus();this.select();" size="50" value="http://picload.org/image/wrpowll/sb.jpg" /><br />
        matches = re.search(r'value="(https?://picload.org/image/.+?)"', responseText)
        if matches is None:
            raise PtpUploaderException("Picload direct image link not found.")

        imageUrl = matches.group(1)
        return imageUrl

    @staticmethod
    def Upload(logger, imagePath=None, imageUrl=None):
        if imagePath is not None:
            return Picload.__UploadImage(logger, imagePath)

        # Rehost the image from url.
        try:
            imagePath = Picload.__DownloadImage(logger, imageUrl)
            return Picload.__UploadImage(logger, imagePath)
        finally:
            if (imagePath is not None) and os.path.isfile(imagePath):
                os.remove(imagePath)
