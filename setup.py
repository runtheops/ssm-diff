from setuptools import setup

setup(
    description = 'A tool to manage contents of AWS SSM Parameter Store',
    name = 'ssm-diff',
    version = '0.3',
    author = 'Sergey Motovilovets',
    author_email = 'motovilovets.sergey@gmail.com',
    license='MIT',
    url = 'https://github.com/runtheops/ssm-diff',
    download_url = 'https://github.com/runtheops/ssm-diff/archive/0.2.tar.gz',
    setup_requires=['setuptools-markdown'],
    long_description_markdown_filename='README.md',
    keywords = ['aws', 'ssm', 'parameter-store'],
    packages = ['states'],
    scripts=['ssm-diff'],
    install_requires=[
        'termcolor',
        'boto3',
        'dpath',
        'PyYAML'
    ]
)
