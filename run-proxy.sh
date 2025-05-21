#!/bin/bash
# Unix shell script to run ProxyMaster with color support
# This script provides a convenient way to run the ProxyMaster tool
# Created by: cyb3r_vishal (community DevKitX)

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set Python executable
PYTHON="python3"

# Define functions for different proxy types
get_http_proxies() {
    echo -e "\n${BLUE}🔍 Scraping and validating HTTP proxies...${NC}"
    $PYTHON "$SCRIPT_DIR/proxymaster.py" -p http
}

get_https_proxies() {
    echo -e "\n${BLUE}🔍 Scraping and validating HTTPS proxies...${NC}"
    $PYTHON "$SCRIPT_DIR/proxymaster.py" -p https
}

get_socks4_proxies() {
    echo -e "\n${BLUE}🔍 Scraping and validating SOCKS4 proxies...${NC}"
    $PYTHON "$SCRIPT_DIR/proxymaster.py" -p socks4
}

get_socks5_proxies() {
    echo -e "\n${BLUE}🔍 Scraping and validating SOCKS5 proxies...${NC}"
    $PYTHON "$SCRIPT_DIR/proxymaster.py" -p socks5
}

start_proxy_monitor() {
    echo -e "\n${BLUE}🔄 Starting proxy monitor service...${NC}"
    $PYTHON "$SCRIPT_DIR/proxy_monitor.py" "$@"
}

add_geo_data() {
    echo -e "\n${BLUE}🌎 Adding geolocation data to proxies...${NC}"
    $PYTHON "$SCRIPT_DIR/proxy_geo.py" "$@"
}

start_proxy_rotator() {
    echo -e "\n${BLUE}🔄 Starting proxy rotator server...${NC}"
    $PYTHON "$SCRIPT_DIR/proxy_rotator.py" "$@"
}

start_proxy_gui() {
    echo -e "\n${BLUE}🖥️ Starting ProxyMaster GUI...${NC}"
    $PYTHON "$SCRIPT_DIR/gui/proxymaster_gui.py"
}

show_help() {
    echo -e "\n${YELLOW}=== ProxyMaster Launcher ===${NC}"
    echo "A convenient wrapper for the ProxyMaster tool"
    echo ""
    
    echo -e "${GREEN}Usage:${NC}"
    echo "  ./run-proxy.sh [command] [options]"
    echo ""
    
    echo -e "${GREEN}Commands:${NC}"
    echo "  http        Scrape and validate HTTP proxies"
    echo "  https       Scrape and validate HTTPS proxies"
    echo "  socks4      Scrape and validate SOCKS4 proxies"
    echo "  socks5      Scrape and validate SOCKS5 proxies"
    echo "  custom      Run with custom options (pass all options after 'custom')"
    echo "  monitor     Start the proxy monitor service"
    echo "  geo         Add geolocation data to proxy list"
    echo "  rotate      Start a rotating proxy server"
    echo "  gui         Start the graphical user interface"
    echo "  help        Show this help message"
    echo ""
    
    echo -e "${GREEN}Examples:${NC}"
    echo "  ./run-proxy.sh http              # Get HTTP proxies"
    echo "  ./run-proxy.sh socks5            # Get SOCKS5 proxies"
    echo "  ./run-proxy.sh custom -p http -t 20 -s icanhazip.com"
    echo "  ./run-proxy.sh monitor -p http -n 30  # Monitor HTTP proxies every 30 minutes"
    echo "  ./run-proxy.sh geo -i output/http_live.txt  # Add geolocation to proxies"
    echo "  ./run-proxy.sh rotate -i output/http_live.txt  # Start a rotating proxy server"
    echo "  ./run-proxy.sh gui               # Start the graphical user interface"
    echo ""
}

# Make sure the script is executable
chmod +x "$SCRIPT_DIR/proxymaster.py"
chmod +x "$SCRIPT_DIR/proxy_monitor.py"
chmod +x "$SCRIPT_DIR/proxy_geo.py"
chmod +x "$SCRIPT_DIR/proxy_rotator.py"
chmod +x "$SCRIPT_DIR/gui/proxymaster_gui.py"

# Process command line arguments
if [ $# -eq 0 ]; then
    show_help
    exit 0
fi

COMMAND="${1,,}"  # Convert to lowercase

case "$COMMAND" in
    "http")
        get_http_proxies
        ;;
    "https")
        get_https_proxies
        ;;
    "socks4")
        get_socks4_proxies
        ;;
    "socks5")
        get_socks5_proxies
        ;;
    "custom")
        # Pass all remaining args to the script
        shift
        $PYTHON "$SCRIPT_DIR/proxymaster.py" "$@"
        ;;
    "monitor")
        # Pass all remaining args to the monitor script
        shift
        start_proxy_monitor "$@"
        ;;
    "geo")
        # Pass all remaining args to the geo script
        shift
        add_geo_data "$@"
        ;;
    "rotate")
        # Pass all remaining args to the rotator script
        shift
        start_proxy_rotator "$@"
        ;;
    "gui")
        # Start the GUI with no args
        start_proxy_gui
        ;;
    "help")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        show_help
        ;;
esac
