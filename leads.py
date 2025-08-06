#!/usr/bin/env python3
"""
Leads - Works for any role using Claude AI
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import time
import os
import json
import anthropic
import hashlib
from claude_resume_analyzer import analyze_resume_file, read_resume_file
from job_config import KEYWORDS, LOCATIONS, TARGET_COMPANIES, PREFERRED_INDUSTRIES, INDUSTRIES_TO_AVOID, MAX_JOBS_PER_SEARCH, SEARCH_DELAY, SEARCH_TIME_PERIOD, RESUME_PATH, SAVED_JOBS_DIR, REMOTE_INDICATORS, HIDDEN_JOBS_FILE

# Cache configuration
CACHE_FILE = "job_analysis_cache.json"
CACHE_EXPIRY_DAYS = 7  # Cache expires after 7 days

def generate_job_cache_key(job):
    """Generate a unique cache key for a job based on title, company, and URL"""
    # Create a unique identifier for the job
    job_identifier = f"{job['title'].lower().strip()}_{job['company'].lower().strip()}"
    
    # If URL is available, use it to make the key more unique
    if job.get('url'):
        # Extract the job ID from LinkedIn URL if possible
        url_match = re.search(r'/jobs/view/.*?-(\d+)', job['url'])
        if url_match:
            job_identifier += f"_{url_match.group(1)}"
        else:
            # Use a hash of the URL as fallback
            url_hash = hashlib.md5(job['url'].encode()).hexdigest()[:8]
            job_identifier += f"_{url_hash}"
    
    return job_identifier

def load_job_cache():
    """Load the job analysis cache from file"""
    if not os.path.exists(CACHE_FILE):
        return {}
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        # Check cache expiry and clean expired entries
        current_time = datetime.now()
        cleaned_cache = {}
        
        for job_key, cache_entry in cache_data.items():
            cached_time = datetime.fromisoformat(cache_entry['timestamp'])
            if (current_time - cached_time).days < CACHE_EXPIRY_DAYS:
                cleaned_cache[job_key] = cache_entry
            else:
                print(f"🗑️  Removing expired cache entry for: {cache_entry.get('job_title', 'Unknown job')}")
        
        # Save cleaned cache back to file
        if len(cleaned_cache) != len(cache_data):
            save_job_cache(cleaned_cache)
        
        print(f"📦 Loaded {len(cleaned_cache)} cached job analyses")
        return cleaned_cache
        
    except Exception as e:
        print(f"⚠️  Error loading cache: {e}")
        return {}

def save_job_cache(cache_data):
    """Save the job analysis cache to file"""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Error saving cache: {e}")

def get_cached_job_analysis(job, cache_data):
    """Get cached analysis for a job if available"""
    job_key = generate_job_cache_key(job)
    
    if job_key in cache_data:
        cache_entry = cache_data[job_key]
        return cache_entry['analysis']
    
    return None

def cache_job_analysis(job, analysis, cache_data):
    """Cache the analysis result for a job"""
    job_key = generate_job_cache_key(job)
    
    cache_data[job_key] = {
        'job_title': job['title'],
        'company': job['company'],
        'url': job.get('url', ''),
        'analysis': analysis,
        'timestamp': datetime.now().isoformat()
    }

def clear_job_cache():
    """Clear the job analysis cache"""
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print(f"🗑️  Cleared job analysis cache: {CACHE_FILE}")
        else:
            print("📦 No cache file found to clear")
    except Exception as e:
        print(f"❌ Error clearing cache: {e}")

def get_cache_stats():
    """Get statistics about the current cache"""
    if not os.path.exists(CACHE_FILE):
        return {"total_entries": 0, "cache_size_mb": 0}
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
        
        cache_size = os.path.getsize(CACHE_FILE) / (1024 * 1024)  # Size in MB
        
        return {
            "total_entries": len(cache_data),
            "cache_size_mb": round(cache_size, 2)
        }
    except Exception as e:
        print(f"⚠️  Error getting cache stats: {e}")
        return {"total_entries": 0, "cache_size_mb": 0}

def load_hidden_jobs():
    """Load the list of hidden job IDs"""
    if not os.path.exists(HIDDEN_JOBS_FILE):
        return set()
    
    try:
        with open(HIDDEN_JOBS_FILE, 'r', encoding='utf-8') as f:
            hidden_jobs = json.load(f)
        return set(hidden_jobs)
    except Exception as e:
        print(f"⚠️  Error loading hidden jobs: {e}")
        return set()

def save_hidden_jobs(hidden_jobs):
    """Save the list of hidden job IDs"""
    try:
        with open(HIDDEN_JOBS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(hidden_jobs), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  Error saving hidden jobs: {e}")

def hide_job(job, hidden_jobs):
    """Add a job to the hidden jobs list"""
    job_key = generate_job_cache_key(job)
    hidden_jobs.add(job_key)
    save_hidden_jobs(hidden_jobs)
    print(f"🚫 Hidden job: {job['title']} at {job['company']}")

def is_job_hidden(job, hidden_jobs):
    """Check if a job is in the hidden jobs list"""
    job_key = generate_job_cache_key(job)
    return job_key in hidden_jobs

def filter_hidden_jobs(jobs, hidden_jobs):
    """Filter out hidden jobs from the list"""
    filtered_jobs = []
    hidden_count = 0
    
    for job in jobs:
        if is_job_hidden(job, hidden_jobs):
            hidden_count += 1
        else:
            filtered_jobs.append(job)
    
    if hidden_count > 0:
        print(f"🚫 Filtered out {hidden_count} hidden jobs")
    
    return filtered_jobs

def analyze_role_with_claude(keywords, api_key):
    """Use Claude to analyze what role the keywords represent and what skills are needed"""
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Retry configuration
    max_retries = 3
    base_delay = 2  # seconds
    
    prompt = f"""
