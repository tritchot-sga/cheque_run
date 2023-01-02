from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in cheque_run/__init__.py
from cheque_run import __version__ as version

setup(
	name="cheque_run",
	version=version,
	description="Payables Utilities for ERP",
	author="SGA Tech Solutions",
	author_email="farabi.hussain@sgatechsolutions.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
