from setuptools import setup, find_packages

__version__ = file('VERSION', 'r').read().strip('\r\n\t ')

setup(name='clusto-sgext',
      version=__version__,
      packages=find_packages(),
      install_requires=[
        'clusto',
        'decorator',
        'IPy',
        'boto',
        'kombu',
        'eventlet',
        'PyYAML',
      ],
      entry_points={
        'console_scripts': [
            'clusto-puppet-node2 = sgext.commands.puppet_node2:main',
            'clusto-barker-consumer = sgext.commands.barker_consumer:main',
            'clusto-ec2-report = sgext.commands.ec2_report:main',
            'clusto-aws-cleanup = sgext.commands.aws_cleanup:main',
            'clusto-elb = sgext.commands.elb:main',
            'clusto-apt = sgext.commands.apt:main',
        ]
      })