You are an expert job market analyst. Based on the provided job search keywords, determine:

1. What role/position these keywords represent
2. What skills, technologies, and qualifications are typically required for this role
3. What experience level this role typically requires

JOB SEARCH KEYWORDS:
{', '.join(keywords)}

Please provide a structured analysis in the following JSON format:

{{
    "role_title": "clear title of the role being searched",
    "role_description": "brief description of what this role typically involves",
    "required_skills": [
        "skill1",
        "skill2",
        "skill3"
    ],
    "preferred_skills": [
        "skill1", 
        "skill2"
    ],
    "technologies": [
        "tech1",
        "tech2"
    ],
    "experience_level": "entry|junior|mid_level|senior|lead",
    "typical_industries": [
        "industry1",
        "industry2"
    ],
    "key_responsibilities": [
        "responsibility1",
        "responsibility2"
    ],
    "certifications": [
        "cert1",
        "cert2"
    ]
}}

Guidelines:
1. Be comprehensive but accurate - only include skills/technologies that are genuinely relevant
2. Consider both technical and soft skills
3. Include industry-standard tools and technologies
4. Think about transferable skills that might be relevant
5. Consider different seniority levels within the role

Return ONLY the JSON response, no additional text.
"""
    
    # Retry loop
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = response.content[0].text
            
            # Try to parse the JSON response
            try:
                role_analysis = json.loads(content)
                return role_analysis
            except json.JSONDecodeError:
                print("❌ Claude returned invalid JSON. Trying to extract JSON...")
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        role_analysis = json.loads(json_match.group())
                        return role_analysis
                    except json.JSONDecodeError:
                        print("❌ Could not parse Claude's response")
                        return None
                else:
                    print("❌ No JSON found in Claude's response")
                    return None
                    
        except Exception as e:
            error_message = str(e)
            print(f"❌ Error calling Claude API (attempt {attempt + 1}/{max_retries}): {e}")
            
            # Check if it's a retryable error
            if "overloaded" in error_message.lower() or "529" in error_message or "rate limit" in error_message.lower():
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"⏳ API overloaded. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    print("❌ Max retries reached. API is still overloaded.")
                    return None
            else:
                # Non-retryable error
                print("❌ Non-retryable error encountered.")
                return None
    
    return None



def get_linkedin_jobs(keywords, locations):
    """Get jobs from LinkedIn posted within the configured time period"""
    
    all_jobs = []
    
    print(f"🔍 Searching LinkedIn for fresh {keywords[0]} jobs...")
    print(f"  Keywords: {', '.join(keywords)}")
    print(f"  Locations: {', '.join(locations)}")
    print(f"  Total searches: {len(keywords) * len(locations)}")
    
    for keyword in keywords:
        for location in locations:
            try:
                # LinkedIn job search URL
                search_url = "https://www.linkedin.com/jobs/search/"
                params = {
                    'keywords': keyword,
                    'location': location,
                    'f_TPR': SEARCH_TIME_PERIOD,  # Configurable time period
                    'position': 1,
                    'pageNum': 0
                }
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                response = requests.get(search_url, params=params, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Find job listings
                    job_cards = soup.find_all('div', class_='base-card')
                    
                    for card in job_cards[:MAX_JOBS_PER_SEARCH]:  # Limit jobs per search
                        try:
                            # Extract job info
                            title_elem = card.find('h3', class_='base-search-card__title')
                            company_elem = card.find('h4', class_='base-search-card__subtitle')
                            location_elem = card.find('span', class_='job-search-card__location')
                            time_elem = card.find('time')
                            

                            
                            if title_elem and company_elem:
                                title = title_elem.get_text(strip=True)
                                company = company_elem.get_text(strip=True)
                                job_location = location_elem.get_text(strip=True) if location_elem else "Unknown"
                                posted_time_raw = time_elem.get_text(strip=True) if time_elem else "Recently"
                                

                                
                                # Get job URL
                                job_link = card.find('a', class_='base-card__full-link')
                                url = job_link['href'] if job_link else ""
                                
                                # Check if it's a target company
                                is_target = any(target.lower() in company.lower() for target in TARGET_COMPANIES)
                                
                                job_info = {
                                    'title': title,
                                    'company': company,
                                    'location': job_location,
                                    'posted': posted_time_raw,
                                    'url': url,
                                    'is_target': is_target,
                                    'keyword': keyword,
                                    'search_location': location
                                }
                                
                                all_jobs.append(job_info)
                                    
                        except Exception as e:
                            continue
                
                # Be nice to LinkedIn servers
                time.sleep(SEARCH_DELAY)
                
            except Exception as e:
                print(f"    Error searching {keyword} in {location}: {e}")
                continue
    
    # Final deduplication pass
    unique_jobs = []
    seen_combinations = set()
    
    for job in all_jobs:
        job_key = f"{job['title'].lower().strip()}_{job['company'].lower().strip()}"
        
        if job_key not in seen_combinations:
            seen_combinations.add(job_key)
            unique_jobs.append(job)
    
    print(f"  Removed {len(all_jobs) - len(unique_jobs)} duplicate jobs")
    
    # Filter jobs by location
    filtered_jobs = filter_jobs_by_location(unique_jobs, locations)
    print(f"  Filtered to {len(filtered_jobs)} jobs in specified locations")
    
    return filtered_jobs

def filter_jobs_by_location(jobs, allowed_locations):
    """Filter jobs to only include those in specified locations"""
    filtered = []
    filtered_out = []
    
    for job in jobs:
        job_location = job['location'].lower().strip()
        
        # Check if this is a true remote job
        is_true_remote = any(indicator in job_location for indicator in REMOTE_INDICATORS)
        
        is_allowed = False
        
        # If it's true remote, allow it (can be anywhere in US)
        if is_true_remote:
            is_allowed = True
        else:
            # For non-remote jobs, check if they're in our specified locations
            for allowed_loc in allowed_locations:
                allowed_loc_lower = allowed_loc.lower().strip()
                
                if allowed_loc_lower == "remote":
                    continue
                
                # Exact match or city matches
                if job_location == allowed_loc_lower or allowed_loc_lower in job_location:
                    is_allowed = True
                    break
        
        if is_allowed:
            filtered.append(job)
        else:
            filtered_out.append(f"{job['title']} at {job['company']} ({job_location})")
    
    # Show what was filtered out
    if filtered_out:
        print(f"    ❌ Filtered out {len(filtered_out)} jobs outside specified locations")
    
    return filtered

def analyze_job_match_with_claude(job, resume_analysis, role_analysis, api_key, cache_data=None):
    """Use Claude to analyze how well a job matches your resume"""
    
    # Check cache first if available
    if cache_data is not None:
        cached_analysis = get_cached_job_analysis(job, cache_data)
        if cached_analysis:
            return cached_analysis
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Get job description from LinkedIn (we'll use the job title and company for now)
    job_info = f"""
