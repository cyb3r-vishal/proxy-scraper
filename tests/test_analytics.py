#!/usr/bin/env python3
"""
Test script for proxy analytics functionality
"""

import os
import sys
import unittest
import tempfile
import sqlite3
from datetime import datetime, timedelta

# Add parent directory to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import analytics module
try:
    from proxy_analytics import ProxyAnalytics
except ImportError:
    print("Error: proxy_analytics module not found.")
    sys.exit(1)


class TestProxyAnalytics(unittest.TestCase):
    """Test suite for the ProxyAnalytics class"""
    
    def setUp(self):
        """Set up a temporary database for testing"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        self.analytics = ProxyAnalytics(db_path=self.temp_db.name)
    
    def tearDown(self):
        """Clean up temporary database after tests"""
        os.unlink(self.temp_db.name)
    
    def test_record_check(self):
        """Test recording a single proxy check"""
        # Record a successful check
        self.analytics.record_check(
            proxy="192.168.1.1:8080",
            proxy_type="http",
            success=True,
            response_time=0.5,
            test_site="test.com"
        )
        
        # Record a failed check
        self.analytics.record_check(
            proxy="192.168.1.2:8080",
            proxy_type="https",
            success=False,
            error="Connection refused"
        )
        
        # Verify data was recorded correctly
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Check counts
        cursor.execute("SELECT COUNT(*) FROM proxy_checks")
        self.assertEqual(cursor.fetchone()[0], 2)
        
        cursor.execute("SELECT COUNT(*) FROM proxy_stats")
        self.assertEqual(cursor.fetchone()[0], 2)
        
        # Check success record
        cursor.execute(
            "SELECT proxy, success, response_time FROM proxy_checks WHERE proxy=?", 
            ("192.168.1.1:8080",)
        )
        record = cursor.fetchone()
        self.assertEqual(record[0], "192.168.1.1:8080")
        self.assertEqual(record[1], 1)  # success is stored as 1
        self.assertEqual(record[2], 0.5)
        
        # Check failure record
        cursor.execute(
            "SELECT proxy, success, error FROM proxy_checks WHERE proxy=?", 
            ("192.168.1.2:8080",)
        )
        record = cursor.fetchone()
        self.assertEqual(record[0], "192.168.1.2:8080")
        self.assertEqual(record[1], 0)  # failure is stored as 0
        self.assertEqual(record[2], "Connection refused")
        
        conn.close()
    
    def test_get_proxy_stats(self):
        """Test retrieving proxy statistics"""
        # Add test data
        test_proxies = [
            {"proxy": "10.0.0.1:8080", "proxy_type": "http", "success": True, "response_time": 0.3},
            {"proxy": "10.0.0.1:8080", "proxy_type": "http", "success": True, "response_time": 0.4},
            {"proxy": "10.0.0.1:8080", "proxy_type": "http", "success": True, "response_time": 0.5},
            {"proxy": "10.0.0.2:8080", "proxy_type": "http", "success": True, "response_time": 0.2},
            {"proxy": "10.0.0.2:8080", "proxy_type": "http", "success": False},
            {"proxy": "10.0.0.3:8080", "proxy_type": "https", "success": False},
            {"proxy": "10.0.0.3:8080", "proxy_type": "https", "success": False}
        ]
        
        for check in test_proxies:
            self.analytics.record_check(**check)
        
        # Get stats
        stats = self.analytics.get_proxy_stats()
        
        # Verify stats
        self.assertEqual(len(stats), 3)  # Three proxies in total
        
        # Verify proxies are sorted by reliability score
        self.assertEqual(stats[0]['proxy'], "10.0.0.1:8080")  # Most reliable (3/3 success)
        self.assertEqual(stats[1]['proxy'], "10.0.0.2:8080")  # Medium (1/2 success)
        self.assertEqual(stats[2]['proxy'], "10.0.0.3:8080")  # Least reliable (0/2 success)
    
    def test_cleanup(self):
        """Test cleanup of old records"""
        # Add current records
        self.analytics.record_check(
            proxy="1.1.1.1:80", 
            proxy_type="http", 
            success=True
        )
        
        # Add old records by directly manipulating the database
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        
        # Insert record with old timestamp (45 days ago)
        old_date = (datetime.now() - timedelta(days=45)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO proxy_checks (proxy, proxy_type, timestamp, success) VALUES (?, ?, ?, ?)",
            ("2.2.2.2:80", "http", old_date, 1)
        )
        
        # Update stats table for consistency
        cursor.execute(
            "INSERT INTO proxy_stats (proxy, proxy_type, first_seen, last_seen, success_count) VALUES (?, ?, ?, ?, ?)",
            ("2.2.2.2:80", "http", old_date, old_date, 1)
        )
        
        conn.commit()
        conn.close()
        
        # Verify we have 2 records before cleanup
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM proxy_checks")
        self.assertEqual(cursor.fetchone()[0], 2)
        conn.close()
        
        # Run cleanup (default 30 days)
        deleted = self.analytics.cleanup()
        
        # Check that old record was deleted
        conn = sqlite3.connect(self.temp_db.name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM proxy_checks")
        self.assertEqual(cursor.fetchone()[0], 1)  # Only the current record remains
        
        cursor.execute("SELECT proxy FROM proxy_checks")
        self.assertEqual(cursor.fetchone()[0], "1.1.1.1:80")  # Verify it's the current record
        
        conn.close()
        
        # Verify deleted count
        self.assertEqual(deleted, 1)


if __name__ == "__main__":
    unittest.main()
