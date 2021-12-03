import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="oocd_tool",
    version="0.1.0",
    author="Jacob Schultz Andersen",
    author_email="schultz.jacob@gmail.com",
    description="A flexible configuration and remote contol tool for openocd.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jasa/oocd-tool.git",
    project_urls={
        "Bug Tracker": "https://github.com/jasa/oocd-tool/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MPL 2 License",
        "Operating System :: OS Independent",
    ],
    install_requires = [
         "setuptools>=42",
         "psutil>=5",
         "grpcio>=1.41",
         "grpcio-tools>=1.41"
    ],
    keywords='arm gdb cortex cortex-m trace microcontroller',
    packages = setuptools.find_packages(),
    python_requires=">=3.6",
    scripts = ['bin/oocd-tool', 'bin/oocd-rpcd'],
    entry_points = {
        "console_scripts": [
            "oocd_tool = oocd_tool.main:main",
        ],
    },
)
