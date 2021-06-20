#!/usr/bin/env python
"""
Installation script:

To release a new version to PyPi:
- Ensure the version is correctly set in xently.__init__.py
- Run: make release
"""
import os
import re
import shutil
import sys

from setuptools import find_packages, setup

from xently import get_next_version

PROJECT_DIR = os.path.dirname(__file__)

sys.path.append(os.path.join(PROJECT_DIR, 'src'))


def get_version(package):
    """
    Return package version as listed in `__version__` in `init.py`.
    """
    with open(os.path.join(package, "__init__.py"), "rb") as init_py:
        src = init_py.read().decode("utf-8")
        return re.search("__version__ = ['\"]([^'\"]+)['\"]", src).group(1), src


def update_version(package):
    old_version, src = get_version(package)
    new_version = get_next_version(old_version=old_version)
    new_file_content = re.sub("__version__ = ['\"]([^'\"]+)['\"]", f'__version__ = "{new_version}"', src)
    with open(os.path.join(package, "__init__.py"), "wb") as init_py:
        init_py.write(bytes(new_file_content, encoding="utf-8"))


version = get_version("xently")[0]

with open(os.path.join(os.path.dirname(__file__), "README.md")) as readme:
    long_description = readme.read()

if sys.argv[-1] == "publish":
    if os.system("pip freeze | grep twine"):
        print("twine not installed.\nUse `pip install twine`.\nExiting.")
        sys.exit()
    os.system("python setup.py sdist bdist_wheel")
    if os.system("twine check dist/*"):
        print("twine check failed. Packages might be outdated.")
        print("Try using `pip install -U twine wheel`.\nExiting.")
        sys.exit()
    if re.match("^-([t]|-test)$", sys.argv[-2]):
        # uploads test package
        os.system("twine upload --repository testpypi dist/*")
    else:
        # uploads production package
        os.system("twine upload dist/*")
    print("You probably want to also tag the version now:")
    print(" git tag -a {0} -m 'version {0}'".format(version))
    print(" git push --tags")
    update_version("xently")
    shutil.rmtree("dist")
    shutil.rmtree("build")
    shutil.rmtree("django_xently.egg-info")
    sys.exit()

setup(
    name='django-xently',
    url='https://github.com/ajharry69/django-xently',
    version=version,
    author="Orinda Harrison",
    author_email="oharry0535@gmail.com",
    description="No description",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license='BSD',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=[
        "django",
        "djangorestframework",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development",
        "Topic :: Internet :: WWW/HTTP",
    ]
)
