from setuptools import setup, find_packages

# usage of setup.py:
# https://stackoverflow.com/a/50194143
# Use "pip install -e ." in the root folder to install in editable state
# Use "pip uninstall package-name" to remove editable install
# package name can be read from pip list
setup(name='CityGen', version='0.1', packages=find_packages())
