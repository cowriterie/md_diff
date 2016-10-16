from setuptools import setup, find_packages
import os

datadir = "src/templates"
datafiles = [(d, [os.path.join(d,f) for f in files])
    for d, folders, files in os.walk(datadir)]

setup(
    name='md-diff',
    version='0.1.0',
    author='Chris Gibson',
    author_email='cgibson@mrvoxel.com',
    license='MIT',
    packages = find_packages(),
    data_files=datafiles,
    install_requires=[
        'Jinja2>=2.8',
        'markdown2==2.3.1',
        'MarkupSafe==0.23',
    ],
)