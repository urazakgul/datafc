from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="datafc",
    version="1.5.0",
    author="Uraz Akgül",
    author_email="urazdev@gmail.com",
    description="A scalable Python library for fetching, processing, and exporting structured football match data.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/urazakgul/datafc",
    license="MIT",
    keywords="football soccer data analytics sofascore selenium",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "selenium",
        "webdriver_manager",
        "openpyxl"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)