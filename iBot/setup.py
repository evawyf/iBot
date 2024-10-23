from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='iBot',
    version='0.1.0',
    author='evawyf',
    author_email='evawyf1@example.com',
    description='A trading bot using Interactive Brokers API',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/evawyf/iBot',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        'ibapi>=9.81.1,<10.0',
        # Add other dependencies here, for example:
        # 'pandas>=1.0.0',
        # 'numpy>=1.18.0',
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-cov>=2.0',
            'flake8>=3.8',
        ],
    },
    entry_points={
        'console_scripts': [
            'ibot=src.main:main',
        ],
    },
)
