from setuptools import setup, find_packages
import pathlib

setup(
    name='rorapi',
    package_dir = {"": "rorapi"}
    version='0.0.1',
    long_description="ROR API",
    url='https://github.com/ror-community/ror-api',
    packages=find_packages(),
    python_requires=">=3.7"
)