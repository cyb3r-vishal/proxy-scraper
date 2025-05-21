# ProxyMaster GUI

This directory contains the graphical user interface for ProxyMaster.

Created by: cyb3r_vishal (community DevKitX)

## Overview

The GUI provides a user-friendly interface to all ProxyMaster functionality:

- Proxy scraping and validation
- Automatic proxy monitoring
- Geolocation data analysis
- Proxy rotation server

## Running the GUI

You can start the GUI in one of these ways:

### From the command line

```bash
# Direct execution
python gui/proxymaster_gui.py

# Using the provided scripts
# Windows:
.\run-proxy.ps1 gui

# Unix:
./run-proxy.sh gui
```

## Features

The GUI is organized into tabs, each focused on a specific aspect of proxy management:

1. **Scraper & Validator Tab**: Discover and test proxies
2. **Proxy Monitor Tab**: Keep your proxy lists fresh
3. **Geolocation Tab**: Add and analyze location data
4. **Proxy Rotator Tab**: Run a local proxy rotation server

## Requirements

The GUI requires additional Python packages:
- customtkinter
- ttkthemes

These should be automatically installed when running `install.py` or can be manually installed with:

```bash
pip install customtkinter ttkthemes
```

## Troubleshooting

If you encounter any issues with the GUI:

1. Make sure all dependencies are installed
2. Check if you can run the command-line versions of the tools
3. Examine the console output for error messages
