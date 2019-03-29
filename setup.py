import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='GWBrowser-pkg',
    version='0.1.2',
    author='Gergely Wootsch',
    author_email='hello@gergely-wootsch.com',
    description='GWBrowser',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/wgergely/GWBrowser',
    packages=['GWBrowser'],
	include_package_data=True,
    package_data={
        'GWBrowser': ['.py', '*.png', '*.css', '*.ttf', '*.ico'],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 2',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Microsoft :: Windows',
    ],
)
