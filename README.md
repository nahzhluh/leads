# Leads - Powered by Claude AI

A smart job search tool that works for ANY role on LinkedIn! Uses Claude AI to analyze your resume and job requirements for intelligent matching with industry preferences. Perfect for any job seeker in any field! Happy job hunting 🚀 

## 🔧 How It Works

The system will:
1. **Analyze your resume with AI** - Claude extracts skills and experience from your resume
2. **Understand what role you're seeking** - Claude analyzes your keywords to understand your target role
3. **Find fresh jobs matching your criteria** - Searches LinkedIn for recent jobs matching your preferences
4. **Rank them by how well they match your background and industry preferences** - Compares job requirements with your resume and preferences
5. **Show you the best opportunities first with detailed reasoning** - Displays jobs ranked by match quality (High/Medium/Low) with confidence scores
6. **Save jobs of interest**: Option to save jobs and generate personalized resumes
7. **Hide jobs from future results**: Option to hide jobs you're not interested in to focus on new opportunities

## 🎯 Quick Start

### 1. Setup & Anthropic API Key
```bash
# Clone Leads
git clone https://github.com/nahzhluh/leads.git

# Navigate to project directory
cd <path-to-leads-project-directory>

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Get your Anthropic API key from https://console.anthropic.com/
# Add it permanently to your shell profile
echo 'export ANTHROPIC_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### 2. Configure your search preferences
Edit `job_config.py` to customize your search:

```python
# Job search keywords examples
KEYWORDS = ["software engineer", "full stack developer", "backend engineer"]

# Preferred locations examples
LOCATIONS = ["Remote", "San Francisco", "New York", "Austin"]

# Target companies examples
TARGET_COMPANIES = ["Google", "Microsoft", "Apple", "Meta", "Amazon"]

# Preferred industries examples
PREFERRED_INDUSTRIES = ["Technology", "Software", "SaaS", "Consumer Technology"]

# Industries to avoid examples
INDUSTRIES_TO_AVOID = ["Insurance", "Real Estate", "Manufacturing", "Healthcare"]

# Search time period (r86400=24h, r172800=48h, r259200=3d, r604800=1w)
SEARCH_TIME_PERIOD = "r86400"

# Resume and saved jobs file paths
RESUME_PATH = "./resume.pdf"  # Path to your resume
SAVED_JOBS_DIR = "./saved_jobs"  # Where to save results
```

**Resume formats:** `.pdf`, `.txt`, `.docx`, `.doc`, `.md`

### 3. Run the leads finder
```bash
python leads.py
```

## 📁 Lead Project Files

- `leads.py` - Main leads script (works for any role)
- `job_config.py` - Customize your search preferences here
- `claude_resume_analyzer.py` - AI-powered resume analysis with caching
- `requirements.txt` - Python dependencies
- `cache_manager.py` - Cache management tool
- `README.md` - This documentation

## 📊 Sample Output

```
🚀 Flexible Job Finder - Powered by Claude AI
==================================================
📦 Cache Status: 45 entries (2.3 MB)
🎯 Searching for: product manager, technical product manager, senior product manager
📍 Locations: Remote, Durham, Raleigh, Chapel Hill, New York
🏭 Preferred Industries: Technology, Software, SaaS, Consumer Technology
❌ Industries to Avoid: Insurance, Real Estate, Manufacturing, Healthcare

🔍 Analyzing role requirements...
✅ Role Analysis Complete!
📋 Role: Product Manager
📝 Description: Product management role focusing on technical products and user experience
🔧 Required Skills: product strategy, user research, data analysis, cross-functional leadership

📄 Analyzing your resume...
📦 Loading job analysis cache...
📦 Loaded 45 cached job analyses

⏰ Searching for jobs posted in the last 24 hours...
📅 2025-08-04 08:46:08

💾 Saving updated job analysis cache...

📊 Cache Statistics:
   📦 Total jobs found: 23
   💾 Jobs from cache: 18
   🔄 New analyses: 5
   📈 Cache hit rate: 78.3%

🟢 HIGH MATCH JOBS (13 jobs) - Best opportunities:
------------------------------------------------------------
1. 🟢 Product Manager
   Match: High Match (Confidence: 9/10)
   Company: BlinkRx
   Location: New York, NY
   Posted: 16 hours ago
   Industry Fit: excellent
   Assessment: Strong alignment with technical PM skills and role requirements...

📊 Match Summary:
   🟢 High Match: 13 jobs
   🟡 Medium Match: 4 jobs
   🔴 Low Match: 6 jobs
```

## 🎉 That's It!