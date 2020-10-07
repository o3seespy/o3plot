from setuptools import setup, find_packages

about = {}
with open("o3plot/__about__.py") as fp:
    exec(fp.read(), about)

with open('README.rst') as readme_file:
    readme = readme_file.read()

# with open('HISTORY.rst') as history_file:
#     history = history_file.read()

setup(name='o3plot',
      version=about['__version__'],
      description='A plotting library for o3seespy',
      long_description=readme,  # + '\n\n' + history,
      url='',
      author=about['__author__'],
      author_email='mmi46@uclive.ac.nz',
      license=about['__license__'],
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Science/Research',
          'Topic :: Scientific/Engineering',
          'Programming Language :: Python :: 3',
      ],
      packages=find_packages(exclude=['contrib', 'docs', 'tests', 'examples',
                                      ]),
      install_requires=[
        'openseespy',
        'o3seespy',
        'numpy',
        'PyQt5',
        'pyqtgraph',
        'bwplot>=0.2.24',
      ],
      # List additional groups of dependencies here (e.g. development
      # dependencies). You can install these using the following syntax,
      # for example:
      # $ pip install -e .[dev,test]
      extras_require={
          'test': ['pytest'],
      },
      python_requires='>=3',
      package_data={'o3plot': ['o3plot/models_data.dat']},
      zip_safe=False)


# From python packaging guides
# versioning is a 3-part MAJOR.MINOR.MAINTENANCE numbering scheme,
# where the project author increments:

# MAJOR version when they make incompatible API changes,
# MINOR version when they add functionality in a backwards-compatible manner, and
# MAINTENANCE version when they make backwards-compatible bug fixes.