from setuptools import setup, find_packages
version = {}
with open("fasterapi/__version__.py") as f:
    exec(f.read(), version)
    
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()
    
setup(
    name="nats-fasterapi",
     version=version["__version__"],
    description="A CLI tool to scaffold FastAPI projects with CRUD and schema support",
    author="Nathaniel Uriri",
    author_email="nat@uriri.com.ng",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nathanieluriri/faster-api",
    packages=find_packages(),
    include_package_data=True,

    install_requires=[
        "click",
        "pymongo",
        "pydantic",
        "fastapi[all]",
        "motor",
        "redis",
        "requests",
        "bcrypt",
        "pyjwt",
        "python-dotenv",
    ],

    entry_points={
        "console_scripts": [
            "fasterapi=fasterapi.cli:cli",
        ],
    },

    classifiers=[
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],

    python_requires=">=3.8",
)
