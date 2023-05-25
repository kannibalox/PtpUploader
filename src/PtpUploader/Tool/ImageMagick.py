import os
import logging
import subprocess

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import Settings, config

logger = logging.getLogger(__name__)


def convert_8bit(src_image):
    if not os.path.isfile(src_image):
        raise PtpUploaderException(
            "Can't read source image '%s' for PNG bit depth check." % src_image
        )
    proc = subprocess.run(["identify", src_image], capture_output=True, check=True)
    if b"16-bit" not in proc.stdout:
        return src_image
    logger.info("Converting PNG %r to 8-bit depth with ImageMagick.", src_image)
    dest_image = src_image + ".optimized.png"
    subprocess.run(
        [config.tools.imagemagick.path, src_image, "-depth", "8", dest_image]
    )
    os.remove(src_image)
    os.rename(dest_image, src_image)
    return src_image


def optimize_png(src_image):
    logger.info("Optimizing PNG '%s' with ImageMagick." % (src_image))

    if not os.path.isfile(src_image):
        raise PtpUploaderException(
            "Can't read source image '%s' for PNG optimization." % src_image
        )

    dest_image = src_image + ".optimized.png"
    if os.path.exists(dest_image):
        raise PtpUploaderException(
            "Can't optimize PNG because output file '%s' already exists." % dest_image
        )

    args = [
        config.tools.imagemagick.path,
        src_image,
        "-define",
        "png:exclude-chunk=gAMA",
        "-define",
        "png:exclude-chunk=cHRM",
        "-quality",
        "99",
        dest_image,
    ]
    errorCode = subprocess.call(args)
    if errorCode != 0:
        raise PtpUploaderException(
            "Process execution '%s' returned with error code '%s'." % (args, errorCode)
        )

    sourceSize = os.path.getsize(src_image)
    outputSize = os.path.getsize(dest_image)
    gainedBytes = sourceSize - outputSize
    if outputSize > 0 and gainedBytes > 0:
        os.remove(src_image)
        os.rename(dest_image, src_image)
        logger.info("Optimized PNG is %s bytes smaller." % (gainedBytes))
    else:
        os.remove(dest_image)
