"""
Setup script for ozone_hotspot.
"""

from setuptools import setup, find_packages
from pathlib import Path

readme = Path(__file__).parent / "README.md"
long_desc = readme.read_text(encoding="utf-8") if readme.exists() else ""

setup(
    name="ozone_hotspot",
    version="1.2.1",
    description="Mobile-measurement Ozone Hotspot AT Diagnosis",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author="Hyunjun Shin, Hyunjung Seo, Cheonwoong Kang",
    url="",
    license="MIT",
    packages=find_packages(where="ozone_hotspot_folder_only"),
    python_requires=">3.9",
    install_requires=[
        "pandas>=1.5",
        "numpy>=1.23",
        "scikit-learn>=1.2",
        "scipy>=1.10",
        "matplotlib>=3.6",
        "shap>=0.42",
    ],
)
