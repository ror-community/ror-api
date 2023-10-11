from setuptools import setup
import pathlib

here = pathlib.Path(__file__).parent.resolve()

setup(
    name='rorapi',
    version='0.0.1',
    long_description="ROR API",
    url='https://github.com/ror-community/ror-api',
    package_dir = {
            'rorapi': 'rorapi',
            'rorapi.v2.models': 'rorapi/v2'},
    packages=["rorapi", "rorapi.v2"],
    python_requires=">=3.7"
)