Job Title: {job['title']}
Company: {job['company']}
Location: {job['location']}
Posted: {job['posted']}
URL: {job['url']}
"""
    
    prompt = f"""
You are an expert job matching analyst. Compare this job posting with the candidate's resume and role requirements to determine the match quality.

JOB POSTING:
{job_info}

CANDIDATE'S RESUME ANALYSIS:
{json.dumps(resume_analysis, indent=2)}

ROLE REQUIREMENTS ANALYSIS:
{json.dumps(role_analysis, indent=2)}

CANDIDATE'S INDUSTRY PREFERENCES:
- Preferred Industries: {', '.join(PREFERRED_INDUSTRIES)}
- Industries to Avoid: {', '.join(INDUSTRIES_TO_AVOID)}

Please analyze the match between this job and the candidate's background. Consider:

1. **Skills Match**: How well do the candidate's skills align with what the job requires?
2. **Experience Level**: Is the candidate's experience level appropriate for this role?
3. **Industry/Company Fit**: Does this company/industry align with the candidate's preferred industries?
4. **Location/Remote Preferences**: Does the location/remote work match the candidate's preferences?
5. **Career Growth**: Does this role represent good career progression for the candidate?
6. **Top Candidate Keywords**: Extract 5-8 specific keywords/phrases from the job listing that would make the candidate stand out as a top candidate. These should be:
   - Technical skills mentioned in the job
   - Industry-specific terms
   - Product management methodologies
   - Tools and technologies
   - Business concepts
   - Leadership/management terms
   - Domain expertise areas
   - Certifications or qualifications mentioned

