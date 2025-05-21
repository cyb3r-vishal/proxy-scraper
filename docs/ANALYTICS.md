# Proxy Analytics

ProxyMaster includes advanced analytics capabilities to track and analyze proxy performance over time. This system helps identify trends, reliability patterns, and optimize your proxy usage for better results.

## Overview

The Proxy Analytics module provides:

- Database storage of all proxy validation attempts
- Historical performance tracking for each proxy
- Success/failure metrics over time 
- Response time analysis
- Reliability scoring
- Visualization capabilities
- Various report formats (console, CSV, JSON, plots)

## Usage

### Command Line Interface

```bash
# Generate a summary report
python proxy_analytics.py report --type summary

# Generate a trend report for the last 14 days
python proxy_analytics.py report --type trend --days 14

# List top performing proxies for a specific type
python proxy_analytics.py report --type top_proxies --proxy-type http

# Generate a CSV report
python proxy_analytics.py report --type summary --format csv

# Create a visual plot of trends
python proxy_analytics.py report --type trend --format plot

# Clean up old records (older than 60 days)
python proxy_analytics.py cleanup --days 60
```

### PowerShell Script

```powershell
# Generate a summary report
.\run-proxy.ps1 analytics report -t summary

# Generate a trend report for the last 14 days
.\run-proxy.ps1 analytics report -t trend -d 14

# List top performing proxies for a specific type
.\run-proxy.ps1 analytics report -t top_proxies -p http

# Generate a CSV report
.\run-proxy.ps1 analytics report -t summary -f csv

# Create a visual plot of trends
.\run-proxy.ps1 analytics report -t trend -f plot

# Clean up old records (older than 60 days)
.\run-proxy.ps1 analytics cleanup -d 60
```

## Integration with Auto Proxy

The analytics system is automatically integrated with Auto Proxy. When the Auto Proxy service runs, it records all validation attempts to the analytics database, building up a historical record of proxy performance.

## Reports

### Summary Reports

Shows aggregated statistics by proxy type:
- Total proxies tracked
- Success and failure counts
- Average uptime percentage
- Average response times
- Average reliability scores

### Trend Reports

Shows how proxy performance metrics change over time:
- Daily success rates
- Average response times by day
- Total check volumes
- Success/failure ratios

### Top Proxies Reports

Lists the best performing proxies based on reliability scores:
- Individual proxy success/failure counts
- Uptime percentages
- Response times
- Reliability scores
- Country information (when available)

## Custom Integration

You can integrate the analytics system into your custom scripts:

```python
from proxy_analytics import ProxyAnalytics

# Initialize
analytics = ProxyAnalytics()

# Record a successful proxy check
analytics.record_check(
    proxy="192.168.1.1:8080",
    proxy_type="http",
    success=True,
    response_time=0.45,
    test_site="example.com"
)

# Record a failed proxy check
analytics.record_check(
    proxy="192.168.1.2:8080",
    proxy_type="http",
    success=False,
    error="Connection timeout"
)

# Get statistics on HTTP proxies with at least 5 checks and 50% uptime
stats = analytics.get_proxy_stats(
    proxy_type="http",
    min_checks=5,
    min_uptime=50.0,
    limit=20
)

# Generate a report
analytics.generate_report(
    report_type="summary",
    proxy_type="http",
    output_format="console"
)
```

## Database Structure

Analytics data is stored in an SQLite database with the following main tables:

- `proxy_checks`: Individual validation attempts
- `proxy_stats`: Aggregated statistics for each proxy

## Data Retention

By default, the analytics system retains data for 30 days. You can change this by running the cleanup command with a different day parameter.
