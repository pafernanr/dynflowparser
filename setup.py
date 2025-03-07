import os
import setuptools


def read(fname):
    return open(
        os.path.join(os.path.dirname(__file__), fname), encoding="utf-8"
        ).read()


setuptools.setup(
    name='dynflowparser',
    version='0.0.0',
    setup_requires=['Jinja2', 'pytz', 'packaging;python_version>="3.9"'],
    scripts=['bin/dynflowparser', 'bin/dynflowparser-export-tasks'],
    packages=setuptools.find_packages(),
    package_data={
        'dynflowparser.html.css': ['*'],
        'dynflowparser.html.js': ['*'],
        'dynflowparser.templates': ['*'],
    },
    license='GPLv3',
    author='Pablo Fernández Rodríguez',
    url='https://github.com/pafernanr/dynflowparser',
    keywords='theforeman dynflow',
    description="""
        Get sosreport dynflow files and generates user friendly html pages for
        tasks, plans, actions and steps.""",
    long_description_content_type='text/markdown',
    long_description=read("README.md"),
    classifiers=[
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
    ],
    )
