import os
import setuptools


def read(fname):
    return open(
        os.path.join(os.path.dirname(__file__), fname), encoding="utf-8"
        ).read()


setuptools.setup(
    name='dynflowparserng',
    version='0.0.0',
    setup_requires=['Jinja2', 'pytz'],
    scripts=[
        'dynflowparserng/bin/__init__.py',
        'dynflowparserng_export_tasks/bin/__init__.py'],
    entry_points={
        'console_scripts': [
            'dynflowparserng=dynflowparserng.bin:main',
            'dynflowparserng-export-tasks=dynflowparserng_export_tasks.bin:main',
            ],
        },
    packages=setuptools.find_packages(),
    package_data={
        'dynflowparserng.html.css': ['*'],
        'dynflowparserng.html.js': ['*'],
        'dynflowparserng.templates': ['*'],
    },
    license='GPLv3',
    author='Pablo Fernández Rodríguez',
    url='https://github.com/pafernanr/dynflowparserng',
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
    ],
    )
