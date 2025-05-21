"""
ProxyMaster Setup Script
"""
from setuptools import setup

setup(
    name='proxyz',
    version='1.0.0',
    py_modules=[
        'proxyScraper', 
        'proxymaster', 
        'proxy_validator', 
        'proxy_cache',        
        'proxy_monitor', 
        'proxy_rotator',
        'proxy_geo',
        'auto_proxy',
        'proxy_analytics'
    ],
    install_requires=[
        'httpx',
        'beautifulsoup4',
        'pysocks',
        'rich',
        'requests',
        'schedule',
        'aiohttp',
        'asyncio',
    ],    entry_points={
        'console_scripts': [
            'proxy_scraper=proxyScraper:main',
            'proxymaster=proxymaster:main',
            'auto_proxy=auto_proxy:main',
            'proxy_analytics=proxy_analytics:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['user_agents.txt'],
    },
    author='cyb3r_vishal',
    description='A comprehensive suite of tools for scraping, validating, and managing proxy lists',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/cyb3r-vishal/proxy-scraper',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Internet :: Proxy Servers',
        'Topic :: Utilities',
    ],
    python_requires='>=3.7',    data_files=[
        ('', ['requirements.txt', 'README.md', 'LICENSE', 'ENHANCEMENTS.md']),
        ('scripts', ['run-proxy.ps1', 'run-proxy.sh', 'start-auto-proxy.bat', 'run-analytics.bat']),
        ('docs', ['docs/AUTO_PROXY.md', 'docs/ANALYTICS.md']),
    ],
)
