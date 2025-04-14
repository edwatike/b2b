from setuptools import setup, find_packages

setup(
    name="parser",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        "pathlib>=1.0.1"
    ],
    python_requires=">=3.8",
) 