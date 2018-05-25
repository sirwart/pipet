import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def get_requirements():
    with open('requirements.txt') as fp:
        return [x.strip() for x in fp.read().split('\n') if not x.startswith('#')]


setup(
    name="pipet",
    version="0.0.0",
    author="Eric Feng",
    author_email="erichfeng@gmail.com",
    description=("Open SQL"),
    license="Apache 2.0",
    install_requires=get_requirements(),
    keywords="SQL",
    url="https://pipet.io",
    packages=find_packages(),
    long_description=read("README.md"),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Development Status :: 1 - Planning",
        "Framework :: Flask",
        "Topic :: Utilities",
    )
)
