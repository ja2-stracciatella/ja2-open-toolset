from setuptools import setup, find_packages
setup(name='ja2py',
      version='0.0.1',
      author='Stefan Lau',
      author_email='github@stefanlau.com',
      url='https://github.com/ja2-stracciatella/ja2-open-toolset',
      install_requires=[
            'fs>=2.0.0,<3',
            'Pillow>=4.1.0,<5'
      ],
      packages=find_packages())
