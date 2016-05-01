from distutils.core import setup

setup(name='grabbids',
#      version='1.0',
#      description='Python Distribution Utilities',
#      author='Greg Ward',
#      author_email='gward@python.net',
#      url='https://www.python.org/sigs/distutils-sig/',
      packages=['grabbids'],
      package_data={'grabbids': ['test/data/*.{tsv,gz}', 'test/data/*/*.{tsv,gz}']},
     )
