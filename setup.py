from setuptools import setup

requires = [
    "python-dateutil",
    "jsonschema",
    'typing_extensions;python_version<"3.8"',
    'dataclasses;python_version<"3.7"',
]

test_dependencies = [
    "apispec_webframeworks",
    "apispec[yaml]",
    "black==22.8.0",
    "flake8",
    "flask",
    "isort",
    "mypy",
    "pytest-ordering",
    "pytest",
    "tox-gh-actions",
    "tox",
    "types-python-dateutil",
]


def read(f):
    return open(f, encoding="utf-8").read()


setup(
    name="dataclasses-jsonschema",
    description="JSON schema generation from dataclasses",
    long_description=read("README.rst"),
    packages=["dataclasses_jsonschema"],
    package_data={"dataclasses_jsonschema": ["py.typed"]},
    author="Simon Knibbs",
    author_email="simon.knibbs@gmail.com",
    url="https://github.com/s-knibbs/dataclasses-jsonschema",
    install_requires=requires,
    extras_require={
        "apispec": ["apispec"],
        "fast-validation": ["fastjsonschema"],
        "fast-dateparsing": ["ciso8601"],
        "fast-uuid": ["fastuuid"],
        "test": test_dependencies,
    },
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=test_dependencies,
    license="MIT",
    use_scm_version=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries",
    ],
)
