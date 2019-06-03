import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='gwbrowser',
    version='0.1.50',
    author='Gergely Wootsch',
    author_email='hello@gergely-wootsch.com',
    description='A PySide2 based asset-manager for digital production',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/wgergely/gwbrowser',
    packages=setuptools.find_packages(),
        include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
    ],
)
