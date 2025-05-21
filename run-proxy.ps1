
# PowerShell script to run ProxyMaster with color support

# Get the script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Set Python executable
$Python = "python"

# Define functions for different proxy types
function Get-HttpProxies {
    Write-Host "`n Scraping and validating HTTP proxies..." -ForegroundColor Cyan
    if (Test-Path "$ScriptDir\fresh_http_proxies.txt") {
        & $Python "$ScriptDir\proxymaster.py" -p http -i "$ScriptDir\fresh_http_proxies.txt"
    } else {
        & $Python "$ScriptDir\fresh_proxies.py"
        & $Python "$ScriptDir\proxymaster.py" -p http -i "$ScriptDir\fresh_http_proxies.txt"
    }
}

function Get-HttpsProxies {
    Write-Host "`n Scraping and validating HTTPS proxies..." -ForegroundColor Cyan
    & $Python "$ScriptDir\proxymaster.py" -p https
}

function Get-Socks4Proxies {
    Write-Host "`n Scraping and validating SOCKS4 proxies..." -ForegroundColor Cyan
    & $Python "$ScriptDir\proxymaster.py" -p socks4
}

function Get-Socks5Proxies {
    Write-Host "`n Scraping and validating SOCKS5 proxies..." -ForegroundColor Cyan
    & $Python "$ScriptDir\proxymaster.py" -p socks5
}

function Start-ProxyMonitor {
    Write-Host "`n Starting proxy monitor service..." -ForegroundColor Cyan
    & $Python "$ScriptDir\proxy_monitor.py" $args
}

function Add-GeoData {
    Write-Host "`n Adding geolocation data to proxies..." -ForegroundColor Cyan
    & $Python "$ScriptDir\proxy_geo.py" $args
}

function Start-ProxyRotator {
    Write-Host "`n Starting proxy rotator server..." -ForegroundColor Cyan
    & $Python "$ScriptDir\proxy_rotator.py" $args
}

function Start-ProxyAnalytics {
    Write-Host "`n Running proxy analytics and generating reports..." -ForegroundColor Cyan
    & $Python "$ScriptDir\proxy_analytics.py" $args
}

function Start-ProxyGUI {
    Write-Host "`n Starting ProxyMaster GUI..." -ForegroundColor Cyan
    & $Python "$ScriptDir\gui\proxymaster_gui.py"
}

function Start-AutoProxy {
    Write-Host "`n Starting automatic proxy scraper and validator..." -ForegroundColor Magenta
    & $Python "$ScriptDir\auto_proxy.py" $args
}

function Show-Help {
    Write-Host "`n=== ProxyMaster Launcher ===" -ForegroundColor Yellow
    Write-Host "A convenient wrapper for the ProxyMaster tool`n"
    
    Write-Host "Usage:" -ForegroundColor Green
    Write-Host "  .\run-proxy.ps1 [command] [options]`n"
    
    Write-Host "Commands:" -ForegroundColor Green
    Write-Host "  http        Scrape and validate HTTP proxies"
    Write-Host "  https       Scrape and validate HTTPS proxies"
    Write-Host "  socks4      Scrape and validate SOCKS4 proxies"
    Write-Host "  socks5      Scrape and validate SOCKS5 proxies"
    Write-Host "  auto        Start automatic proxy scraping and validating"
    Write-Host "  monitor     Start the proxy monitor service"
    Write-Host "  geo         Add geolocation data to proxy list"
    Write-Host "  rotate      Start a rotating proxy server" 
    Write-Host "  analytics   Generate proxy performance reports and statistics"
    Write-Host "  gui         Start the graphical user interface"
    Write-Host "  custom      Run with custom options"
    Write-Host "  telegram    Enable Telegram integration"
    Write-Host "  help        Show this help message`n"
    
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\run-proxy.ps1 http              # Get HTTP proxies"
    Write-Host "  .\run-proxy.ps1 socks5            # Get SOCKS5 proxies"
    Write-Host "  .\run-proxy.ps1 auto -t http,https -i 30  # Auto scrape HTTP/HTTPS proxies every 30 minutes"
    Write-Host "  .\run-proxy.ps1 monitor -p http -n 30  # Monitor HTTP proxies every 30 minutes"
    Write-Host "  .\run-proxy.ps1 geo -i output/http_live.txt  # Add geolocation to proxies"
    Write-Host "  .\run-proxy.ps1 rotate -i output/http_live.txt  # Start a rotating proxy server"
    Write-Host "  .\run-proxy.ps1 analytics report -t summary  # Generate proxy performance summary"
    Write-Host "  .\run-proxy.ps1 gui               # Start the graphical user interface"
    Write-Host "  .\run-proxy.ps1 custom -p http -t 20 -s icanhazip.com"
    Write-Host "  .\run-proxy.ps1 telegram -p http --telegram-token <token> --telegram-chat <chat_id> --telegram-batch 50"
    Write-Host "`n"
}

# Handle Ctrl+C gracefully
$job = $null

function Stop-ProxyMaster {
    Write-Host "`n`nStopping ProxyMaster..." -ForegroundColor Yellow
    # Kill any running Python processes started by this script
    Get-Process python | Where-Object { $_.CommandLine -like "*$ScriptDir*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    if ($job) {
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }
    exit
}

# Register the event handler for Ctrl+C
$job = Register-ObjectEvent -InputObject ([System.Console]) -EventName CancelKeyPress -Action { Stop-ProxyMaster }

# Make sure we clean up when the script exits
trap {
    Stop-ProxyMaster
    break
}

# Process command line arguments
if ($args.Count -eq 0) {
    Show-Help
    exit
}

$Command = $args[0].ToLower()

try {
    switch ($Command) {
        "http" { 
            Get-HttpProxies
        }
        "https" { 
            Get-HttpsProxies
        }
        "socks4" { 
            Get-Socks4Proxies
        }
        "socks5" { 
            Get-Socks5Proxies
        }
        "auto" {
            # Pass all remaining args to the auto proxy script
            $AutoArgs = $args[1..($args.Count-1)]
            Start-AutoProxy $AutoArgs
        }
        "monitor" {
            # Pass all remaining args to the monitor script
            $MonitorArgs = $args[1..($args.Count-1)]
            Start-ProxyMonitor $MonitorArgs
        }
        "geo" {
            # Pass all remaining args to the geo script
            $GeoArgs = $args[1..($args.Count-1)]
            Add-GeoData $GeoArgs
        }
        "rotate" {
            # Pass all remaining args to the rotator script
            $RotatorArgs = $args[1..($args.Count-1)]
            Start-ProxyRotator $RotatorArgs
        }
        "analytics" {
            # Pass all remaining args to the analytics script
            $AnalyticsArgs = $args[1..($args.Count-1)]
            Start-ProxyAnalytics $AnalyticsArgs
        }
        "gui" {
            # Start the GUI with no args
            Start-ProxyGUI
        }
        "custom" {
            # Pass all remaining args to the script
            $CustomArgs = $args[1..($args.Count-1)]
            & $Python "$ScriptDir\proxymaster.py" $CustomArgs
        }
        "telegram" {
            # Get the remaining arguments for Python
            $TelegramArgs = $args[1..($args.Count-1)]
            
            Write-Host "`n Enabling Telegram integration..." -ForegroundColor Magenta
            
            # Direct pass to Python
            & $Python "$ScriptDir\proxymaster.py" $TelegramArgs
        }
        "help" {
            Show-Help
        }
        default {
            Write-Host "Unknown command: $Command" -ForegroundColor Red
            Show-Help
        }
    }
}
catch {
    Write-Host "`nError: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
