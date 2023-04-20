from setuptools import setup

setup(
    name='spandimentotool',
    version='0.1',
    packages=['spandimentotool'],
    include_package_data=True,
    url='',
    license='',
    author='Francesco Granella',
    author_email='',
    description='',
    install_requires=[
        'matplotlib', 'pandas', 'numpy', 'xarray', 'tabulate', 'pycaret', 'geopandas', 'pyarrow'
    ],
    entry_points = {
        'console_scripts': ['spandimento=spandimentotool.CLI:main', 'prova=spandimentotool.CLI:prova'],
    })