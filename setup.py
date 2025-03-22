from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="brother_eye",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["main"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "brother_eye=main:main",
        ],
    },
    package_data={
        "": ["*.tcss", "*.json"],
    },
    include_package_data=True,
    python_requires=">=3.12,<3.13",
    description="a terminal voice assistant meant to be lightweight and local",
    author="Issa Euceph",
    author_email="ieuceph@gmail.com",
    url="https://github.com/euceph/brother_eye",
)