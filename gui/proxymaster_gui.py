#!/usr/bin/env python3
"""
ProxyMaster GUI - Graphical interface for proxy scraping and validation
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import queue
import time
import json
from datetime import datetime, timedelta
import signal
import subprocess
import requests
import importlib

# Check for required packages and install if missing
try:
    from ttkthemes import ThemedTk
    import customtkinter as ctk
except ImportError:
    import subprocess
    print("Installing required GUI packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ttkthemes", "customtkinter"])
    from ttkthemes import ThemedTk
    import customtkinter as ctk

# Import ProxyMaster functionality
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from proxymaster import scrape_proxies, validate_proxies, Proxy
except ImportError:
    print("Error: ProxyMaster module not found. Please make sure you're running this from the ProxyMaster directory.")
    sys.exit(1)

# Set appearance mode and default color theme
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

# Default settings
DEFAULT_TIMEOUT = 10
DEFAULT_TEST_SITES = ["icanhazip.com", "api.ipify.org", "ifconfig.me"]
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class RedirectText:
    """Class to redirect console output to a tkinter Text widget"""
    
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.queue = queue.Queue()
        self.update_me()
    
    def write(self, string):
        self.queue.put(string)
    
    def flush(self):
        pass
    
    def update_me(self):
        try:
            while 1:
                self.text_widget.configure(state=tk.NORMAL)
                self.text_widget.insert(tk.END, self.queue.get_nowait())
                self.text_widget.see(tk.END)
                self.text_widget.configure(state=tk.DISABLED)
        except queue.Empty:
            pass
        self.text_widget.after(100, self.update_me)


class ProxyMasterGUI(ctk.CTk):
    """Main GUI class for ProxyMaster"""
    def __init__(self):
        super().__init__()
        # Configure window
        self.title("ProxyMaster 2.0 - by cyb3r_vishal (community DevKitX)")
        self.geometry("1000x700")
        self.minsize(800, 600)
        
        # Variables
        self.proxy_type = tk.StringVar(value="http")
        self.timeout = tk.IntVar(value=DEFAULT_TIMEOUT)
        self.min_success_rate = tk.DoubleVar(value=0.25)
        self.test_sites = tk.StringVar(value=",".join(DEFAULT_TEST_SITES))
        self.input_file = tk.StringVar()
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="Ready")
        self.working_thread = None
        self.monitor_thread = None
        self.rotator_thread = None
        self.rotator_process = None
        
        # Main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tab control
        self.tab_control = ttk.Notebook(self.main_frame)
          # Create tabs
        self.scraper_tab = ctk.CTkFrame(self.tab_control)
        self.monitor_tab = ctk.CTkFrame(self.tab_control)
        self.geo_tab = ctk.CTkFrame(self.tab_control)
        self.rotator_tab = ctk.CTkFrame(self.tab_control)
        self.analytics_tab = ctk.CTkFrame(self.tab_control)
        
        # Add tabs to notebook
        self.tab_control.add(self.scraper_tab, text="Scraper & Validator")
        self.tab_control.add(self.monitor_tab, text="Proxy Monitor")
        self.tab_control.add(self.geo_tab, text="Geolocation")
        self.tab_control.add(self.rotator_tab, text="Proxy Rotator")
        self.tab_control.add(self.analytics_tab, text="Analytics")
        
        self.tab_control.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        # Initialize each tab
        self.setup_scraper_tab()
        self.setup_monitor_tab()
        self.setup_geo_tab()
        self.setup_rotator_tab()
        self.setup_analytics_tab()
        
        # Status bar
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.status_label = ctk.CTkLabel(self.status_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.progress_bar = ctk.CTkProgressBar(self.status_frame)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.progress_bar.set(0)
        
        # Footer with creator information
        self.footer_frame = ctk.CTkFrame(self)
        self.footer_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        creator_label = ctk.CTkLabel(
            self.footer_frame, 
            text="Created by: cyb3r_vishal | community DevKitX",
            font=("Arial", 10),
            text_color="gray60"
        )
        creator_label.pack(side=tk.LEFT, padx=5)
        
        # About button
        about_btn = ctk.CTkButton(
            self.footer_frame, 
            text="About", 
            command=self.show_about,
            width=80,
            height=25,
            font=("Arial", 10)
        )
        about_btn.pack(side=tk.RIGHT, padx=5)        # Initialize console_text as None, we'll create it in setup_scraper_tab
        self.console_text = None
        
        # Save old stdout for later
        self.old_stdout = sys.stdout
        
    def setup_scraper_tab(self):
        """Set up the scraper and validator tab"""
        # Create left panel (settings)
        left_frame = ctk.CTkFrame(self.scraper_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # Settings section
        settings_frame = ctk.CTkFrame(left_frame)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Settings", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Proxy type
        proxy_frame = ctk.CTkFrame(settings_frame)
        proxy_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(proxy_frame, text="Proxy Type:").pack(side=tk.LEFT, padx=5)
        
        proxy_options = ["http", "https", "socks4", "socks5"]
        for option in proxy_options:
            rb = ctk.CTkRadioButton(proxy_frame, text=option, variable=self.proxy_type, value=option)
            rb.pack(side=tk.LEFT, padx=5)
        
        # Timeout
        timeout_frame = ctk.CTkFrame(settings_frame)
        timeout_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(timeout_frame, text="Timeout (seconds):").pack(side=tk.LEFT, padx=5)
        timeout_slider = ctk.CTkSlider(timeout_frame, from_=1, to=30, number_of_steps=29, variable=self.timeout)
        timeout_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ctk.CTkLabel(timeout_frame, textvariable=self.timeout).pack(side=tk.LEFT, padx=5)
        
        # Success rate
        success_frame = ctk.CTkFrame(settings_frame)
        success_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(success_frame, text="Min Success Rate:").pack(side=tk.LEFT, padx=5)
        success_slider = ctk.CTkSlider(success_frame, from_=0.0, to=1.0, number_of_steps=20, variable=self.min_success_rate)
        success_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Format success rate value to 2 decimal places
        def format_success_rate(*args):
            success_label.configure(text=f"{self.min_success_rate.get():.2f}")
        
        self.min_success_rate.trace_add("write", format_success_rate)
        success_label = ctk.CTkLabel(success_frame, text=f"{self.min_success_rate.get():.2f}")
        success_label.pack(side=tk.LEFT, padx=5)
        
        # Test sites
        sites_frame = ctk.CTkFrame(settings_frame)
        sites_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(sites_frame, text="Test Sites:").pack(side=tk.LEFT, padx=5)
        sites_entry = ctk.CTkEntry(sites_frame, textvariable=self.test_sites)
        sites_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Input file section
        input_frame = ctk.CTkFrame(left_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(input_frame, text="Input File (Optional)", font=("Arial", 14, "bold")).pack(pady=5)
        
        file_frame = ctk.CTkFrame(input_frame)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        input_entry = ctk.CTkEntry(file_frame, textvariable=self.input_file)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = ctk.CTkButton(file_frame, text="Browse", command=self.browse_input_file)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        actions_frame = ctk.CTkFrame(left_frame)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        scrape_btn = ctk.CTkButton(actions_frame, text="Scrape Only", command=self.scrape_only)
        scrape_btn.pack(fill=tk.X, padx=5, pady=5)
        
        validate_btn = ctk.CTkButton(actions_frame, text="Validate Only", command=self.validate_only)
        validate_btn.pack(fill=tk.X, padx=5, pady=5)
        
        scrape_validate_btn = ctk.CTkButton(actions_frame, text="Scrape & Validate", 
                                           command=self.scrape_and_validate,
                                           fg_color="#28a745")
        scrape_validate_btn.pack(fill=tk.X, padx=5, pady=5)
        
        stop_btn = ctk.CTkButton(actions_frame, text="Stop", command=self.stop_operation,
                                fg_color="#dc3545")
        stop_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Create right panel (console and results)
        right_frame = ctk.CTkFrame(self.scraper_tab)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Console output
        console_frame = ctk.CTkFrame(right_frame)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(console_frame, text="Console Output", font=("Arial", 14, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        console_scroll = ctk.CTkScrollbar(console_frame)
        console_scroll.pack(side=tk.RIGHT, fill=tk.Y)
          # Create the console text widget
        self.console_text = tk.Text(console_frame, height=20, yscrollcommand=console_scroll.set,
                                   bg="#2b2b2b", fg="#f8f8f2", font=("Consolas", 10))
        self.console_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console_text.configure(state=tk.DISABLED)
        
        # Create redirector and redirect stdout
        self.console_redirect = RedirectText(self.console_text)
        sys.stdout = self.console_redirect
        
        console_scroll.configure(command=self.console_text.yview)
    
    def setup_monitor_tab(self):
        """Set up the monitor tab"""
        # Create left panel (settings)
        left_frame = ctk.CTkFrame(self.monitor_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # Settings section
        settings_frame = ctk.CTkFrame(left_frame)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Monitor Settings", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Proxy type
        proxy_frame = ctk.CTkFrame(settings_frame)
        proxy_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(proxy_frame, text="Proxy Type:").pack(side=tk.LEFT, padx=5)
        
        self.monitor_proxy_type = tk.StringVar(value="http")
        proxy_options = ["http", "https", "socks4", "socks5"]
        for option in proxy_options:
            rb = ctk.CTkRadioButton(proxy_frame, text=option, variable=self.monitor_proxy_type, value=option)
            rb.pack(side=tk.LEFT, padx=5)
        
        # Input file
        file_frame = ctk.CTkFrame(settings_frame)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(file_frame, text="Proxy File:").pack(side=tk.LEFT, padx=5)
        
        self.monitor_input_file = tk.StringVar()
        input_entry = ctk.CTkEntry(file_frame, textvariable=self.monitor_input_file)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = ctk.CTkButton(file_frame, text="Browse", 
                                  command=lambda: self.browse_file(self.monitor_input_file))
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Check interval
        interval_frame = ctk.CTkFrame(settings_frame)
        interval_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(interval_frame, text="Check Interval (minutes):").pack(side=tk.LEFT, padx=5)
        
        self.check_interval = tk.IntVar(value=60)
        interval_slider = ctk.CTkSlider(interval_frame, from_=5, to=120, number_of_steps=23,
                                      variable=self.check_interval)
        interval_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ctk.CTkLabel(interval_frame, textvariable=self.check_interval).pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        actions_frame = ctk.CTkFrame(left_frame)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.monitor_once = tk.BooleanVar(value=False)
        once_check = ctk.CTkCheckBox(actions_frame, text="Run once (don't monitor continuously)", 
                                   variable=self.monitor_once)
        once_check.pack(fill=tk.X, padx=5, pady=5)
        
        start_btn = ctk.CTkButton(actions_frame, text="Start Monitor", 
                                command=self.start_monitor,
                                fg_color="#28a745")
        start_btn.pack(fill=tk.X, padx=5, pady=5)
        
        stop_btn = ctk.CTkButton(actions_frame, text="Stop Monitor", 
                               command=self.stop_monitor,
                               fg_color="#dc3545")
        stop_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Create right panel (monitor status and history)
        right_frame = ctk.CTkFrame(self.monitor_tab)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status section
        status_frame = ctk.CTkFrame(right_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(status_frame, text="Monitor Status", font=("Arial", 14, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        self.monitor_status = tk.StringVar(value="Not Running")
        self.next_check = tk.StringVar(value="N/A")
        self.last_check = tk.StringVar(value="Never")
        self.proxies_found = tk.StringVar(value="0")
        
        info_frame = ctk.CTkFrame(status_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a grid of labels for status information
        status_grid = [
            ("Status:", self.monitor_status),
            ("Next Check:", self.next_check),
            ("Last Check:", self.last_check),
            ("Proxies Found:", self.proxies_found)
        ]
        
        for i, (label_text, var) in enumerate(status_grid):
            ctk.CTkLabel(info_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            ctk.CTkLabel(info_frame, textvariable=var).grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
        
        # History section
        history_frame = ctk.CTkFrame(right_frame)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(history_frame, text="Check History", font=("Arial", 14, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        # Create a notebook with tabs for different views
        history_notebook = ttk.Notebook(history_frame)
        history_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # List view tab
        list_frame = ctk.CTkFrame(history_notebook)
        history_notebook.add(list_frame, text="List View")
        
        # Create a treeview for the history list
        columns = ("datetime", "checked", "valid", "rate")
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Define column headings
        self.history_tree.heading("datetime", text="Date & Time")
        self.history_tree.heading("checked", text="Checked")
        self.history_tree.heading("valid", text="Valid")
        self.history_tree.heading("rate", text="Success Rate")
        
        # Set column widths
        self.history_tree.column("datetime", width=150)
        self.history_tree.column("checked", width=80)
        self.history_tree.column("valid", width=80)
        self.history_tree.column("rate", width=100)
        
        # Add a scrollbar
        history_scroll = ctk.CTkScrollbar(list_frame, command=self.history_tree.yview)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_tree.configure(yscrollcommand=history_scroll.set)
        self.history_tree.pack(fill=tk.BOTH, expand=True)
        
        # Load history data if available
        self.load_monitor_history()
    
    def setup_geo_tab(self):
        """Set up the geolocation tab"""
        # Create left panel (settings)
        left_frame = ctk.CTkFrame(self.geo_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # Settings section
        settings_frame = ctk.CTkFrame(left_frame)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Geolocation Settings", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Input file
        input_frame = ctk.CTkFrame(settings_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(input_frame, text="Proxy File:").pack(side=tk.LEFT, padx=5)
        
        self.geo_input_file = tk.StringVar()
        input_entry = ctk.CTkEntry(input_frame, textvariable=self.geo_input_file)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = ctk.CTkButton(input_frame, text="Browse", 
                                 command=lambda: self.browse_file(self.geo_input_file))
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Output file
        output_frame = ctk.CTkFrame(settings_frame)
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(output_frame, text="Output File:").pack(side=tk.LEFT, padx=5)
        
        self.geo_output_file = tk.StringVar()
        output_entry = ctk.CTkEntry(output_frame, textvariable=self.geo_output_file)
        output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = ctk.CTkButton(output_frame, text="Browse", 
                                 command=lambda: self.save_file(self.geo_output_file))
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Action buttons
        actions_frame = ctk.CTkFrame(left_frame)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        start_btn = ctk.CTkButton(actions_frame, text="Add Geolocation Data", 
                                command=self.start_geo,
                                fg_color="#28a745")
        start_btn.pack(fill=tk.X, padx=5, pady=5)
        
        stop_btn = ctk.CTkButton(actions_frame, text="Stop", 
                               command=self.stop_geo,
                               fg_color="#dc3545")
        stop_btn.pack(fill=tk.X, padx=5, pady=5)
        
        view_btn = ctk.CTkButton(actions_frame, text="View Results", 
                               command=self.view_geo_results)
        view_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Create right panel (geolocation results)
        right_frame = ctk.CTkFrame(self.geo_tab)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results notebook
        results_notebook = ttk.Notebook(right_frame)
        results_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Table view tab
        table_frame = ctk.CTkFrame(results_notebook)
        results_notebook.add(table_frame, text="Table View")
        
        # Create a treeview for the geo results
        columns = ("proxy", "country", "city", "isp", "anonymity")
        self.geo_tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        # Define column headings
        self.geo_tree.heading("proxy", text="Proxy")
        self.geo_tree.heading("country", text="Country")
        self.geo_tree.heading("city", text="City")
        self.geo_tree.heading("isp", text="ISP")
        self.geo_tree.heading("anonymity", text="Anonymity")
        
        # Set column widths
        self.geo_tree.column("proxy", width=150)
        self.geo_tree.column("country", width=100)
        self.geo_tree.column("city", width=100)
        self.geo_tree.column("isp", width=150)
        self.geo_tree.column("anonymity", width=120)
        
        # Add a scrollbar
        geo_scroll = ctk.CTkScrollbar(table_frame, command=self.geo_tree.yview)
        geo_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.geo_tree.configure(yscrollcommand=geo_scroll.set)
        self.geo_tree.pack(fill=tk.BOTH, expand=True)
        
        # Stats view tab
        stats_frame = ctk.CTkFrame(results_notebook)
        results_notebook.add(stats_frame, text="Statistics")
        
        # Create frames for statistics
        country_frame = ctk.CTkFrame(stats_frame)
        country_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(country_frame, text="Country Distribution", font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        # Country stats treeview
        columns = ("country", "count", "percentage")
        self.country_tree = ttk.Treeview(country_frame, columns=columns, show="headings", height=5)
        
        self.country_tree.heading("country", text="Country")
        self.country_tree.heading("count", text="Count")
        self.country_tree.heading("percentage", text="Percentage")
        
        self.country_tree.column("country", width=150)
        self.country_tree.column("count", width=80, anchor=tk.CENTER)
        self.country_tree.column("percentage", width=100, anchor=tk.CENTER)
        
        country_scroll = ctk.CTkScrollbar(country_frame, command=self.country_tree.yview)
        country_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.country_tree.configure(yscrollcommand=country_scroll.set)
        self.country_tree.pack(fill=tk.BOTH, expand=True)
        
        # Anonymity stats
        anon_frame = ctk.CTkFrame(stats_frame)
        anon_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(anon_frame, text="Anonymity Distribution", font=("Arial", 12, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        # Anonymity stats treeview
        columns = ("level", "count", "percentage")
        self.anon_tree = ttk.Treeview(anon_frame, columns=columns, show="headings", height=5)
        
        self.anon_tree.heading("level", text="Anonymity Level")
        self.anon_tree.heading("count", text="Count")
        self.anon_tree.heading("percentage", text="Percentage")
        
        self.anon_tree.column("level", width=150)
        self.anon_tree.column("count", width=80, anchor=tk.CENTER)
        self.anon_tree.column("percentage", width=100, anchor=tk.CENTER)
        
        anon_scroll = ctk.CTkScrollbar(anon_frame, command=self.anon_tree.yview)
        anon_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.anon_tree.configure(yscrollcommand=anon_scroll.set)
        self.anon_tree.pack(fill=tk.BOTH, expand=True)
    
    def setup_rotator_tab(self):
        """Set up the proxy rotator tab"""
        # Create left panel (settings)
        left_frame = ctk.CTkFrame(self.rotator_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # Settings section
        settings_frame = ctk.CTkFrame(left_frame)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(settings_frame, text="Rotator Settings", font=("Arial", 14, "bold")).pack(pady=5)
        
        # Input file
        input_frame = ctk.CTkFrame(settings_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(input_frame, text="Proxy File:").pack(side=tk.LEFT, padx=5)
        
        self.rotator_input_file = tk.StringVar()
        input_entry = ctk.CTkEntry(input_frame, textvariable=self.rotator_input_file)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = ctk.CTkButton(input_frame, text="Browse", 
                                 command=lambda: self.browse_file(self.rotator_input_file))
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Port
        port_frame = ctk.CTkFrame(settings_frame)
        port_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(port_frame, text="Port:").pack(side=tk.LEFT, padx=5)
        
        self.rotator_port = tk.IntVar(value=8080)
        port_entry = ctk.CTkEntry(port_frame, textvariable=self.rotator_port, width=80)
        port_entry.pack(side=tk.LEFT, padx=5)
        
        # Rotation count
        rotation_frame = ctk.CTkFrame(settings_frame)
        rotation_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(rotation_frame, text="Rotation Count:").pack(side=tk.LEFT, padx=5)
        
        self.rotation_count = tk.IntVar(value=20)
        count_slider = ctk.CTkSlider(rotation_frame, from_=1, to=50, number_of_steps=49,
                                   variable=self.rotation_count)
        count_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ctk.CTkLabel(rotation_frame, textvariable=self.rotation_count).pack(side=tk.LEFT, padx=5)
        
        # Timeout
        timeout_frame = ctk.CTkFrame(settings_frame)
        timeout_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(timeout_frame, text="Timeout (seconds):").pack(side=tk.LEFT, padx=5)
        
        self.rotator_timeout = tk.IntVar(value=10)
        timeout_slider = ctk.CTkSlider(timeout_frame, from_=1, to=30, number_of_steps=29,
                                     variable=self.rotator_timeout)
        timeout_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ctk.CTkLabel(timeout_frame, textvariable=self.rotator_timeout).pack(side=tk.LEFT, padx=5)
        
        # Test option
        test_frame = ctk.CTkFrame(settings_frame)
        test_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.skip_testing = tk.BooleanVar(value=False)
        test_check = ctk.CTkCheckBox(test_frame, text="Skip proxy testing", variable=self.skip_testing)
        test_check.pack(fill=tk.X, padx=5, pady=5)
        
        # Action buttons
        actions_frame = ctk.CTkFrame(left_frame)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        start_btn = ctk.CTkButton(actions_frame, text="Start Proxy Rotator", 
                                command=self.start_rotator,
                                fg_color="#28a745")
        start_btn.pack(fill=tk.X, padx=5, pady=5)
        
        stop_btn = ctk.CTkButton(actions_frame, text="Stop Rotator", 
                               command=self.stop_rotator,
                               fg_color="#dc3545")
        stop_btn.pack(fill=tk.X, padx=5, pady=5)
        
        test_btn = ctk.CTkButton(actions_frame, text="Test Connection", 
                               command=self.test_rotator_connection)
        test_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Create right panel (rotator status and proxy stats)
        right_frame = ctk.CTkFrame(self.rotator_tab)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Status section
        status_frame = ctk.CTkFrame(right_frame)
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(status_frame, text="Rotator Status", font=("Arial", 14, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        self.rotator_status = tk.StringVar(value="Not Running")
        self.proxy_count = tk.StringVar(value="0")
        self.current_proxy = tk.StringVar(value="None")
        self.success_requests = tk.StringVar(value="0")
        self.throughput = tk.StringVar(value="0 req/s")
        
        info_frame = ctk.CTkFrame(status_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a grid of labels for status information
        status_grid = [
            ("Status:", self.rotator_status),
            ("Proxy Count:", self.proxy_count),
            ("Current Proxy:", self.current_proxy),
            ("Successful Requests:", self.success_requests),
            ("Throughput:", self.throughput)
        ]
        
        for i, (label_text, var) in enumerate(status_grid):
            ctk.CTkLabel(info_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            ctk.CTkLabel(info_frame, textvariable=var).grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
        
        # Connection info
        connection_frame = ctk.CTkFrame(right_frame)
        connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ctk.CTkLabel(connection_frame, text="Connection Information", font=("Arial", 14, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        info_text = """
        To use this proxy rotator in your applications:
        
        Proxy URL: http://localhost:{port}
        
        Example with curl:
        curl -x http://localhost:{port} https://icanhazip.com
        
        Example with Python requests:
        import requests
        proxies = {{"http": "http://localhost:{port}", "https": "http://localhost:{port}"}}
        response = requests.get("https://icanhazip.com", proxies=proxies)
        """.format(port=self.rotator_port.get())
        
        # Add a text widget with connection info
        connection_text = ctk.CTkTextbox(connection_frame, height=150)
        connection_text.pack(fill=tk.X, padx=5, pady=5)
        connection_text.insert(tk.END, info_text)
        connection_text.configure(state=tk.DISABLED)
        
        # Update connection info when port changes
        def update_connection_info(*args):
            connection_text.configure(state=tk.NORMAL)
            connection_text.delete(1.0, tk.END)
            connection_text.insert(tk.END, info_text.format(port=self.rotator_port.get()))
            connection_text.configure(state=tk.DISABLED)
        
        self.rotator_port.trace_add("write", update_connection_info)
        
        # Proxy performance
        performance_frame = ctk.CTkFrame(right_frame)
        performance_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(performance_frame, text="Proxy Performance", font=("Arial", 14, "bold")).pack(anchor=tk.W, padx=5, pady=5)
        
        # Create a treeview for proxy performance
        columns = ("proxy", "success", "fail", "rate")
        self.proxy_tree = ttk.Treeview(performance_frame, columns=columns, show="headings")
        
        # Define column headings
        self.proxy_tree.heading("proxy", text="Proxy")
        self.proxy_tree.heading("success", text="Success")
        self.proxy_tree.heading("fail", text="Fails")
        self.proxy_tree.heading("rate", text="Success Rate")
        
        # Set column widths
        self.proxy_tree.column("proxy", width=150)
        self.proxy_tree.column("success", width=80, anchor=tk.CENTER)
        self.proxy_tree.column("fail", width=80, anchor=tk.CENTER)
        self.proxy_tree.column("rate", width=100, anchor=tk.CENTER)
        
        # Add a scrollbar
        proxy_scroll = ctk.CTkScrollbar(performance_frame, command=self.proxy_tree.yview)
        proxy_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.proxy_tree.configure(yscrollcommand=proxy_scroll.set)
        self.proxy_tree.pack(fill=tk.BOTH, expand=True)
    
    def setup_analytics_tab(self):
        """Set up the analytics tab using the AnalyticsTab class"""
        try:
            # Dynamically import the analytics_tab module
            from gui.analytics_tab import AnalyticsTab, HAS_ANALYTICS
            
            # Create an instance of AnalyticsTab, passing the tab control and this instance
            self.analytics_controller = AnalyticsTab(self.analytics_tab, self)
            
            # If analytics module is not available, add a console for output
            if not HAS_ANALYTICS:
                frame = ctk.CTkFrame(self.analytics_tab)
                frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                warning = ctk.CTkLabel(
                    frame,
                    text="Analytics module not fully available.\nRun 'pip install pandas matplotlib rich' to enable all features.",
                    font=("Segoe UI", 14),
                    text_color="orange"
                )
                warning.pack(pady=10)
                
                # Add a console for output
                console_frame = ctk.CTkFrame(frame)
                console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                self.analytics_console = ctk.CTkTextbox(console_frame, height=400)
                self.analytics_console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                self.analytics_console.insert(tk.END, "Analytics functionality limited. Install required packages for full features.\n")
                self.analytics_console.configure(state=tk.DISABLED)
        
        except Exception as e:
            # Create a basic tab with error message if there's an issue
            error_frame = ctk.CTkFrame(self.analytics_tab)
            error_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            error_label = ctk.CTkLabel(
                error_frame,
                text=f"Error setting up analytics tab:\n{str(e)}",
                font=("Segoe UI", 14),
                text_color="red"
            )
            error_label.pack(pady=20)
            
            # Add button to install requirements
            install_btn = ctk.CTkButton(
                error_frame,
                text="Install Requirements",
                command=self._install_analytics_requirements
            )
            install_btn.pack(pady=10)
    
    def _install_analytics_requirements(self):
        """Install requirements for analytics"""
        try:
            self.status_var.set("Installing analytics requirements...")
            self.progress_bar.set(0.2)
            
            # Run in a thread to avoid blocking the GUI
            def install_thread():
                try:
                    import subprocess
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", 
                        "pandas", "matplotlib", "rich"
                    ])
                    
                    self.status_var.set("Requirements installed. Restart the application.")
                    self.progress_bar.set(1.0)
                    
                    # Show message box
                    messagebox.showinfo(
                        "Installation Complete", 
                        "Analytics requirements have been installed.\nPlease restart the application."
                    )
                except Exception as e:
                    self.status_var.set(f"Error installing requirements: {str(e)}")
                    self.progress_bar.set(0)
            
            threading.Thread(target=install_thread, daemon=True).start()
        
        except Exception as e:
            self.status_var.set(f"Error installing requirements: {str(e)}")
            self.progress_bar.set(0)
    
    def browse_input_file(self):
        """Browse for an input file"""
        filename = filedialog.askopenfilename(
            title="Select proxy file",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filename:
            self.input_file.set(filename)
    
    def browse_file(self, variable):
        """Browse for a file and set the variable"""
        filename = filedialog.askopenfilename(
            title="Select file",
            filetypes=(("Text files", "*.txt"), ("JSON files", "*.json"), ("All files", "*.*"))
        )
        if filename:
            variable.set(filename)
    
    def save_file(self, variable):
        """Browse for a save location and set the variable"""
        filename = filedialog.asksaveasfilename(
            title="Save as",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filename:
            variable.set(filename)
    
    def scrape_only(self):
        """Scrape proxies without validation"""
        if self.working_thread and self.working_thread.is_alive():
            messagebox.showwarning("Operation in Progress", "Another operation is already running. Please stop it first.")
            return
        
        self.progress_var.set(0)
        self.status_var.set("Scraping proxies...")
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"{self.proxy_type.get()}_proxies_{timestamp}.txt")
        
        # Start scraping in a separate thread
        self.working_thread = threading.Thread(
            target=self._scrape_thread,
            args=(self.proxy_type.get(), output_file)
        )
        self.working_thread.daemon = True
        self.working_thread.start()
    
    def _scrape_thread(self, proxy_type, output_file):
        """Thread function for scraping"""
        try:
            print(f"Starting proxy scraping for {proxy_type}...")
            proxy_count = scrape_proxies(proxy_type, output_file, True)
            
            self.status_var.set(f"Scraped {proxy_count} {proxy_type} proxies")
            print(f"Scraping completed. Output saved to: {output_file}")
            
            messagebox.showinfo("Scraping Complete", f"Successfully scraped {proxy_count} {proxy_type} proxies.\nSaved to: {output_file}")
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Error during scraping: {str(e)}")
            messagebox.showerror("Error", f"An error occurred during scraping:\n{str(e)}")
    
    def validate_only(self):
        """Validate proxies without scraping"""
        if self.working_thread and self.working_thread.is_alive():
            messagebox.showwarning("Operation in Progress", "Another operation is already running. Please stop it first.")
            return
        
        if not self.input_file.get():
            messagebox.showwarning("Input Required", "Please select an input file with proxies to validate.")
            return
        
        self.progress_var.set(0)
        self.status_var.set("Validating proxies...")
        
        # Parse test sites
        test_sites = self.test_sites.get().split(",")
        test_sites = [site.strip() for site in test_sites if site.strip()]
        
        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(OUTPUT_DIR, f"{self.proxy_type.get()}_valid_{timestamp}.txt")
        
        # Start validation in a separate thread
        self.working_thread = threading.Thread(
            target=self._validate_thread,
            args=(
                self.input_file.get(),
                output_file,
                self.proxy_type.get(),
                self.timeout.get(),
                test_sites,
                self.min_success_rate.get()
            )
        )
        self.working_thread.daemon = True
        self.working_thread.start()
    
    def _validate_thread(self, input_file, output_file, proxy_type, timeout, test_sites, min_success_rate):
        """Thread function for validation"""
        try:
            print(f"Starting proxy validation for {proxy_type}...")
            valid_proxies = validate_proxies(
                input_file,
                output_file,
                proxy_type,
                timeout,
                test_sites,
                min_success_rate,
                True
            )
            
            valid_count = len(valid_proxies)
            self.status_var.set(f"Found {valid_count} valid {proxy_type} proxies")
            print(f"Validation completed. Found {valid_count} valid proxies.")
            print(f"Results saved to: {output_file}")
            
            messagebox.showinfo(
                "Validation Complete", 
                f"Found {valid_count} valid {proxy_type} proxies.\nSaved to: {output_file}"
            )
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Error during validation: {str(e)}")
            messagebox.showerror("Error", f"An error occurred during validation:\n{str(e)}")
    
    def scrape_and_validate(self):
        """Scrape and validate proxies"""
        if self.working_thread and self.working_thread.is_alive():
            messagebox.showwarning("Operation in Progress", "Another operation is already running. Please stop it first.")
            return
        
        self.progress_var.set(0)
        self.status_var.set("Scraping and validating proxies...")
        
        # Parse test sites
        test_sites = self.test_sites.get().split(",")
        test_sites = [site.strip() for site in test_sites if site.strip()]
        
        # Generate output filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        scraped_file = os.path.join(OUTPUT_DIR, f"{self.proxy_type.get()}_proxies_{timestamp}.txt")
        valid_file = os.path.join(OUTPUT_DIR, f"{self.proxy_type.get()}_valid_{timestamp}.txt")
        
        # Start scraping and validation in a separate thread
        self.working_thread = threading.Thread(
            target=self._scrape_validate_thread,
            args=(
                self.proxy_type.get(),
                scraped_file,
                valid_file,
                self.timeout.get(),
                test_sites,
                self.min_success_rate.get()
            )
        )
        self.working_thread.daemon = True
        self.working_thread.start()
    
    def _scrape_validate_thread(self, proxy_type, scraped_file, valid_file, timeout, test_sites, min_success_rate):
        """Thread function for scraping and validation"""
        try:
            print(f"Starting proxy scraping for {proxy_type}...")
            proxy_count = scrape_proxies(proxy_type, scraped_file, True)
            
            print(f"Scraped {proxy_count} {proxy_type} proxies. Now validating...")
            
            valid_proxies = validate_proxies(
                scraped_file,
                valid_file,
                proxy_type,
                timeout,
                test_sites,
                min_success_rate,
                True
            )
            
            valid_count = len(valid_proxies)
            self.status_var.set(f"Found {valid_count} valid {proxy_type} proxies")
            print(f"Validation completed. Found {valid_count} valid proxies out of {proxy_count} scraped.")
            print(f"Results saved to: {valid_file}")
            
            # Also save to live file
            live_file = os.path.join(OUTPUT_DIR, f"{proxy_type}_live.txt")
            with open(live_file, "w") as f:
                for proxy in valid_proxies:
                    f.write(str(proxy) + "\n")
            
            messagebox.showinfo(
                "Operation Complete", 
                f"Scraped: {proxy_count} proxies\nValid: {valid_count} proxies\n\nSaved to: {valid_file}\nLive file: {live_file}"
            )
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Error during operation: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
    
    def stop_operation(self):
        """Stop the current operation"""
        if self.working_thread and self.working_thread.is_alive():
            # We can't directly stop a thread, but we can set a flag
            self.status_var.set("Stopping operation...")
            messagebox.showinfo("Stopping", "The operation will stop after the current step completes.")
        else:
            messagebox.showinfo("No Operation", "No operation is currently running.")
    
    def start_monitor(self):
        """Start the proxy monitor"""
        if self.working_thread and self.working_thread.is_alive():
            messagebox.showwarning("Operation in Progress", "Another operation is already running. Please stop it first.")
            return
        
        if not self.monitor_input_file.get():
            messagebox.showwarning("Input Required", "Please select an input file with proxies to monitor.")
            return
        
        # Set up the monitor
        self.monitor_status.set("Running")
        self.last_check.set("Starting...")
        
        # Calculate next check time
        interval_minutes = self.check_interval.get()
        next_time = datetime.now()
        next_time = next_time.replace(second=0) + timedelta(minutes=interval_minutes)
        self.next_check.set(next_time.strftime("%Y-%m-%d %H:%M"))
        
        # Define the monitor function
        def monitor_thread():
            # Import the necessary functions
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from proxy_monitor import recheck_proxies
            
            run_once = self.monitor_once.get()
            interval = self.check_interval.get()
            method = self.monitor_proxy_type.get()
            input_file = self.monitor_input_file.get()
            timeout = 10  # Default timeout
            
            try:
                # Initial check
                print(f"Starting proxy monitor for {method} proxies...")
                print(f"Source file: {input_file}")
                print(f"Check interval: {interval} minutes")
                
                # Perform the check
                valid_proxies = recheck_proxies(method, input_file, timeout, interval)
                
                # Update UI
                self.last_check.set(datetime.now().strftime("%Y-%m-%d %H:%M"))
                if valid_proxies:
                    self.proxies_found.set(str(len(valid_proxies)))
                
                # Update history tree
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.history_tree.insert("", 0, values=(
                    timestamp, 
                    "N/A",  # We don't know how many were checked from the return
                    len(valid_proxies) if valid_proxies else 0,
                    "N/A"  # We don't know the success rate
                ))
                
                # If we're not running once, set up the scheduled checks
                if not run_once:
                    while True:
                        # Wait for the interval
                        for i in range(interval * 60):
                            if self.monitor_status.get() != "Running":
                                return  # Exit if stopped
                            time.sleep(1)
                            
                            # Update next check time every minute
                            if i % 60 == 0:
                                minutes_left = interval - (i // 60)
                                next_time = datetime.now() + timedelta(minutes=minutes_left)
                                self.next_check.set(next_time.strftime("%Y-%m-%d %H:%M"))
                        
                        # Perform the check
                        if self.monitor_status.get() != "Running":
                            return  # Exit if stopped
                        
                        print(f"\nScheduled check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        valid_proxies = recheck_proxies(method, input_file, timeout, interval)
                        
                        # Update UI
                        self.last_check.set(datetime.now().strftime("%Y-%m-%d %H:%M"))
                        if valid_proxies:
                            self.proxies_found.set(str(len(valid_proxies)))
                        
                        # Update history tree
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.history_tree.insert("", 0, values=(
                            timestamp, 
                            "N/A",
                            len(valid_proxies) if valid_proxies else 0,
                            "N/A"
                        ))
                else:
                    # Just run once and then set status to stopped
                    self.monitor_status.set("Stopped")
                    self.next_check.set("N/A")
                    print("Monitor completed (ran once)")
            
            except Exception as e:
                self.monitor_status.set("Error")
                print(f"Error in monitor: {str(e)}")
                messagebox.showerror("Monitor Error", str(e))
            
        # Start the thread
        self.monitor_thread = threading.Thread(target=monitor_thread)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitor(self):
        """Stop the proxy monitor"""
        if self.monitor_status.get() == "Running":
            self.monitor_status.set("Stopping...")
            print("Stopping proxy monitor...")
            
            # Wait for thread to recognize stop and exit
            time.sleep(1)
            self.monitor_status.set("Stopped")
            self.next_check.set("N/A")
            print("Proxy monitor stopped")
        else:
            messagebox.showinfo("Not Running", "The proxy monitor is not currently running.")
    
    def load_monitor_history(self):
        """Load proxy monitor history data"""
        # Look for history file in the output directory
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        
        history_file = os.path.join(OUTPUT_DIR, f"{self.monitor_proxy_type.get()}_history.json")
        
        try:
            with open(history_file, "r") as f:
                history_data = json.load(f)
                
                # Clear existing items
                for item in self.history_tree.get_children():
                    self.history_tree.delete(item)
                
                # Add history items (most recent first)
                for entry in reversed(history_data):
                    self.history_tree.insert("", 0, values=(
                        datetime.fromisoformat(entry.get("datetime", "")).strftime("%Y-%m-%d %H:%M:%S"),
                        entry.get("total_checked", "N/A"),
                        entry.get("valid_count", "N/A"),
                        f"{entry.get('success_rate', 0):.2f}"
                    ))
        except (FileNotFoundError, json.JSONDecodeError):
            # No history or invalid file, that's okay
            pass
    
    def start_geo(self):
        """Start adding geolocation data"""
        if self.working_thread and self.working_thread.is_alive():
            messagebox.showwarning("Operation in Progress", "Another operation is already running. Please stop it first.")
            return
        
        if not self.geo_input_file.get():
            messagebox.showwarning("Input Required", "Please select an input file with proxies to geolocate.")
            return
        
        # Generate default output file if not specified
        if not self.geo_output_file.get():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
            self.geo_output_file.set(os.path.join(output_dir, f"geo_proxies_{timestamp}.json"))
        
        # Update status
        self.status_var.set("Adding geolocation data...")
        self.progress_var.set(0)
        
        # Start the geo operation in a thread
        self.working_thread = threading.Thread(target=self._geo_thread)
        self.working_thread.daemon = True
        self.working_thread.start()
    
    def _geo_thread(self):
        """Thread for geolocation data processing"""
        try:
            # Import the geo module
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from proxy_geo import process_proxy_list, get_ip_info, assess_anonymity
            
            input_file = self.geo_input_file.get()
            output_file = self.geo_output_file.get()
            
            print(f"Adding geolocation data to proxies in {input_file}")
            print(f"Output will be saved to {output_file}")
            
            # Process proxies directly to have more control in the GUI
            # Clear the treeview
            for item in self.geo_tree.get_children():
                self.geo_tree.delete(item)
            
            for item in self.country_tree.get_children():
                self.country_tree.delete(item)
                
            for item in self.anon_tree.get_children():
                self.anon_tree.delete(item)
            
            # Load proxies
            proxies = []
            try:
                with open(input_file, "r") as f:
                    for line in f:
                        proxy = line.strip()
                        if proxy:
                            proxies.append(proxy)
            except FileNotFoundError:
                print(f"Error: File {input_file} not found")
                messagebox.showerror("Error", f"File {input_file} not found")
                return
            
            if not proxies:
                print("No proxies found in input file")
                messagebox.showwarning("No Proxies", "No proxies found in the input file")
                return
            
            # Set up results storage
            results = []
            country_stats = {}
            anonymity_stats = {}
            
            # Progress tracking
            total_proxies = len(proxies)
            processed = 0
            
            print(f"Processing {total_proxies} proxies...")
            
            # Process each proxy
            for proxy in proxies:
                # Extract IP address
                ip = proxy.split(":")[0]
                
                # Get geolocation data
                ip_info = get_ip_info(ip)
                
                # Try backup if primary fails
                if ip_info["status"] != "success":
                    ip_info = get_ip_info(ip, use_backup=True)
                
                # Assess anonymity
                anonymity = assess_anonymity(ip_info)
                
                # Create result entry
                result = {
                    "proxy": proxy,
                    "ip": ip,
                    "country": ip_info.get("country", "Unknown"),
                    "countryCode": ip_info.get("countryCode", "XX"),
                    "region": ip_info.get("regionName", ""),
                    "city": ip_info.get("city", "Unknown"),
                    "isp": ip_info.get("isp", "Unknown"),
                    "organization": ip_info.get("org", ""),
                    "as": ip_info.get("as", ""),
                    "asname": ip_info.get("asname", ""),
                    "isProxy": ip_info.get("proxy", False),
                    "isHosting": ip_info.get("hosting", False),
                    "anonymityLevel": anonymity
                }
                
                # Add to results
                results.append(result)
                
                # Update statistics
                country = result["country"]
                if country in country_stats:
                    country_stats[country] += 1
                else:
                    country_stats[country] = 1
                
                if anonymity in anonymity_stats:
                    anonymity_stats[anonymity] += 1
                else:
                    anonymity_stats[anonymity] = 1
                
                # Add to treeview
                self.geo_tree.insert("", "end", values=(
                    proxy,
                    country,
                    result["city"],
                    result["isp"],
                    anonymity
                ))
                
                # Update progress
                processed += 1
                self.progress_var.set(processed / total_proxies)
                print(f"Processed {processed}/{total_proxies}: {proxy} - {country}, {result['city']}")
                
                # Let the GUI update
                time.sleep(0.01)
            
            # Save results
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "w") as f:
                json.dump(results, f, indent=2)
            
            # Update statistics views
            total = len(results)
            
            # Country stats
            sorted_countries = sorted(country_stats.items(), key=lambda x: x[1], reverse=True)
            for country, count in sorted_countries:
                percentage = (count / total) * 100
                self.country_tree.insert("", "end", values=(
                    country,
                    count,
                    f"{percentage:.1f}%"
                ))
            
            # Anonymity stats
            sorted_anonymity = sorted(anonymity_stats.items(), key=lambda x: x[1], reverse=True)
            for level, count in sorted_anonymity:
                percentage = (count / total) * 100
                self.anon_tree.insert("", "end", values=(
                    level,
                    count,
                    f"{percentage:.1f}%"
                ))
            
            # Complete
            self.status_var.set(f"Geolocation complete: {total} proxies processed")
            self.progress_var.set(1)
            print(f"Geolocation complete. Results saved to {output_file}")
            messagebox.showinfo("Complete", f"Successfully added geolocation data to {total} proxies.\nResults saved to {output_file}")
            
        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Error during geolocation: {str(e)}")
            messagebox.showerror("Error", f"An error occurred during geolocation:\n{str(e)}")
    
    def stop_geo(self):
        """Stop the geolocation operation"""
        if self.working_thread and self.working_thread.is_alive():
            self.status_var.set("Stopping geolocation...")
            messagebox.showinfo("Stopping", "The operation will stop after the current step completes.")
        else:
            messagebox.showinfo("No Operation", "No geolocation operation is currently running.")
    
    def view_geo_results(self):
        """View geolocation results from a file"""
        # Ask for a file to view
        filename = filedialog.askopenfilename(
            title="Select Geolocation Results File",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            initialdir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
        )
        
        if not filename:
            return
        
        try:
            # Load the file
            with open(filename, "r") as f:
                results = json.load(f)
            
            # Clear the treeviews
            for item in self.geo_tree.get_children():
                self.geo_tree.delete(item)
            
            for item in self.country_tree.get_children():
                self.country_tree.delete(item)
                
            for item in self.anon_tree.get_children():
                self.anon_tree.delete(item)
            
            # Statistics
            country_stats = {}
            anonymity_stats = {}
            
            # Populate treeview
            for result in results:
                self.geo_tree.insert("", "end", values=(
                    result.get("proxy", "Unknown"),
                    result.get("country", "Unknown"),
                    result.get("city", "Unknown"),
                    result.get("isp", "Unknown"),
                    result.get("anonymityLevel", "Unknown")
                ))
                
                # Update statistics
                country = result.get("country", "Unknown")
                if country in country_stats:
                    country_stats[country] += 1
                else:
                    country_stats[country] = 1
                
                anonymity = result.get("anonymityLevel", "Unknown")
                if anonymity in anonymity_stats:
                    anonymity_stats[anonymity] += 1
                else:
                    anonymity_stats[anonymity] = 1
            
            # Update statistics views
            total = len(results)
            
            # Country stats
            sorted_countries = sorted(country_stats.items(), key=lambda x: x[1], reverse=True)
            for country, count in sorted_countries:
                percentage = (count / total) * 100
                self.country_tree.insert("", "end", values=(
                    country,
                    count,
                    f"{percentage:.1f}%"
                ))
            
            # Anonymity stats
            sorted_anonymity = sorted(anonymity_stats.items(), key=lambda x: x[1], reverse=True)
            for level, count in sorted_anonymity:
                percentage = (count / total) * 100
                self.anon_tree.insert("", "end", values=(
                    level,
                    count,
                    f"{percentage:.1f}%"
                ))
            
            print(f"Loaded {len(results)} proxies with geolocation data from {filename}")
            
        except Exception as e:
            print(f"Error loading file: {str(e)}")
            messagebox.showerror("Error", f"Failed to load geolocation data:\n{str(e)}")
    
    def start_rotator(self):
        """Start the proxy rotator"""
        if self.rotator_thread and hasattr(self, 'rotator_thread') and self.rotator_thread.is_alive():
            messagebox.showwarning("Already Running", "Proxy rotator is already running.")
            return
        
        if not self.rotator_input_file.get():
            messagebox.showwarning("Input Required", "Please select an input file with proxies to use.")
            return
        
        # Update status
        self.rotator_status.set("Starting...")
        
        # Start the rotator in a thread
        self.rotator_thread = threading.Thread(target=self._rotator_thread)
        self.rotator_thread.daemon = True
        self.rotator_thread.start()
    
    def _rotator_thread(self):
        """Thread for running the proxy rotator"""
        try:
            # Import the rotator module
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from proxy_rotator import load_proxies_from_file
            
            # Set up rotator parameters
            input_file = self.rotator_input_file.get()
            port = self.rotator_port.get()
            rotation_count = self.rotation_count.get()
            timeout = self.rotator_timeout.get()
            skip_testing = self.skip_testing.get()
            
            print(f"Starting proxy rotator on port {port}")
            print(f"Using proxies from: {input_file}")
            print(f"Rotation count: {rotation_count}")
            print(f"Timeout: {timeout} seconds")
            print(f"Skip testing: {skip_testing}")
            
            # Load proxies
            proxies = load_proxies_from_file(input_file, skip_testing, timeout)
            
            if not proxies:
                print("No valid proxies found. Rotator cannot start.")
                self.rotator_status.set("Error: No proxies")
                messagebox.showerror("No Proxies", "No valid proxies found. Rotator cannot start.")
                return
            
            # Update proxy count
            self.proxy_count.set(str(len(proxies)))
            
            # Update the tree
            for item in self.proxy_tree.get_children():
                self.proxy_tree.delete(item)
            
            for proxy_info in proxies:
                self.proxy_tree.insert("", "end", values=(
                    proxy_info["proxy"],
                    "0", # success count
                    "0", # fail count
                    "N/A" # success rate
                ))
            
            # Create server in thread subprocess since we can't easily stop it otherwise
            from subprocess import Popen, PIPE
            
            # Build the command
            cmd = [
                sys.executable,
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "proxy_rotator.py"),
                "-i", input_file,
                "-p", str(port),
                "-r", str(rotation_count),
                "-t", str(timeout)
            ]
            
            if skip_testing:
                cmd.append("--skip-testing")
            
            # Run the command
            self.rotator_process = Popen(cmd, stdout=PIPE, stderr=PIPE, text=True, bufsize=1)
            
            # Update status
            self.rotator_status.set("Running")
            
            # Track current proxy and performance
            proxy_index = 0
            start_time = time.time()
            success_count = 0
            
            # Set initial proxy
            if proxies:
                self.current_proxy.set(proxies[0]["proxy"])
            
            # Monitor the process
            while self.rotator_process.poll() is None:
                # Read output
                output = self.rotator_process.stdout.readline().strip()
                if output:
                    print(output)
                    
                    # Check for rotation messages
                    if "Rotating to proxy" in output:
                        # Extract the proxy
                        parts = output.split("Rotating to proxy")
                        if len(parts) > 1:
                            new_proxy = parts[1].strip()
                            self.current_proxy.set(new_proxy)
                            
                            # Update proxy index
                            for i, proxy_info in enumerate(proxies):
                                if proxy_info["proxy"] in new_proxy:
                                    proxy_index = i
                                    break
                    
                    # Check for success/fail messages
                    elif "Success:" in output:
                        success_count += 1
                        self.success_requests.set(str(success_count))
                        
                        # Calculate throughput
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            throughput = success_count / elapsed
                            self.throughput.set(f"{throughput:.2f} req/s")
                        
                        # Update proxy stats in tree
                        if "via" in output:
                            proxy_str = output.split("via")[1].strip()
                            for item in self.proxy_tree.get_children():
                                values = self.proxy_tree.item(item, "values")
                                if proxy_str in values[0]:
                                    # Increment success count
                                    success = int(values[1]) + 1
                                    fail = int(values[2])
                                    rate = success / (success + fail) if (success + fail) > 0 else 0
                                    
                                    self.proxy_tree.item(item, values=(
                                        values[0],
                                        str(success),
                                        values[2],
                                        f"{rate:.2f}"
                                    ))
                                    break
                    
                    elif "Error for" in output:
                        # Update proxy stats in tree
                        for item in self.proxy_tree.get_children():
                            values = self.proxy_tree.item(item, "values")
                            if values[0] in output:
                                # Increment fail count
                                success = int(values[1])
                                fail = int(values[2]) + 1
                                rate = success / (success + fail) if (success + fail) > 0 else 0
                                
                                self.proxy_tree.item(item, values=(
                                    values[0],
                                    values[1],
                                    str(fail),
                                    f"{rate:.2f}"
                                ))
                                break
                
                # Check for errors
                err_output = self.rotator_process.stderr.readline().strip()
                if err_output:
                    print(f"ERROR: {err_output}")
                
                # Sleep a bit to avoid consuming all CPU
                time.sleep(0.1)
            
            # Process ended
            print("Proxy rotator has stopped")
            self.rotator_status.set("Stopped")
            self.current_proxy.set("None")
            
        except Exception as e:
            self.rotator_status.set("Error")
            print(f"Error during proxy rotation: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
    
    def stop_rotator(self):
        """Stop the proxy rotator"""
        if hasattr(self, 'rotator_process') and self.rotator_process:
            print("Stopping proxy rotator...")
            self.rotator_status.set("Stopping...")
            
            # Terminate the process
            try:
                self.rotator_process.terminate()
                
                # Wait for process to end
                for _ in range(5):  # Wait up to 5 seconds
                    if self.rotator_process.poll() is not None:
                        break
                    time.sleep(1)
                
                # Force kill if still running
                if self.rotator_process.poll() is None:
                    if sys.platform == 'win32':
                        import subprocess
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.rotator_process.pid)])
                    else:
                        import signal
                        os.kill(self.rotator_process.pid, signal.SIGKILL)
                
                self.rotator_status.set("Stopped")
                self.current_proxy.set("None")
                print("Proxy rotator stopped")
                
            except Exception as e:
                print(f"Error stopping rotator: {str(e)}")
        else:
            messagebox.showinfo("Not Running", "The proxy rotator is not currently running.")
    
    def test_rotator_connection(self):
        """Test the proxy rotator connection"""
        if self.rotator_status.get() != "Running":
            messagebox.showwarning("Not Running", "The proxy rotator is not currently running.")
            return
        
        try:
            import requests
            
            # Test the connection
            port = self.rotator_port.get()
            proxy_url = f"http://localhost:{port}"
            
            proxy_config = {
                "http": proxy_url,
                "https": proxy_url
            }
            
            print(f"Testing connection to proxy rotator at {proxy_url}...")
            
            # Try to connect
            response = requests.get("http://icanhazip.com", 
                                   proxies=proxy_config, 
                                   timeout=self.rotator_timeout.get())
            
            if response.status_code == 200:
                ip = response.text.strip()
                print(f"Connection successful! Your IP appears as: {ip}")
                messagebox.showinfo("Test Successful", f"Connection successful!\nYour IP appears as: {ip}")
            else:
                print(f"Connection failed. Status code: {response.status_code}")
                messagebox.showerror("Test Failed", f"Connection failed.\nStatus code: {response.status_code}")
                
        except Exception as e:
            print(f"Error testing connection: {str(e)}")
            messagebox.showerror("Connection Error", f"Failed to connect to proxy rotator:\n{str(e)}")
    
    def show_about(self):
        """Show information about the creator and the tool"""
        about_window = tk.Toplevel(self)
        about_window.title("About ProxyMaster")
        about_window.geometry("400x300")
        about_window.resizable(False, False)
        
        # Make the window modal
        about_window.transient(self)
        about_window.grab_set()
        
        # Center content
        frame = ctk.CTkFrame(about_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Logo or title
        title = ctk.CTkLabel(
            frame, 
            text="ProxyMaster 2.0",
            font=("Arial", 24, "bold")
        )
        title.pack(pady=(20, 10))
        
        # Creator info
        creator = ctk.CTkLabel(
            frame, 
            text="Created by: cyb3r_vishal",
            font=("Arial", 14)
        )
        creator.pack(pady=5)
        
        # Community info
        community = ctk.CTkLabel(
            frame, 
            text="community DevKitX",
            font=("Arial", 14)
        )
        community.pack(pady=5)
        
        # Description
        description = ctk.CTkLabel(
            frame, 
            text="A comprehensive suite of tools for scraping,\nvalidating, and managing proxy lists",
            font=("Arial", 12),
            justify="center"
        )
        description.pack(pady=(20, 10))
        
        # Version
        version = ctk.CTkLabel(
            frame, 
            text=f"Version 2.0.0 | {datetime.now().strftime('%Y-%m-%d')}",
            font=("Arial", 10),
            text_color="gray60"
        )
        version.pack(pady=5)
        
        # Close button
        close_btn = ctk.CTkButton(
            frame, 
            text="Close", 
            command=about_window.destroy,
            width=100
        )
        close_btn.pack(pady=20)
    
    def on_closing(self):
        """Handle window closing"""
        running_operations = []
        
        if self.working_thread and self.working_thread.is_alive():
            running_operations.append("scraping/validation")
            
        if hasattr(self, 'monitor_thread') and self.monitor_thread and self.monitor_thread.is_alive():
            running_operations.append("proxy monitor")
            
        if hasattr(self, 'rotator_process') and self.rotator_process and self.rotator_process.poll() is None:
            running_operations.append("proxy rotator")
        
        if running_operations:
            if messagebox.askokcancel("Quit", f"The following operations are still running: {', '.join(running_operations)}.\nDo you want to quit anyway?"):
                # Stop rotator if running
                if hasattr(self, 'rotator_process') and self.rotator_process and self.rotator_process.poll() is None:
                    try:
                        self.rotator_process.terminate()
                        # Force kill if needed
                        if sys.platform == 'win32':
                            import subprocess
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.rotator_process.pid)])
                        else:
                            import signal
                            os.kill(self.rotator_process.pid, signal.SIGKILL)
                    except:
                        pass
                  # Restore stdout
                sys.stdout = self.old_stdout
                self.destroy()
        else:
            # Restore stdout
            sys.stdout = self.old_stdout
            self.destroy()


if __name__ == "__main__":
    app = ProxyMasterGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
