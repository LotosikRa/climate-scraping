# Automatically created by: shub deploy

from setuptools import setup, find_packages


PROJECT_DIRECTORY_NAME = 'scrapy_climate'


setup(
    name='project',
    version='0.1',
    packages=find_packages(),
    data_files=[('', ['client-secret.json', 'config.json'])],
    entry_points={'scrapy': ['settings = {}.settings'.format(PROJECT_DIRECTORY_NAME)]},
)
