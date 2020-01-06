# -*- coding: utf-8 -*-

# Learn more: https://github.com/kennethreitz/setup.py

from setuptools import setup, find_packages


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    install_requires=required,
    name='sched_presentation_tool',
    version='0.1.0',
    description='This module downloads files uploaded to a session in sched',
    long_description=readme,
    author='Kyle Kirkby',
    author_email='kyle.kirkby@linaro.org',
    url='https://github.com/linaro-marketing/SchedPresentationTool',
    license=license,
    packages=find_packages(exclude=('tests', 'docs'))
)
