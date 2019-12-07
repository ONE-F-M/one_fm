# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import re, ast

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in one_fm/__init__.py
_version_re = re.compile(r'__version__\s+=\s+(.*)')

with open('one_fm/__init__.py', 'rb') as f:
	version = str(ast.literal_eval(_version_re.search(
		f.read().decode('utf-8')).group(1)))

setup(
	name='one_fm',
	version=version,
	description='One Facility Management is a leader in the fields of commercial automation and integrated security management systems providing the latest in products and services in these fields',
	author='omar jaber',
	author_email='omar.ja93@gmail.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
