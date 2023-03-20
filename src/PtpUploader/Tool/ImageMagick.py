import os
import subprocess

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings


class ImageMagick:
    # Compresses PNG more if possible.
    # The compression is lossless.
    @staticmethod
    def OptimizePng(logger, sourceImagePath):
        logger.info("Optimizing PNG '%s' with ImageMagick." % (sourceImagePath))

        if not os.path.isfile(sourceImagePath):
            raise PtpUploaderException(
                "Can't read source image '%s' for PNG optimization." % sourceImagePath
            )

        outputImagePath = sourceImagePath + ".optimized.png"
        if os.path.exists(outputImagePath):
            raise PtpUploaderException(
                "Can't optimize PNG because output file '%s' already exists."
                % outputImagePath
            )

        args = [
            Settings.ImageMagickConvertPath,
            sourceImagePath,
            "-define",
            "png:exclude-chunk=gAMA",
            "-define",
            "png:exclude-chunk=cHRM",
            "-quality",
            "99",
            outputImagePath,
        ]
        errorCode = subprocess.call(args)
        if errorCode != 0:
            raise PtpUploaderException(
                "Process execution '%s' returned with error code '%s'."
                % (args, errorCode)
            )

        sourceSize = os.path.getsize(sourceImagePath)
        outputSize = os.path.getsize(outputImagePath)
        gainedBytes = sourceSize - outputSize
        if outputSize > 0 and gainedBytes > 0:
            os.remove(sourceImagePath)
            os.rename(outputImagePath, sourceImagePath)
            logger.info("Optimized PNG is %s bytes smaller." % (gainedBytes))
        else:
            os.remove(outputImagePath)
