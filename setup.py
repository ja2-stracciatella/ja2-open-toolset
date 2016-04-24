from setuptools import setup, find_packages
setup(name='ja2py',
      version='0.0.1',
      author='Stefan Lau',
      author_email='github@stefanlau.com',
      url='https://github.com/ja2-stracciatella/ja2-open-toolset',
      install_requires=[
            'fs>=0.5.2',
            'Pillow>=2.8.2'
      ],
      packages=find_packages())
