"""
Setup script for Lost & Found CLI Tool

Install with: pip install -e .
"""

from setuptools import setup, find_packages

setup(
    name="lostfound-cli",
    version="1.0.0",
    description="CLI tool for the Lost & Found Image-Matching System",
    author="Lost & Found Team",
    python_requires=">=3.9",
    packages=find_packages(include=["cli", "cli.*"]),
    install_requires=[
        "click>=8.1.0",
        "httpx>=0.25.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "lf=cli.main:main",
            "lostfound=cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Utilities",
    ],
)
