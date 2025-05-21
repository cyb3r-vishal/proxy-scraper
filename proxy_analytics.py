#!/usr/bin/env python3
"""
Proxy Analytics - Track and analyze proxy performance over time
"""

import os
import sys
import json
import time
import sqlite3
import datetime
from pathlib import Path
import argparse
import logging
from typing import Dict, List, Tuple, Union, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("proxy_analytics.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ProxyAnalytics")

# Check for required packages and install if missing
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    logger.info("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "matplotlib", "rich"])
    import pandas as pd
    import matplotlib.pyplot as plt
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

console = Console()

# Default paths
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "proxy_metrics.db")
REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


class ProxyAnalytics:
    """Class to track and analyze proxy performance over time"""
    
    def __init__(self, db_path: str = DB_PATH) -> None:
        """Initialize the analytics system with database connection"""
        self.db_path = db_path
        self._init_db()
        self.console = Console()
    
    def _init_db(self) -> None:
        """Initialize the SQLite database and create tables if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxy_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy TEXT,
                proxy_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                response_time FLOAT,
                test_site TEXT,
                error TEXT
            )
            ''')
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxy_stats (
                proxy TEXT,
                proxy_type TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                avg_response_time FLOAT DEFAULT 0,
                uptime_percentage FLOAT DEFAULT 0,
                reliability_score FLOAT DEFAULT 0,
                country TEXT,
                PRIMARY KEY (proxy, proxy_type)
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info(f"Database initialized at {self.db_path}")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def record_check(self, proxy: str, proxy_type: str, success: bool, 
                    response_time: float = 0.0, test_site: str = None, 
                    error: str = None) -> None:
        """Record a single proxy check result to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert the check result
            cursor.execute('''
            INSERT INTO proxy_checks (proxy, proxy_type, success, response_time, test_site, error)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (proxy, proxy_type, success, response_time, test_site, error))
            
            # Update or insert stats record
            cursor.execute('''
            INSERT INTO proxy_stats (
                proxy, proxy_type, first_seen, last_seen, 
                success_count, failure_count, avg_response_time
            )
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?, ?)
            ON CONFLICT(proxy, proxy_type) DO UPDATE SET
                last_seen = CURRENT_TIMESTAMP,
                success_count = CASE WHEN ? THEN proxy_stats.success_count + 1 ELSE proxy_stats.success_count END,
                failure_count = CASE WHEN ? THEN proxy_stats.failure_count + 1 ELSE proxy_stats.failure_count END,
                avg_response_time = CASE WHEN ? THEN 
                    (proxy_stats.avg_response_time * proxy_stats.success_count + ?) / (proxy_stats.success_count + 1)
                    ELSE proxy_stats.avg_response_time END,
                uptime_percentage = 100.0 * (proxy_stats.success_count + CASE WHEN ? THEN 1 ELSE 0 END) / 
                    (proxy_stats.success_count + proxy_stats.failure_count + 1),
                reliability_score = CASE WHEN ? THEN 
                    (proxy_stats.success_count + 1) / 
                    (proxy_stats.success_count + proxy_stats.failure_count + 1) * 
                    (1 / (1 + CASE WHEN (proxy_stats.avg_response_time * proxy_stats.success_count + ?) / (proxy_stats.success_count + 1) = 0 
                        THEN 0.001 ELSE (proxy_stats.avg_response_time * proxy_stats.success_count + ?) / (proxy_stats.success_count + 1) END))
                    ELSE 
                    proxy_stats.success_count / 
                    (proxy_stats.success_count + proxy_stats.failure_count + 1) * 
                    (1 / (1 + CASE WHEN proxy_stats.avg_response_time = 0 THEN 0.001 ELSE proxy_stats.avg_response_time END))
                    END
            ''', (
                proxy, proxy_type, 
                1 if success else 0, 0 if success else 1, 
                response_time if success else 0,
                success, not success, success, response_time,
                success, success, response_time, response_time
            ))
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            logger.error(f"Error recording proxy check: {e}")
    
    def record_batch(self, results: List[Dict]) -> None:
        """Record multiple proxy check results at once"""
        for result in results:
            self.record_check(
                result['proxy'],
                result.get('proxy_type', 'http'),
                result['success'],
                result.get('response_time', 0.0),
                result.get('test_site'),
                result.get('error')
            )
    
    def get_proxy_stats(self, proxy_type: str = None, min_checks: int = 3, 
                        min_uptime: float = 0.0, limit: int = 100) -> List[Dict]:
        """Get statistics for proxies matching criteria"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = '''
            SELECT 
                proxy, proxy_type, first_seen, last_seen,
                success_count, failure_count, avg_response_time,
                uptime_percentage, reliability_score, country
            FROM proxy_stats
            WHERE (success_count + failure_count) >= ?
            AND uptime_percentage >= ?
            '''
            params = [min_checks, min_uptime]
            
            if proxy_type:
                query += " AND proxy_type = ?"
                params.append(proxy_type)
            
            query += " ORDER BY reliability_score DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Error retrieving proxy stats: {e}")
            return []
    
    def generate_report(self, report_type: str = 'summary', 
                         proxy_type: str = None, days: int = 7,
                         output_format: str = 'console') -> str:
        """Generate a report of proxy performance"""
        conn = sqlite3.connect(self.db_path)
        
        if report_type == 'summary':
            # Summary report with key metrics
            if proxy_type:
                df = pd.read_sql_query(f'''
                SELECT 
                    proxy_type,
                    COUNT(DISTINCT proxy) as total_proxies,
                    SUM(success_count) as total_successes,
                    SUM(failure_count) as total_failures,
                    ROUND(AVG(uptime_percentage), 2) as avg_uptime,
                    ROUND(AVG(avg_response_time), 3) as avg_response_time,
                    ROUND(AVG(reliability_score), 3) as avg_reliability
                FROM proxy_stats
                WHERE proxy_type = ?
                GROUP BY proxy_type
                ''', conn, params=[proxy_type])
            else:
                df = pd.read_sql_query('''
                SELECT 
                    proxy_type,
                    COUNT(DISTINCT proxy) as total_proxies,
                    SUM(success_count) as total_successes,
                    SUM(failure_count) as total_failures,
                    ROUND(AVG(uptime_percentage), 2) as avg_uptime,
                    ROUND(AVG(avg_response_time), 3) as avg_response_time,
                    ROUND(AVG(reliability_score), 3) as avg_reliability
                FROM proxy_stats
                GROUP BY proxy_type
                ''', conn)
        
        elif report_type == 'trend':
            # Trend report over time
            days_ago = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            if proxy_type:
                df = pd.read_sql_query(f'''
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as total_checks,
                    SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failures,
                    ROUND(AVG(CASE WHEN success=1 THEN response_time ELSE NULL END), 3) as avg_response_time,
                    ROUND(100.0 * SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
                FROM proxy_checks
                WHERE proxy_type = ? AND timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp)
                ''', conn, params=[proxy_type, days_ago])
            else:
                df = pd.read_sql_query(f'''
                SELECT 
                    DATE(timestamp) as date,
                    COUNT(*) as total_checks,
                    SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes,
                    SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failures,
                    ROUND(AVG(CASE WHEN success=1 THEN response_time ELSE NULL END), 3) as avg_response_time,
                    ROUND(100.0 * SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
                FROM proxy_checks
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY DATE(timestamp)
                ''', conn, params=[days_ago])
            
        elif report_type == 'top_proxies':
            # Top performing proxies
            limit = 20
            if proxy_type:
                df = pd.read_sql_query(f'''
                SELECT 
                    proxy, proxy_type,
                    success_count, failure_count,
                    ROUND(uptime_percentage, 2) as uptime,
                    ROUND(avg_response_time, 3) as response_time,
                    ROUND(reliability_score, 4) as reliability,
                    country
                FROM proxy_stats
                WHERE proxy_type = ? AND (success_count + failure_count) >= 5
                ORDER BY reliability_score DESC
                LIMIT ?
                ''', conn, params=[proxy_type, limit])
            else:
                df = pd.read_sql_query(f'''
                SELECT 
                    proxy, proxy_type,
                    success_count, failure_count,
                    ROUND(uptime_percentage, 2) as uptime,
                    ROUND(avg_response_time, 3) as response_time,
                    ROUND(reliability_score, 4) as reliability,
                    country
                FROM proxy_stats
                WHERE (success_count + failure_count) >= 5
                ORDER BY reliability_score DESC
                LIMIT ?
                ''', conn, params=[limit])
            
        conn.close()
        
        # Handle output format
        if output_format == 'csv':
            filename = f"proxy_{report_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = os.path.join(REPORTS_DIR, filename)
            df.to_csv(filepath, index=False)
            logger.info(f"Report saved to {filepath}")
            return filepath
            
        elif output_format == 'json':
            filename = f"proxy_{report_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(REPORTS_DIR, filename)
            df.to_json(filepath, orient='records')
            logger.info(f"Report saved to {filepath}")
            return filepath
            
        elif output_format == 'console':
            if not df.empty:
                table = Table(title=f"Proxy {report_type.title()} Report", show_header=True, header_style="bold magenta")
                
                # Add columns based on DataFrame
                for col in df.columns:
                    table.add_column(col.replace('_', ' ').title(), style="cyan")
                
                # Add rows
                for _, row in df.iterrows():
                    table.add_row(*[str(val) for val in row])
                    
                console.print(table)
                return "Report displayed on console"
            else:
                console.print(Panel("[yellow]No data found for the requested report[/]", title="Warning"))
                return "No data found"
            
        elif output_format == 'plot':
            if report_type == 'trend' and not df.empty:
                plt.figure(figsize=(12, 6))
                
                # Success rate trend
                ax1 = plt.subplot(121)
                df.plot(x='date', y='success_rate', ax=ax1, color='green', marker='o')
                ax1.set_title('Success Rate Trend')
                ax1.set_ylabel('Success Rate (%)')
                ax1.set_xlabel('Date')
                ax1.grid(True, alpha=0.3)
                
                # Response time trend
                ax2 = plt.subplot(122)
                df.plot(x='date', y='avg_response_time', ax=ax2, color='blue', marker='o')
                ax2.set_title('Response Time Trend')
                ax2.set_ylabel('Avg. Response Time (s)')
                ax2.set_xlabel('Date')
                ax2.grid(True, alpha=0.3)
                
                plt.tight_layout()
                
                # Save the plot
                filename = f"proxy_trend_plot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                filepath = os.path.join(REPORTS_DIR, filename)
                plt.savefig(filepath)
                plt.close()
                logger.info(f"Plot saved to {filepath}")
                return filepath
                
            else:
                logger.warning("Plot output is only available for trend reports")
                return "Plot not available for this report type"
        else:
            return "Unknown output format"
    
    def cleanup(self, days: int = 30) -> int:
        """Clean up old records from the database"""
        try:
            retention_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM proxy_checks WHERE date(timestamp) < ?", (retention_date,))
            deleted_count = cursor.rowcount
            
            # Also clean up any proxies that haven't been seen recently and have few checks
            cursor.execute("""
            DELETE FROM proxy_stats 
            WHERE date(last_seen) < ? AND (success_count + failure_count) < 5
            """, (retention_date,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old proxy check records")
            return deleted_count
            
        except sqlite3.Error as e:
            logger.error(f"Error cleaning up database: {e}")
            return 0


def main():
    """Main function when script is run directly"""
    parser = argparse.ArgumentParser(description="Proxy Analytics - Track and analyze proxy performance")
    subparsers = parser.add_subparsers(dest="command", help="Action to perform")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate proxy analytics report")
    report_parser.add_argument("-t", "--type", choices=["summary", "trend", "top_proxies"], default="summary",
                              help="Type of report to generate")
    report_parser.add_argument("-p", "--proxy-type", help="Filter by proxy type (http, https, socks4, socks5)")
    report_parser.add_argument("-d", "--days", type=int, default=7, help="Number of days for trend reports")
    report_parser.add_argument("-f", "--format", choices=["console", "csv", "json", "plot"], default="console",
                              help="Output format for the report")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old records")
    cleanup_parser.add_argument("-d", "--days", type=int, default=30, 
                               help="Remove records older than specified days")
    
    args = parser.parse_args()
    analytics = ProxyAnalytics()
    
    if args.command == "report":
        result = analytics.generate_report(
            report_type=args.type,
            proxy_type=args.proxy_type,
            days=args.days,
            output_format=args.format
        )
        if args.format not in ["console", "plot"]:
            console.print(f"[green]Report saved: {result}[/]")
            
    elif args.command == "cleanup":
        count = analytics.cleanup(days=args.days)
        console.print(f"[green]Cleaned up {count} old records[/]")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/]")
        sys.exit(0)
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[bold red]Error: {str(e)}[/]")
        sys.exit(1)
