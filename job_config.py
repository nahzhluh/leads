#!/usr/bin/env python3
"""
Job Search Configuration - Customize your search here!
"""

# JOB SEARCH KEYWORDS - Change these to match your target role
# Examples:
# ["software engineer", "full stack developer", "backend engineer"]
# ["data scientist", "machine learning engineer", "analytics engineer"] 
# ["product manager", "technical product manager", "senior product manager"]
# ["marketing manager", "digital marketing", "growth marketing"]
# ["sales representative", "account executive", "business development"]
# ["designer", "ux designer", "ui designer", "product designer"]
KEYWORDS = ["software engineer", "full stack developer", "backend engineer"]

# LOCATIONS - Change these to your preferred locations
# Examples:
# ["Remote", "San Francisco", "New York", "Austin"]
# ["Remote", "Durham", "Raleigh", "Chapel Hill"]
# ["Remote", "Boston", "Cambridge", "Somerville"]
LOCATIONS = ["Remote", "San Francisco", "New York", "Austin"]

# TARGET COMPANIES - Companies you're particularly interested in
# These will get a bonus score in matching
# Examples:
# ["Google", "Microsoft", "Apple", "Meta", "Amazon"]
# ["Red Hat", "SAS", "IBM", "Lenovo"]
# ["Startup1", "Startup2", "Company3"]
TARGET_COMPANIES = [
    "Google", "Microsoft", "Apple", "Meta", "Amazon", "Netflix", "Uber", "Airbnb"
]

# PREFERRED INDUSTRIES - Industries you're most interested in
# These will get a bonus score in matching
# Examples:
# ["Technology", "Software", "SaaS", "Fintech", "Healthcare", "E-commerce"]
# ["Consumer Technology", "Developer Tools", "Open Source", "AI/ML"]
# ["Gaming", "Entertainment", "Media", "Education"]
PREFERRED_INDUSTRIES = [
    "Technology", "Software", "SaaS", "Fintech", "Healthcare", "E-commerce"
]

# INDUSTRIES TO AVOID - Industries you're not interested in
# These will get a penalty in matching
# Examples:
# ["Insurance", "Real Estate", "Manufacturing", "Retail"]
# ["Healthcare", "Government", "Non-profit"]
INDUSTRIES_TO_AVOID = [
    "Insurance", "Real Estate", "Manufacturing", "Retail"
]

# SEARCH SETTINGS
MAX_JOBS_PER_SEARCH = 5  # Number of jobs to fetch per keyword/location combination
SEARCH_DELAY = 2  # Seconds to wait between searches (be nice to LinkedIn!)

# SEARCH TIME PERIOD - How far back to search for jobs
# Options: r86400 (24 hours), r172800 (48 hours), r259200 (3 days), r604800 (1 week)
# Examples:
# SEARCH_TIME_PERIOD = "r86400"      # Last 24 hours (default)
# SEARCH_TIME_PERIOD = "r172800"     # Last 48 hours
# SEARCH_TIME_PERIOD = "r259200"     # Last 3 days
# SEARCH_TIME_PERIOD = "r604800"     # Last week
# SEARCH_TIME_PERIOD = "r2592000"    # Last month
SEARCH_TIME_PERIOD = "r86400"        # Last 24 hours (default)

# FILE PATHS - Configure where to find your resume and save job results
# Examples:
# RESUME_PATH = "/Users/username/Documents/resume.pdf"
# RESUME_PATH = "C:\\Users\\username\\Documents\\resume.pdf"
# RESUME_PATH = "./resume.pdf"  # Relative to project directory
RESUME_PATH = "./resume.pdf"  # Path to your resume file

# SAVED JOBS DIRECTORY - Where to save selected job results
# Examples:
# SAVED_JOBS_DIR = "/Users/username/Documents/job_search_results"
# SAVED_JOBS_DIR = "C:\\Users\\username\\Documents\\job_search_results"
# SAVED_JOBS_DIR = "./saved_jobs"  # Relative to project directory
SAVED_JOBS_DIR = "./saved_jobs"  # Directory to save job results

# REMOTE JOB INDICATORS - Keywords that indicate a job is remote
# Used for location filtering to identify true remote positions
REMOTE_INDICATORS = [
    "remote", "work from home", "wfh", "virtual", "anywhere", 
    "united states", "us", "usa"
]

# HIDDEN JOBS - Jobs to hide from future results
# This file stores job IDs that you want to hide from future searches
HIDDEN_JOBS_FILE = "./hidden_jobs.json"  # File to store hidden job IDs 