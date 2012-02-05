from distutils.core import setup

setup(name='libmount',
      description='A wrapper around libmount, for reading and manipulating filesystem tables.',
      author='Oxford University Computing Services',
      author_email='infodev@oucs.ox.ac.uk',
      version='0.9',
      packages=['libmount'],
      license='BSD',
      url='https://github.com/oucs/python-libmount',
      long_description=open('README.rst').read(),
      classifiers=['Development Status :: 4 - Beta',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: POSIX',
                   'Programming Language :: Python',
                   'Topic :: System :: Filesystems',
                   'Topic :: System :: Systems Administration'],
      keywords=['University of Oxford', 'libmount', 'filesystem table', 'fstab'],
)