Provide your analysis in the following JSON format:

{{
    "match_level": "High Match|Medium Match|Low Match",
    "match_emoji": "🟢|🟡|🔴",
    "confidence_score": 1-10,
    "key_reasons": [
        "reason1",
        "reason2",
        "reason3"
    ],
    "skill_alignment": "excellent|good|fair|poor",
    "experience_fit": "perfect|good|fair|poor",
    "industry_fit": "excellent|good|fair|poor",
    "overall_assessment": "brief explanation of why this is a high/medium/low match",
    "top_candidate_keywords": [
        "keyword1",
        "keyword2",
        "keyword3",
        "keyword4",
        "keyword5"
    ]
}}

Guidelines:
- **High Match**: Candidate is an excellent fit with strong skill alignment, appropriate experience level, good industry fit, and good career progression
- **Medium Match**: Candidate has relevant skills and experience, but may need some development, industry learning, or the role isn't perfect
- **Low Match**: Significant gaps in skills, experience level, industry alignment, or career alignment

Industry Considerations:
- **Preferred Industries**: Give bonus points for jobs in Technology, Software, SaaS, Consumer Technology, Developer Tools, Open Source, AI/ML, Fintech
- **Industries to Avoid**: Apply penalties for jobs in Insurance, Real Estate, Manufacturing, Healthcare, Government, Non-profit, Gaming, Entertainment
- **Industry Fit**: Consider how well the company's industry aligns with the candidate's preferences and background

Be realistic and honest in your assessment. Consider both the candidate's strengths and potential gaps.

