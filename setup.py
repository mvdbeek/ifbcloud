try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

requirements = ['requests', 'configargparse', 'lxml']

ENTRY_POINTS = '''
        [console_scripts]
        ifbcloud=ifbcloud.ifbcloud:main
'''

readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')

setup(
    name='ifbcloud',
    version='0.1.2',
    packages=['ifbcloud'],
    install_requires=requirements,
    long_description=readme + '\n\n' + history,
    entry_points=ENTRY_POINTS,
    keywords='IFB',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'Operating System :: POSIX',
        'Topic :: Software Development',
        'Topic :: Software Development :: Testing',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    url='https://github.com/mvdbeek/ifbcloud',
    license='MIT',
    author='Marius van den Beek',
    author_email='m.vandenbeek@gmail.com',
    description='Commandline utility to start and stop instances on the french IFB cloud'
)
