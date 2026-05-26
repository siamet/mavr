"""Setup configuration for the mavr package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split("\n")
    requirements = [r.strip() for r in requirements if r.strip() and not r.startswith("#")]

dev_requirements_file = Path(__file__).parent / "requirements-dev.txt"
dev_requirements = []
if dev_requirements_file.exists():
    dev_requirements = dev_requirements_file.read_text(encoding="utf-8").strip().split("\n")
    dev_requirements = [r.strip() for r in dev_requirements if r.strip() and not r.startswith("#") and not r.startswith("-r")]

setup(
    name="mavr",
    version="0.1.0",
    author="siamet",
    author_email="siamet@protonmail.com",
    description="Mavr: multi-agent AI system for automated code review and refactoring",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siamet/mavr",
    packages=find_packages(exclude=["tests", "tests.*", "docs", "scripts"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
    },
    entry_points={
        "console_scripts": [
            "mavr=src.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
