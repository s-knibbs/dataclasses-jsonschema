from setuptools import setup

requires = [
    'python-dateutil',
    'jsonschema',
    'dataclasses;python_version<"3.7"'
]


def read(f):
    return open(f, encoding='utf-8').read()


setup(
    name='dataclasses-jsonschema',
    description='JSON schema generation from dataclasses',
    long_description=read('README.rst'),
    packages=['dataclasses_jsonschema'],
    package_data={'dataclasses_jsonschema': ["py.typed"]},
    author='Simon Knibbs',
    author_email='simon.knibbs@gmail.com',
    url='https://github.com/s-knibbs/dataclasses-jsonschema',
    install_requires=requires,
    extras_require={
        'fast-validation': ["PyValico>=0.0.1"]
    },
    setup_requires=['pytest-runner', 'setuptools_scm'],
    tests_require=['pytest', 'flake8', 'mypy'],
    license='MIT',
    use_scm_version=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries'
    ]
)
