from setuptools import setup, find_packages

setup(
    name='md-diff',
    version='0.1.0',
    author='Chris Gibson',
    author_email='cgibson@mrvoxel.com',
    license='MIT',
    py_modules=['mddiff.mddiff'],
    data_files=[
        ('templates', ['mddiff/templates/*']),
    ],
    install_requires=[
        'Jinja2>=2.8',
        'markdown2==2.3.1',
        'MarkupSafe==0.23',
    ],
)