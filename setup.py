#!/usr/bin/env python
import os

from setuptools import setup, find_packages


def package_files(directory):
    paths = []
    for (path, _, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join("..", path, filename))
    return paths


setup(
    name="PtpUploader",
    version="0.1",
    author="kannibalox",
    url="https://github.com/kannibalox/PtpUploader",
    install_requires=[
        "pyrobase @ git+https://github.com/kannibalox/pyrobase@py3",
        "pyrocore @ git+https://github.com/kannibalox/pyrocore@py3",
        "sqlalchemy",
        "werkzeug",
        "flask",
        "requests",
        "watchdog",
        "beautifulsoup4",
    ],
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={
        "": [
            "templates/*.html",
            "static/*",
            "static/*/*",
            "static/*/*/*",
            "static/*/*/*/*",
        ]
    },
    license="MIT",
    entry_points={
        "console_scripts": [
            "PtpUploader=PtpUploader.Main:Main",
            "ReleaseInfoMaker=PtpUploader.ReleaseInfoMaker:Main",
        ],
    },
)
