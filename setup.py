import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cb_da",
    version="0.0.6",
    install_requires=[
        'pandas>=1.2.5',
        'numpy>=1.20.2',
    ],
    author="ConsiliumBots",
    author_email="b.madariaga.e@gmail.com",
    description='A package with an implementation of the Galey-Shapley algorithm (deferred acceptance)',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ConsiliumBots/cb-da",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
