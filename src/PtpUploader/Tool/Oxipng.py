import os
import logging
import subprocess

from PtpUploader.PtpUploaderException import PtpUploaderException
from PtpUploader.Settings import config

logger = logging.getLogger(__name__)


def optimize_png(sourceImagePath: os.PathLike):
    logger.info("Optimizing PNG '%s' with oxiping." % (sourceImagePath))
    if not os.path.isfile(sourceImagePath):
        raise PtpUploaderException(
            "Can't read source image '%s' for PNG optimization." % sourceImagePath
        )
    args = [config.tools.oxipng.path, "-o", "3", "--strip", "all", sourceImagePath]
    proc = subprocess.run(args, capture_output=True, encoding="utf-8")
    if proc.returncode != 0:
        raise PtpUploaderException(
            "Process execution '%s' returned with error code '%s'."
            % (args, proc.returncode)
        )
    logger.info(proc.stderr)
