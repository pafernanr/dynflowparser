import setuptools


setuptools.setup(
    name='dynflowparser',
    version='0.0.0',
    python_requires='>3.8',
    setup_requires=['Jinja2', 'pytz', 'packaging;python_version>="3.8"'],
    long_description="Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps.",
    author='Pablo Fernández Rodríguez',
    url='https://github.com/pafernanr/dynflowparser',
    license='GPLv3',
    scripts=['bin/dynflowparser', 'bin/dynflowparser-export-tasks'],
    packages=setuptools.find_packages(),
    package_data={
        'dynflowparser.html.css': ['*'],
        'dynflowparser.html.js': ['*'],
        'dynflowparser.templates': ['*'],
    },
    )