Return ONLY the JSON response, no additional text.
"""
    
    # Retry configuration
    max_retries = 3
    base_delay = 2  # seconds
    
    # Retry loop
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = response.content[0].text
            
            # Try to parse the JSON response
            try:
                analysis = json.loads(content)
                
                # Cache the successful analysis
                if cache_data is not None:
                    cache_job_analysis(job, analysis, cache_data)
                
                return analysis
            except json.JSONDecodeError:
                print(f"❌ Claude returned invalid JSON for job matching. Trying to extract JSON...")
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    try:
                        analysis = json.loads(json_match.group())
                        
                        # Cache the successful analysis
                        if cache_data is not None:
                            cache_job_analysis(job, analysis, cache_data)
                        
                        return analysis
                    except json.JSONDecodeError:
                        print(f"❌ Could not parse Claude's job matching response")
                        return None
                else:
                    print(f"❌ No JSON found in Claude's job matching response")
                    return None
                    
        except Exception as e:
            error_message = str(e)
            print(f"❌ Error calling Claude API for job matching (attempt {attempt + 1}/{max_retries}): {e}")
            
            # Check if it's a retryable error
            if "overloaded" in error_message.lower() or "529" in error_message or "rate limit" in error_message.lower():
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    print(f"⏳ API overloaded. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    continue
                else:
                    print("❌ Max retries reached. API is still overloaded.")
                    return None
            else:
                # Non-retryable error
                print("❌ Non-retryable error encountered.")
                return None
    
    return None

def analyze_job_match(job, resume_analysis, role_analysis, api_key, cache_data=None):
    """Analyze how well a job matches your resume using Claude"""
    
    # Use Claude for intelligent job matching
    claude_analysis = analyze_job_match_with_claude(job, resume_analysis, role_analysis, api_key, cache_data)
    
    if claude_analysis:
        return claude_analysis
    else:
        # Fallback to simple scoring if Claude fails
        job_text = f"{job['title']} {job['company']} {job['location']}".lower()
        
        # Simple fallback logic
        skill_matches = []
        for skill in resume_analysis.get('skills', []):
            if skill.lower() in job_text:
                skill_matches.append(skill)
        
        total_score = len(skill_matches)
        
        if total_score >= 3:
            match_level = "High Match"
            match_emoji = "🟢"
        elif total_score >= 1:
            match_level = "Medium Match"
            match_emoji = "🟡"
        else:
            match_level = "Low Match"
            match_emoji = "🔴"
        
        return {
            'match_level': match_level,
            'match_emoji': match_emoji,
            'confidence_score': total_score,
            'key_reasons': [f"Found {total_score} skill matches"],
            'skill_alignment': "good" if total_score > 0 else "poor",
            'experience_fit': "good",
            'overall_assessment': f"Fallback analysis: {total_score} skill matches found"
        }

def sort_jobs_by_match(jobs, resume_analysis, role_analysis, api_key, cache_data=None):
    """Sort jobs by match level (High, Medium, Low)"""
    for job in jobs:
        job['match_analysis'] = analyze_job_match(job, resume_analysis, role_analysis, api_key, cache_data)
    
    # Sort by match level priority and then by confidence score
    match_priority = {"High Match": 3, "Medium Match": 2, "Low Match": 1}
    
    return sorted(jobs, key=lambda x: (
        match_priority[x['match_analysis']['match_level']], 
        x['match_analysis']['confidence_score']
    ), reverse=True)

def display_jobs(jobs, role_analysis):
    """Display jobs in a nice format"""
    if not jobs:
        print("❌ No fresh jobs found in the last 24 hours.")
        return
    
    # Load hidden jobs
    hidden_jobs = load_hidden_jobs()
    
    # Filter out hidden jobs
    jobs = filter_hidden_jobs(jobs, hidden_jobs)
    
    if not jobs:
        print("❌ No fresh jobs found after filtering hidden jobs.")
        return
    
    print(f"\n✅ Found {len(jobs)} fresh {role_analysis.get('role_title', 'job')} positions:")
    print("📊 Jobs ranked by match quality (best matches first)")
    print("=" * 80)
    
    # Group jobs by match level for better display
    high_matches = [job for job in jobs if job['match_analysis']['match_level'] == "High Match"]
    medium_matches = [job for job in jobs if job['match_analysis']['match_level'] == "Medium Match"]
    low_matches = [job for job in jobs if job['match_analysis']['match_level'] == "Low Match"]
    
    # Define match level configurations
    match_levels = [
        {
            'jobs': high_matches,
            'emoji': '🟢',
            'title': 'HIGH MATCH JOBS',
            'description': 'Best opportunities',
            'show_stars': True,
            'show_industry_fit': True
        },
        {
            'jobs': medium_matches,
            'emoji': '🟡', 
            'title': 'MEDIUM MATCH JOBS',
            'description': 'Good opportunities',
            'show_stars': False,
            'show_industry_fit': False
        },
        {
            'jobs': low_matches,
            'emoji': '🔴',
            'title': 'LOW MATCH JOBS', 
            'description': 'Less suitable',
            'show_stars': False,
            'show_industry_fit': False
        }
    ]
    
    job_counter = 1
    
    for level_config in match_levels:
        jobs_list = level_config['jobs']
        if not jobs_list:
            continue
            
        print(f"\n{level_config['emoji']} {level_config['title']} ({len(jobs_list)} jobs) - {level_config['description']}:")
        print("-" * 60)
        
        for i, job in enumerate(jobs_list, 1):
            # Store job number for saving functionality
            job['job_number'] = job_counter
            
            target_badge = " 🎯" if job['is_target'] else ""
            match_badge = job['match_analysis']['match_emoji']
            
            # Add star to top 3 high matches
            star = "⭐️ " if level_config['show_stars'] and i <= 3 else ""
            
            # Check if this is a remote job
            job_location = job['location'].lower().strip()
            remote_indicators = ["remote", "work from home", "wfh", "virtual", "anywhere", "united states", "us", "usa"]
            is_remote = any(indicator in job_location for indicator in remote_indicators)
            
            # Format location with remote indicator
            location_display = job['location']
            if is_remote:
                location_display = f"{job['location']} (Remote)"
            
            print(f"{job_counter}. {star}{match_badge} {job['title']} @ {job['company']}{target_badge}")
            print(f"   Match: {job['match_analysis']['match_level']} (Confidence: {job['match_analysis']['confidence_score']}/10)")
            print(f"   Company: {job['company']}")
            print(f"   Location: {location_display}")
            print(f"   Posted: {job['posted']}")
            print(f"   Keyword: {job['keyword']}")
            print(f"   URL: {job['url']}")
            
            # Show key reasons for the match
            if job['match_analysis'].get('key_reasons'):
                print(f"   Key Reasons: {', '.join(job['match_analysis']['key_reasons'][:2])}")
                if len(job['match_analysis']['key_reasons']) > 2:
                    print(f"   ... and {len(job['match_analysis']['key_reasons']) - 2} more reasons")
            
            # Show industry fit if available (only for high matches)
            if level_config['show_industry_fit'] and job['match_analysis'].get('industry_fit'):
                print(f"   Industry Fit: {job['match_analysis']['industry_fit']}")
            
            # Show overall assessment
            if job['match_analysis'].get('overall_assessment'):
                print(f"   Assessment: {job['match_analysis']['overall_assessment']}")
            
            # Show top candidate keywords if available
            if job['match_analysis'].get('top_candidate_keywords'):
                print(f"   🎯 Top Candidate Keywords: {', '.join(job['match_analysis']['top_candidate_keywords'])}")
            
            print()
            job_counter += 1
    
    # Summary
    high_matches = sum(1 for job in jobs if job['match_analysis']['match_level'] == "High Match")
    medium_matches = sum(1 for job in jobs if job['match_analysis']['match_level'] == "Medium Match")
    low_matches = sum(1 for job in jobs if job['match_analysis']['match_level'] == "Low Match")
    
    print("📊 Match Summary:")
    print(f"   🟢 High Match: {high_matches} jobs")
    print(f"   🟡 Medium Match: {medium_matches} jobs")
    print(f"   🔴 Low Match: {low_matches} jobs")
    
    print(f"\n✨ Done! Found {len(jobs)} total jobs.")
    
    # Interactive job saving and hiding
    if jobs:
        save_selected_jobs(jobs)
        hide_selected_jobs(jobs)

def generate_customized_resume(job, api_key):
    """Generate a customized resume for a specific job using Claude"""
    try:
        # Get the original resume content
        if not os.path.exists(RESUME_PATH):
            print(f"❌ Resume file not found at: {RESUME_PATH}")
            return None
        
        resume_content = read_resume_file(RESUME_PATH)
        if not resume_content:
            return None
        
        # Create prompt for resume customization
        prompt = f"""You are an expert resume writer and career coach. I need you to customize a resume for a specific job application.

