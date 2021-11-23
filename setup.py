import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="openocd-tool",
    version="0.0.1",
    author="Jacob Schultz Andersen",
    author_email="schultz.jacob@gmail.com",
    description="openocd-tool is a helper script to openocd. Used to program and debug embedded devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jasa/openocd-tool.git",
    project_urls={
        "Bug Tracker": "https://github.com/jasa/openocd-tool/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MPL 2 License",
        "Operating System :: OS Independent",
    ],
    install_requires = [
         "setuptools>=42",
         "psutil>=5"
    ],   
    keywords='arm gdb cortex cortex-m trace microcontroller',
    packages = setuptools.find_packages(),
    python_requires=">=3.6",
    scripts = ['scripts/openocd-tool'],
)
