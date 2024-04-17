from setuptools import setup, Extension
from Cython.Build import cythonize


setup(
    name="rateman",
    ext_modules=cythonize(
        [
            Extension("rateman.c_parsing", ["rateman/c_parsing.pyx"]),
            Extension("rateman.c_sta_rate_stats", ["rateman/c_sta_rate_stats.pyx"]),
        ],
        language_level=3
    )
)
