"""
Setup script for ozone_hotspot.

Allows:
    pip install -e .          # editable install
    pip install .              # regular install
    python setup.py sdist      # build source distribution
"""
from setuptools import setup, find_packages
from pathlib import Path

readme = Path(__file__).parent / "README.md"
long_desc = readme.read_text(encoding="utf-8") if readme.exists() else ""

setup(
    name="ozone_hotspot",
    version="1.2.1",
    description="Mobile-measurement Ozone Hotspot AI Diagnosis",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author="Hyunjun Shin, Hyunjung Seo, Cheonwoong Kang",
    url="",
    license="MIT",
    packages=find_packages()where="ozone_hotspot_folder_only",
    python_requires=">=3.9",
    install_requires=[
        "pandas>=1.5",
        "numpy>=1.23",
        "scikit-learn>=1.2",
        "matplotlib>=3.6",
    ],
    extras_require={
        "shap": ["shap>=0.42"],
    },
    entry_points={
        "console_scripts": [
            "ozone-hotspot=ozone_hotspot.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
    ],
)
