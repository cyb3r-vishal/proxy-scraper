"""
Analytics tab for the ProxyMaster GUI
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import datetime
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

try:
    import customtkinter as ctk
except ImportError:
    import subprocess
    print("Installing required GUI packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "customtkinter"])
    import customtkinter as ctk

# Import our analytics module
try:
    from proxy_analytics import ProxyAnalytics
    HAS_ANALYTICS = True
except ImportError:
    HAS_ANALYTICS = False


class AnalyticsTab:
    """Analytics tab for the ProxyMaster GUI"""
    
    def __init__(self, parent_notebook, app_instance):
        """Initialize the analytics tab"""
        self.parent = parent_notebook
        self.app = app_instance
        self.analytics = ProxyAnalytics() if HAS_ANALYTICS else None
        
        # Create the tab
        self.frame = ctk.CTkFrame(parent_notebook)
        parent_notebook.add(self.frame, text="Analytics")
        
        # Build the UI
        self._build_ui()
    
    def _build_ui(self):
        """Build the user interface for the analytics tab"""
        if not HAS_ANALYTICS:
            label = ctk.CTkLabel(
                self.frame, 
                text="Analytics module not available.\nRun 'pip install matplotlib pandas' to enable.",
                font=("Segoe UI", 14),
                text_color="orange"
            )
            label.pack(pady=20)
            return
            
        # Main container with left sidebar and right content
        container = ctk.CTkFrame(self.frame)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left sidebar for options
        sidebar = ctk.CTkFrame(container, width=200)
        sidebar.pack(side="left", fill="y", padx=5, pady=5)
        
        # Right content area
        content = ctk.CTkFrame(container)
        content.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Sidebar header
        header = ctk.CTkLabel(
            sidebar, 
            text="Analytics Options", 
            font=("Segoe UI", 14, "bold")
        )
        header.pack(pady=10)
        
        # Report type selection
        report_frame = ctk.CTkFrame(sidebar)
        report_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(report_frame, text="Report Type:").pack(anchor="w")
        
        self.report_type = tk.StringVar(value="summary")
        report_types = [
            ("Summary", "summary"),
            ("Trends", "trend"),
            ("Top Proxies", "top_proxies")
        ]
        
        for text, value in report_types:
            radio = ctk.CTkRadioButton(
                report_frame, 
                text=text, 
                variable=self.report_type, 
                value=value
            )
            radio.pack(anchor="w", padx=10, pady=2)
        
        # Proxy type selection
        filter_frame = ctk.CTkFrame(sidebar)
        filter_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(filter_frame, text="Proxy Type:").pack(anchor="w")
        
        self.proxy_type = tk.StringVar(value="")
        proxy_types = [
            ("All", ""),
            ("HTTP", "http"),
            ("HTTPS", "https"),
            ("SOCKS4", "socks4"),
            ("SOCKS5", "socks5")
        ]
        
        option_menu = ctk.CTkOptionMenu(
            filter_frame,
            values=[pt[0] for pt in proxy_types],
            command=self._on_proxy_type_change
        )
        option_menu.pack(fill="x", padx=5, pady=5)
        
        # Days selection for trend reports
        days_frame = ctk.CTkFrame(sidebar)
        days_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(days_frame, text="Days (for trends):").pack(anchor="w")
        
        self.days = ctk.CTkSlider(
            days_frame,
            from_=1,
            to=30,
            number_of_steps=29
        )
        self.days.set(7)
        self.days.pack(fill="x", padx=5, pady=5)
        
        self.days_label = ctk.CTkLabel(days_frame, text="7 days")
        self.days_label.pack()
        
        self.days.configure(command=self._update_days_label)
        
        # Action buttons
        button_frame = ctk.CTkFrame(sidebar)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        self.generate_button = ctk.CTkButton(
            button_frame,
            text="Generate Report",
            command=self._generate_report
        )
        self.generate_button.pack(fill="x", pady=5)
        
        self.export_button = ctk.CTkButton(
            button_frame,
            text="Export Data",
            command=self._export_data
        )
        self.export_button.pack(fill="x", pady=5)
        
        self.cleanup_button = ctk.CTkButton(
            button_frame,
            text="Cleanup Old Data",
            command=self._cleanup_data
        )
        self.cleanup_button.pack(fill="x", pady=5)
        
        # Content area - tabs for different views
        self.content_notebook = ttk.Notebook(content)
        self.content_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tab for report display
        self.report_frame = ctk.CTkFrame(self.content_notebook)
        self.content_notebook.add(self.report_frame, text="Report")
        
        # Tab for chart display
        self.chart_frame = ctk.CTkFrame(self.content_notebook)
        self.content_notebook.add(self.chart_frame, text="Chart")
        
        # Initial welcome message
        welcome = ctk.CTkLabel(
            self.report_frame,
            text="Welcome to Proxy Analytics!\n\nSelect options on the left and click 'Generate Report' to begin.",
            font=("Segoe UI", 14)
        )
        welcome.pack(pady=50)
    
    def _update_days_label(self, value=None):
        """Update the days label when the slider is moved"""
        days = int(self.days.get())
        self.days_label.configure(text=f"{days} days")
    
    def _on_proxy_type_change(self, selection):
        """Handle proxy type selection change"""
        for text, value in [
            ("All", ""),
            ("HTTP", "http"),
            ("HTTPS", "https"),
            ("SOCKS4", "socks4"),
            ("SOCKS5", "socks5")
        ]:
            if text == selection:
                self.proxy_type.set(value)
                break
    
    def _generate_report(self):
        """Generate the selected analytics report"""
        if not HAS_ANALYTICS:
            messagebox.showerror("Error", "Analytics module not available")
            return
            
        # Clear previous content
        for widget in self.report_frame.winfo_children():
            widget.destroy()
            
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Show loading indicator
        loading = ctk.CTkLabel(
            self.report_frame,
            text="Generating report...",
            font=("Segoe UI", 14)
        )
        loading.pack(pady=20)
        self.report_frame.update_idletasks()
        
        # Get selected options
        report_type = self.report_type.get()
        proxy_type = self.proxy_type.get()
        days = int(self.days.get())
        
        # Run in a thread to avoid blocking the UI
        def run_report():
            try:
                # Generate report with cache option for chart data
                cache_data = None
                
                if report_type == "trend":
                    # For trend reports, we need to get dataframe for charts
                    conn = self.analytics._init_db()
                    days_ago = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime('%Y-%m-%d')
                    
                    query = f'''
                    SELECT 
                        DATE(timestamp) as date,
                        COUNT(*) as total_checks,
                        SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as successes,
                        SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as failures,
                        ROUND(AVG(CASE WHEN success=1 THEN response_time ELSE NULL END), 3) as avg_response_time,
                        ROUND(100.0 * SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
                    FROM proxy_checks
                    '''
                    
                    params = []
                    if proxy_type:
                        query += " WHERE proxy_type = ? AND timestamp >= ?"
                        params = [proxy_type, days_ago]
                    else:
                        query += " WHERE timestamp >= ?"
                        params = [days_ago]
                        
                    query += " GROUP BY DATE(timestamp) ORDER BY DATE(timestamp)"
                    
                    df = pd.read_sql_query(query, conn, params=params)
                    cache_data = df
                
                # Generate the report for display
                report_result = self.analytics.generate_report(
                    report_type=report_type,
                    proxy_type=proxy_type,
                    days=days,
                    output_format="console"  # We'll handle the display ourselves
                )
                
                # Update UI in the main thread
                self.frame.after(0, lambda: self._update_report_display(report_type, cache_data))
                
            except Exception as e:
                self.frame.after(0, lambda: messagebox.showerror("Error", f"Failed to generate report: {str(e)}"))
            finally:
                self.frame.after(0, lambda: loading.destroy())
        
        # Start the thread
        threading.Thread(target=run_report, daemon=True).start()
    
    def _update_report_display(self, report_type, df=None):
        """Update the display with the generated report"""
        # Clear previous content
        for widget in self.report_frame.winfo_children():
            widget.destroy()
            
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
        
        # Get database stats
        try:
            conn = self.analytics._init_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM proxy_checks")
            total_checks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT proxy) FROM proxy_stats")
            total_proxies = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM proxy_checks WHERE success = 1")
            successful_checks = cursor.fetchone()[0]
            
            if total_checks > 0:
                success_rate = (successful_checks / total_checks) * 100
            else:
                success_rate = 0
                
            conn.close()
            
            # Display stats in header
            header_frame = ctk.CTkFrame(self.report_frame)
            header_frame.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(
                header_frame,
                text=f"Database Statistics: {total_proxies} proxies, {total_checks} checks, {success_rate:.1f}% success rate",
                font=("Segoe UI", 12, "bold")
            ).pack(pady=5)
            
        except Exception as e:
            print(f"Error getting database stats: {e}")
        
        # Add the appropriate content based on report type
        if report_type == "summary":
            self._display_summary_report()
        elif report_type == "trend":
            self._display_trend_report(df)
        elif report_type == "top_proxies":
            self._display_top_proxies_report()
    
    def _display_summary_report(self):
        """Display the summary report"""
        try:
            # Get data
            stats = self.analytics.get_proxy_stats()
            
            # Create a frame for the table
            table_frame = ctk.CTkFrame(self.report_frame)
            table_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Create the table
            columns = ["Proxy Type", "Count", "Success %", "Avg Response", "Score"]
            
            # Create the table header
            for i, col in enumerate(columns):
                header = ctk.CTkLabel(
                    table_frame,
                    text=col,
                    font=("Segoe UI", 12, "bold")
                )
                header.grid(row=0, column=i, padx=5, pady=5, sticky="w")
            
            # Group stats by proxy type
            proxy_types = {}
            for stat in stats:
                ptype = stat["proxy_type"]
                if ptype not in proxy_types:
                    proxy_types[ptype] = []
                proxy_types[ptype].append(stat)
            
            # Display aggregated stats
            row = 1
            for ptype, pstats in proxy_types.items():
                count = len(pstats)
                success_pct = sum(s["uptime_percentage"] for s in pstats) / count if count else 0
                avg_response = sum(s["avg_response_time"] for s in pstats) / count if count else 0
                avg_score = sum(s["reliability_score"] for s in pstats) / count if count else 0
                
                type_label = ctk.CTkLabel(table_frame, text=ptype.upper())
                type_label.grid(row=row, column=0, padx=5, pady=2, sticky="w")
                
                count_label = ctk.CTkLabel(table_frame, text=str(count))
                count_label.grid(row=row, column=1, padx=5, pady=2, sticky="w")
                
                success_label = ctk.CTkLabel(table_frame, text=f"{success_pct:.1f}%")
                success_label.grid(row=row, column=2, padx=5, pady=2, sticky="w")
                
                resp_label = ctk.CTkLabel(table_frame, text=f"{avg_response:.3f}s")
                resp_label.grid(row=row, column=3, padx=5, pady=2, sticky="w")
                
                score_label = ctk.CTkLabel(table_frame, text=f"{avg_score:.3f}")
                score_label.grid(row=row, column=4, padx=5, pady=2, sticky="w")
                
                row += 1
            
            # Create chart for the Chart tab
            self._create_summary_chart(proxy_types)
            
        except Exception as e:
            error = ctk.CTkLabel(
                self.report_frame,
                text=f"Error displaying summary report: {str(e)}",
                text_color="red"
            )
            error.pack(pady=20)
    
    def _create_summary_chart(self, proxy_types):
        """Create a summary chart"""
        try:
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Prepare data
            types = list(proxy_types.keys())
            counts = [len(proxy_types[t]) for t in types]
            success_rates = [
                sum(s["uptime_percentage"] for s in proxy_types[t]) / len(proxy_types[t])
                if len(proxy_types[t]) else 0
                for t in types
            ]
            
            # Create bar chart
            x = range(len(types))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], counts, width, label='Proxy Count')
            ax2 = ax.twinx()
            ax2.bar([i + width/2 for i in x], success_rates, width, color='green', alpha=0.7, label='Success Rate (%)')
            
            # Labels and legend
            ax.set_xlabel('Proxy Type')
            ax.set_ylabel('Count')
            ax2.set_ylabel('Success Rate (%)')
            ax.set_title('Proxy Count and Success Rate by Type')
            ax.set_xticks(x)
            ax.set_xticklabels([t.upper() for t in types])
            
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            
            # Add to chart frame
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            error = ctk.CTkLabel(
                self.chart_frame,
                text=f"Error creating chart: {str(e)}",
                text_color="red"
            )
            error.pack(pady=20)
    
    def _display_trend_report(self, df):
        """Display the trend report"""
        try:
            if df is None or df.empty:
                no_data = ctk.CTkLabel(
                    self.report_frame,
                    text="No trend data available for the selected period",
                    font=("Segoe UI", 14)
                )
                no_data.pack(pady=50)
                return
                
            # Create a frame for the table
            table_frame = ctk.CTkFrame(self.report_frame)
            table_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Create the table
            columns = ["Date", "Total Checks", "Successes", "Failures", "Success Rate", "Avg Response"]
            
            # Create the table header
            for i, col in enumerate(columns):
                header = ctk.CTkLabel(
                    table_frame,
                    text=col,
                    font=("Segoe UI", 12, "bold")
                )
                header.grid(row=0, column=i, padx=5, pady=5, sticky="w")
            
            # Display data rows
            for i, (_, row) in enumerate(df.iterrows(), 1):
                ctk.CTkLabel(table_frame, text=str(row['date'])).grid(
                    row=i, column=0, padx=5, pady=2, sticky="w"
                )
                ctk.CTkLabel(table_frame, text=str(row['total_checks'])).grid(
                    row=i, column=1, padx=5, pady=2, sticky="w"
                )
                ctk.CTkLabel(table_frame, text=str(row['successes'])).grid(
                    row=i, column=2, padx=5, pady=2, sticky="w"
                )
                ctk.CTkLabel(table_frame, text=str(row['failures'])).grid(
                    row=i, column=3, padx=5, pady=2, sticky="w"
                )
                ctk.CTkLabel(table_frame, text=f"{row['success_rate']:.1f}%").grid(
                    row=i, column=4, padx=5, pady=2, sticky="w"
                )
                ctk.CTkLabel(table_frame, text=f"{row['avg_response_time']:.3f}s").grid(
                    row=i, column=5, padx=5, pady=2, sticky="w"
                )
            
            # Create chart for the Chart tab
            self._create_trend_chart(df)
            
        except Exception as e:
            error = ctk.CTkLabel(
                self.report_frame,
                text=f"Error displaying trend report: {str(e)}",
                text_color="red"
            )
            error.pack(pady=20)
    
    def _create_trend_chart(self, df):
        """Create a trend chart"""
        try:
            # Create matplotlib figure
            fig = plt.figure(figsize=(10, 6))
            
            # Success rate trend
            ax1 = plt.subplot(121)
            ax1.plot(df['date'], df['success_rate'], 'g-o')
            ax1.set_title('Success Rate Trend')
            ax1.set_ylabel('Success Rate (%)')
            ax1.set_xlabel('Date')
            ax1.grid(True, alpha=0.3)
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            
            # Response time trend
            ax2 = plt.subplot(122)
            ax2.plot(df['date'], df['avg_response_time'], 'b-o')
            ax2.set_title('Response Time Trend')
            ax2.set_ylabel('Avg. Response Time (s)')
            ax2.set_xlabel('Date')
            ax2.grid(True, alpha=0.3)
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            # Add to chart frame
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            error = ctk.CTkLabel(
                self.chart_frame,
                text=f"Error creating chart: {str(e)}",
                text_color="red"
            )
            error.pack(pady=20)
    
    def _display_top_proxies_report(self):
        """Display the top proxies report"""
        try:
            proxy_type = self.proxy_type.get()
            
            # Get top proxies
            stats = self.analytics.get_proxy_stats(
                proxy_type=proxy_type,
                min_checks=3,
                min_uptime=10.0,
                limit=20
            )
            
            if not stats:
                no_data = ctk.CTkLabel(
                    self.report_frame,
                    text="No proxy data available with the selected criteria",
                    font=("Segoe UI", 14)
                )
                no_data.pack(pady=50)
                return
            
            # Create a frame for the table with scrollbar
            container = ctk.CTkFrame(self.report_frame)
            container.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Add scrollbar
            canvas = tk.Canvas(container)
            scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Create the table
            columns = ["Proxy", "Type", "Success", "Failure", "Uptime %", "Response", "Score"]
            
            # Create the table header
            for i, col in enumerate(columns):
                header = ttk.Label(
                    scrollable_frame,
                    text=col,
                    font=("Segoe UI", 10, "bold")
                )
                header.grid(row=0, column=i, padx=5, pady=5, sticky="w")
            
            # Display data rows
            for i, stat in enumerate(stats, 1):
                ttk.Label(scrollable_frame, text=stat['proxy']).grid(
                    row=i, column=0, padx=5, pady=2, sticky="w"
                )
                ttk.Label(scrollable_frame, text=stat['proxy_type']).grid(
                    row=i, column=1, padx=5, pady=2, sticky="w"
                )
                ttk.Label(scrollable_frame, text=str(stat['success_count'])).grid(
                    row=i, column=2, padx=5, pady=2, sticky="w"
                )
                ttk.Label(scrollable_frame, text=str(stat['failure_count'])).grid(
                    row=i, column=3, padx=5, pady=2, sticky="w"
                )
                ttk.Label(scrollable_frame, text=f"{stat['uptime_percentage']:.1f}%").grid(
                    row=i, column=4, padx=5, pady=2, sticky="w"
                )
                ttk.Label(scrollable_frame, text=f"{stat['avg_response_time']:.3f}s").grid(
                    row=i, column=5, padx=5, pady=2, sticky="w"
                )
                ttk.Label(scrollable_frame, text=f"{stat['reliability_score']:.3f}").grid(
                    row=i, column=6, padx=5, pady=2, sticky="w"
                )
            
            # Create chart for the Chart tab
            self._create_top_proxies_chart(stats[:10])  # Top 10 for chart
            
        except Exception as e:
            error = ctk.CTkLabel(
                self.report_frame,
                text=f"Error displaying top proxies report: {str(e)}",
                text_color="red"
            )
            error.pack(pady=20)
    
    def _create_top_proxies_chart(self, stats):
        """Create a chart for top proxies"""
        try:
            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Prepare data
            proxies = [s['proxy'][:15] + '...' if len(s['proxy']) > 15 else s['proxy'] for s in stats]
            uptime = [s['uptime_percentage'] for s in stats]
            response = [s['avg_response_time'] * 1000 for s in stats]  # Convert to ms
            
            # Create bar chart
            x = range(len(proxies))
            width = 0.35
            
            ax.bar([i - width/2 for i in x], uptime, width, label='Uptime %')
            ax2 = ax.twinx()
            ax2.bar([i + width/2 for i in x], response, width, color='orange', alpha=0.7, label='Response (ms)')
            
            # Labels and legend
            ax.set_xlabel('Proxy')
            ax.set_ylabel('Uptime %')
            ax2.set_ylabel('Response Time (ms)')
            ax.set_title('Top Proxies by Reliability')
            ax.set_xticks(x)
            ax.set_xticklabels(proxies, rotation=45, ha='right')
            
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
            
            plt.tight_layout()
            
            # Add to chart frame
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            error = ctk.CTkLabel(
                self.chart_frame,
                text=f"Error creating chart: {str(e)}",
                text_color="red"
            )
            error.pack(pady=20)
    
    def _export_data(self):
        """Export analytics data to CSV"""
        if not HAS_ANALYTICS:
            messagebox.showerror("Error", "Analytics module not available")
            return
            
        try:
            report_type = self.report_type.get()
            proxy_type = self.proxy_type.get()
            days = int(self.days.get())
            
            result = self.analytics.generate_report(
                report_type=report_type,
                proxy_type=proxy_type,
                days=days,
                output_format="csv"
            )
            
            messagebox.showinfo("Export Complete", f"Data exported to:\n{result}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {str(e)}")
    
    def _cleanup_data(self):
        """Clean up old analytics data"""
        if not HAS_ANALYTICS:
            messagebox.showerror("Error", "Analytics module not available")
            return
            
        try:
            days = int(messagebox.askstring(
                "Cleanup Data",
                "Delete data older than how many days?",
                initialvalue="30"
            ))
            
            if days < 1:
                messagebox.showwarning("Invalid Input", "Days must be at least 1")
                return
                
            count = self.analytics.cleanup(days=days)
            messagebox.showinfo("Cleanup Complete", f"Removed {count} old records")
            
        except Exception as e:
            if str(e):  # Not a cancel operation
                messagebox.showerror("Error", f"Failed to clean up data: {str(e)}")
