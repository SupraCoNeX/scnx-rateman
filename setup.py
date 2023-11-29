from setuptools import setup, Extension
from Cython.Build import cythonize


setup(
    name="rateman",
    ext_modules=cythonize(
        [
            Extension("rateman.c_parsing", ["rateman/c_parsing.pyx"])
        ],
        language_level=3
    )
)
