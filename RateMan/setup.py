# Copyright SupraCoNeX
#     https://www.supraconex.org
#
# Usage:
# ToDo:- Docu: python setup.py build_sphinx -E
# ToDo:- Test: python setup.py test

from setuptools import setup
from sphinx.setup_command import BuildDoc
from os import path

cmdclass = {"build_sphinx": BuildDoc}

name = "rateman"
author = "SupraCoNeX"
version = "0.1"  # __version__
release = ".".join(version.split(".")[:2])

# read the contents of the README file
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name=name,
    version="0.1",
    author=author,
    author_email="supraconex@supraconex.org",
    description="Rate Monitor and Controlling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/supraconex.org",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[
        "sphinx",
        "sphinx_rtd_theme",
        "matplotlib",
        "tornado",
        "numpy",
        "scipy",
        "six",
        "pycodestyle",
        "pandas",
        "pint==0.9",
        "dask",
        "paramiko",
        "dash",
    ],
)
