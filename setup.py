#!/usr/bin/env python
from setuptools import setup, find_packages
import os

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

setup(
    name="PtpUploader",
    version="0.1",
    author="kannibalox",
    url="https://github.com/kannibalox/PTPAPI",
    install_requires=[
        "pyrocore",
        "sqlalchemy",
        "flask",
        "requests",
        "watchdog",
        "beautifulsoup4",
        "poster3"
    ],
    packages=find_packages('src'),
    package_dir={'':'src'},
    package_data={'': ['templates/*.html',
                       'static/*',
                       'static/*/*',
                       'static/*/*/*',
                       'static/*/*/*/*'
    ]
    },
    license='MIT',
    entry_points={
        'console_scripts': [
            'PtpUploader=PtpUploader.Main:Main',
            'ReleaseInfoMaker=PtpUploader.ReleaseInfoMaker:Main'
        ],
    }
)