JOB DETAILS:
- Title: {job['title']}
- Company: {job['company']}
- Location: {job['location']}
- URL: {job['url']}

JOB ANALYSIS:
- Match Level: {job['match_analysis']['match_level']}
- Confidence Score: {job['match_analysis']['confidence_score']}/10
- Key Reasons for Match: {', '.join(job['match_analysis'].get('key_reasons', []))}
- Industry Fit: {job['match_analysis'].get('industry_fit', 'Not specified')}
- Overall Assessment: {job['match_analysis'].get('overall_assessment', 'Not provided')}
- Top Candidate Keywords: {', '.join(job['match_analysis'].get('top_candidate_keywords', []))}

ORIGINAL RESUME:
{resume_content}

TASK: Create a customized version of this resume that:
1. Emphasizes relevant experience and skills that match this specific job
2. Uses keywords and terminology from the job description, especially the top candidate keywords identified
3. Highlights achievements that demonstrate the required competencies
4. Adjusts the professional summary to align with the role
5. Reorganizes experience to prioritize relevant positions
6. Maintains professional formatting and readability
7. Focuses on quantifiable achievements where possible
8. Aligns with the company's industry and culture
9. Incorporates the top candidate keywords naturally throughout the resume to make the candidate stand out

Please provide the complete customized resume in a clean, professional format suitable for submission. Focus on making the candidate appear as the ideal fit for this specific role while maintaining honesty and accuracy.

RESPONSE FORMAT: Return only the customized resume text, formatted professionally with clear sections (Summary, Experience, Skills, etc.)."""

        # Call Claude API with retry logic
        client = anthropic.Anthropic(api_key=api_key)
        
        # Retry configuration
        max_retries = 3
        base_delay = 2  # seconds
        
        # Retry loop
        for attempt in range(max_retries):
            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                return response.content[0].text
                
            except Exception as e:
                error_message = str(e)
                print(f"❌ Error generating customized resume (attempt {attempt + 1}/{max_retries}): {e}")
                
                # Check if it's a retryable error
                if "overloaded" in error_message.lower() or "529" in error_message or "rate limit" in error_message.lower():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        print(f"⏳ API overloaded. Retrying in {delay} seconds...")
                        time.sleep(delay)
                        continue
                    else:
                        print("❌ Max retries reached. API is still overloaded.")
                        return None
                else:
                    # Non-retryable error
                    print("❌ Non-retryable error encountered.")
                    return None
        
        return None
        
    except Exception as e:
        print(f"Error generating customized resume: {e}")
        return None

def save_selected_jobs(jobs):
    """Interactive function to save selected jobs to a file"""
    if not jobs:
        return
    
    print(f"\n💾 Save jobs to file? (y/n): ", end="")
    save_choice = input().strip().lower()
    
    if save_choice not in ['y', 'yes']:
        print("📝 No jobs saved.")
        return
    
    print(f"\n✨ Found {len(jobs)} total jobs.")
    print("Enter job numbers to save (comma-separated, e.g., 1,3,7-9, or 'all'): ", end="")
    job_selection = input().strip()
    
    if not job_selection:
        print("❌ No jobs selected.")
        return
    
    # Parse job selection
    selected_jobs = []
    
    if job_selection.lower() == 'all':
        selected_jobs = jobs
    else:
        try:
            # Parse comma-separated numbers and ranges
            for part in job_selection.split(','):
                part = part.strip()
                if '-' in part:
                    # Handle ranges like "1-5"
                    start, end = map(int, part.split('-'))
                    for job_num in range(start, end + 1):
                        job = next((j for j in jobs if j.get('job_number') == job_num), None)
                        if job:
                            selected_jobs.append(job)
                else:
                    # Handle single numbers
                    job_num = int(part)
                    job = next((j for j in jobs if j.get('job_number') == job_num), None)
                    if job:
                        selected_jobs.append(job)
        except ValueError:
            print("❌ Invalid input. Please enter valid job numbers.")
            return
    
    if not selected_jobs:
        print("❌ No valid jobs selected.")
        return
    
    # Ask if user wants customized resumes
    print(f"\n📝 Generate customized resumes for {len(selected_jobs)} selected jobs? (y/n): ", end="")
    resume_choice = input().strip().lower()
    generate_resumes = resume_choice in ['y', 'yes']
    
    if generate_resumes:
        print("🤖 Generating customized resumes with Claude...")
    
    # Create saved jobs directory if it doesn't exist
    os.makedirs(SAVED_JOBS_DIR, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(SAVED_JOBS_DIR, f"selected_jobs_{timestamp}.txt")
    
    # Get API key for resume customization
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if generate_resumes and not api_key:
        print("⚠️  Warning: ANTHROPIC_API_KEY not set. Skipping resume customization.")
        generate_resumes = False
    
    # Write jobs to file
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Selected Jobs - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, job in enumerate(selected_jobs, 1):
                print(f"📄 Processing job {i}/{len(selected_jobs)}: {job['title']} at {job['company']}")
                
                f.write(f"{i}. {job['title']}\n")
                f.write(f"   Company: {job['company']}\n")
                f.write(f"   Location: {job['location']}\n")
                f.write(f"   Posted: {job['posted']}\n")
                f.write(f"   Match: {job['match_analysis']['match_level']} (Confidence: {job['match_analysis']['confidence_score']}/10)\n")
                f.write(f"   URL: {job['url']}\n")
                
                # Add key reasons if available
                if job['match_analysis'].get('key_reasons'):
                    f.write(f"   Key Reasons: {', '.join(job['match_analysis']['key_reasons'])}\n")
                
                # Add industry fit if available
                if job['match_analysis'].get('industry_fit'):
                    f.write(f"   Industry Fit: {job['match_analysis']['industry_fit']}\n")
                
                # Add overall assessment if available
                if job['match_analysis'].get('overall_assessment'):
                    f.write(f"   Assessment: {job['match_analysis']['overall_assessment']}\n")
                
                # Add top candidate keywords if available
                if job['match_analysis'].get('top_candidate_keywords'):
                    f.write(f"   🎯 Top Candidate Keywords: {', '.join(job['match_analysis']['top_candidate_keywords'])}\n")
                
                f.write("\n")
                
                # Generate customized resume if requested
                if generate_resumes:
                    try:
                        customized_resume = generate_customized_resume(job, api_key)
                        if customized_resume:
                            f.write("📝 CUSTOMIZED RESUME:\n")
                            f.write("-" * 40 + "\n")
                            f.write(customized_resume)
                            f.write("\n\n")
                            print(f"   ✅ Generated customized resume")
                        else:
                            print(f"   ⚠️  Failed to generate resume")
                    except Exception as e:
                        print(f"   ❌ Error generating resume: {e}")
                        f.write("📝 CUSTOMIZED RESUME: [Error generating resume]\n\n")
                
                f.write("=" * 60 + "\n\n")
        
        print(f"✅ Saved {len(selected_jobs)} jobs to {filename}")
        if generate_resumes:
            print(f"📝 Customized resumes included in the file")
        
    except Exception as e:
        print(f"❌ Error saving jobs: {e}")

def hide_selected_jobs(jobs):
    """Interactive function to hide selected jobs from future results"""
    if not jobs:
        return
    
    print(f"\n🚫 Hide jobs from future results? (y/n): ", end="")
    hide_choice = input().strip().lower()
    
    if hide_choice not in ['y', 'yes']:
        print("📝 No jobs hidden.")
        return
    
    print(f"\n✨ Found {len(jobs)} total jobs.")
    print("Enter job numbers to hide (comma-separated, e.g., 1,3,7-9, or 'all'): ", end="")
    job_selection = input().strip()
    
    if not job_selection:
        print("❌ No jobs selected.")
        return
    
    # Load hidden jobs
    hidden_jobs = load_hidden_jobs()
    
    # Parse job selection
    selected_jobs = []
    
    if job_selection.lower() == 'all':
        selected_jobs = jobs
    else:
        try:
            # Parse comma-separated numbers and ranges
            for part in job_selection.split(','):
                part = part.strip()
                if '-' in part:
                    # Handle ranges like "1-5"
                    start, end = map(int, part.split('-'))
                    for job_num in range(start, end + 1):
                        job = next((j for j in jobs if j.get('job_number') == job_num), None)
                        if job:
                            selected_jobs.append(job)
                else:
                    # Handle single numbers
                    job_num = int(part)
                    job = next((j for j in jobs if j.get('job_number') == job_num), None)
                    if job:
                        selected_jobs.append(job)
        except ValueError:
            print("❌ Invalid input. Please enter valid job numbers.")
            return
    
    if not selected_jobs:
        print("❌ No valid jobs selected.")
        return
    
    # Hide the selected jobs
    hidden_count = 0
    for job in selected_jobs:
        if not is_job_hidden(job, hidden_jobs):
            hide_job(job, hidden_jobs)
            hidden_count += 1
        else:
            print(f"⚠️  Job {job.get('job_number')} already hidden: {job['title']} at {job['company']}")
    
    print(f"✅ Hidden {hidden_count} jobs from future results")

def main():
    """Main function"""
    print("🚀 Leads - Powered by Claude AI")
    print("=" * 50)
    
    # Show cache statistics
    cache_stats = get_cache_stats()
    
    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set!")
        print("Please set your Anthropic API key:")
        print("export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    # Convert time period to human-readable format
    time_period_map = {
        "r86400": "24 hours",
        "r172800": "48 hours", 
        "r259200": "3 days",
        "r604800": "1 week",
        "r2592000": "1 month"
    }
    time_period_display = time_period_map.get(SEARCH_TIME_PERIOD, f"custom period ({SEARCH_TIME_PERIOD})")
    
    print(f"🎯 Searching for: {', '.join(KEYWORDS)}")
    print(f"📍 Locations: {', '.join(LOCATIONS)}")
    print(f"⏰ Time Period: Last {time_period_display}")
    print(f"🏭 Preferred Industries: {', '.join(PREFERRED_INDUSTRIES)}")
    print(f"❌ Industries to Avoid: {', '.join(INDUSTRIES_TO_AVOID)}")
    print()
    
    # Analyze the role first
    print("🔍 Analyzing role requirements...")
    role_analysis = analyze_role_with_claude(KEYWORDS, api_key)
    
    if not role_analysis:
        print("❌ Failed to analyze role requirements")
        return
    
    print(f"✅ Role Analysis Complete!")
    print(f"📋 Role: {role_analysis.get('role_title', 'Unknown')}")
    print(f"📝 Description: {role_analysis.get('role_description', 'No description')}")
    print(f"🔧 Required Skills: {', '.join(role_analysis.get('required_skills', [])[:5])}")
    if len(role_analysis.get('required_skills', [])) > 5:
        print(f"   ... and {len(role_analysis.get('required_skills', [])) - 5} more")
    print()
    
    # Analyze resume
    print("📄 Analyzing your resume...")
    print(f"📁 Resume path: {RESUME_PATH}")
    
    if not os.path.exists(RESUME_PATH):
        print(f"❌ Resume file not found at: {RESUME_PATH}")
        print("Please update RESUME_PATH in job_config.py to point to your resume file.")
        print("Supported formats: .pdf, .txt, .docx, .doc, .md")
        return
    
    resume_analysis = analyze_resume_file(RESUME_PATH)
    if not resume_analysis:
        print("❌ Failed to analyze resume. Please check the file format.")
        return
    
    print(f"\n⏰ Searching for jobs posted in the last {time_period_display}...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load job analysis cache
    print("📦 Loading job analysis cache...")
    job_cache = load_job_cache()
    
    # Get jobs
    jobs = get_linkedin_jobs(KEYWORDS, LOCATIONS)
    
    # Count jobs that were already cached before analysis
    already_cached_jobs = sum(1 for job in jobs if get_cached_job_analysis(job, job_cache) is not None)
    
    # Sort jobs by match level
    sorted_jobs = sort_jobs_by_match(jobs, resume_analysis, role_analysis, api_key, job_cache)
    
    # Save updated cache
    print("💾 Saving updated job analysis cache...")
    save_job_cache(job_cache)
    
    # Show cache statistics
    total_jobs = len(jobs)
    cached_jobs = already_cached_jobs
    new_analyses = total_jobs - cached_jobs
    
    print(f"\n📊 Cache Statistics:")
    print(f"   📦 Total jobs found: {total_jobs}")
    print(f"   💾 Jobs from cache: {cached_jobs}")
    print(f"   🔄 New analyses: {new_analyses}")
    if total_jobs > 0:
        cache_hit_rate = (cached_jobs / total_jobs) * 100
        print(f"   📈 Cache hit rate: {cache_hit_rate:.1f}%")
    
    # Display results and handle job saving
    display_jobs(sorted_jobs, role_analysis)

if __name__ == "__main__":
    main() 