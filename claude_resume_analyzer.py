#!/usr/bin/env python3
"""
Claude-based Resume Analyzer for Product Management Roles

AI-Powered Match Scoring
========================
Jobs are analyzed by Claude AI and scored based on:

Match Levels
------------
- 🟢 **High Match**: Excellent fit with strong skill alignment, appropriate experience level, and good industry fit
- 🟡 **Medium Match**: Good fit with relevant skills, but may need some development or industry learning
- 🔴 **Low Match**: Significant gaps in skills, experience level, industry alignment, or career alignment

Scoring Factors
--------------
- **Skills Match**: How well your skills align with job requirements
- **Experience Level**: Whether your experience level is appropriate for the role
- **Industry Fit**: How well the company's industry aligns with your preferences (preferred industries get bonuses, avoided industries get penalties)
- **Location/Remote**: Whether the location and remote work options match your preferences
- **Career Growth**: Whether the role represents good career progression
- **Target Company**: Bonus for companies you're particularly interested in
"""

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
import anthropic
from typing import Dict, List, Optional

# Cache file location
CACHE_FILE = "resume_analysis_cache.json"

def get_file_hash(file_path: str) -> str:
    """Generate a hash of the file content to detect changes"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            return hashlib.md5(content).hexdigest()
    except Exception as e:
        print(f"⚠️  Warning: Could not generate hash for {file_path}: {e}")
        return ""

def get_file_metadata(file_path: str) -> Dict:
    """Get file metadata for change detection"""
    try:
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'mtime': stat.st_mtime,
            'hash': get_file_hash(file_path)
        }
    except Exception as e:
        print(f"⚠️  Warning: Could not get metadata for {file_path}: {e}")
        return {}

def load_cached_analysis(file_path: str) -> Optional[Dict]:
    """Load cached analysis if available and file hasn't changed"""
    try:
        if not os.path.exists(CACHE_FILE):
            return None
        
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        
        if file_path not in cache:
            return None
        
        cached_data = cache[file_path]
        current_metadata = get_file_metadata(file_path)
        
        # Check if file has changed
        if (cached_data.get('metadata', {}).get('hash') == current_metadata.get('hash') and
            cached_data.get('metadata', {}).get('size') == current_metadata.get('size') and
            cached_data.get('metadata', {}).get('mtime') == current_metadata.get('mtime')):
            
            print(f"📋 Using cached analysis for {file_path}")
            return cached_data.get('analysis')
        else:
            print(f"📝 Resume file has changed, re-analyzing {file_path}")
            return None
            
    except Exception as e:
        print(f"⚠️  Warning: Could not load cache: {e}")
        return None

def save_cached_analysis(file_path: str, analysis: Dict):
    """Save analysis results to cache"""
    try:
        # Load existing cache or create new one
        cache = {}
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        
        # Add new analysis with metadata
        cache[file_path] = {
            'analysis': analysis,
            'metadata': get_file_metadata(file_path),
            'cached_at': datetime.now().isoformat()
        }
        
        # Save cache
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        
        print(f"💾 Cached analysis for {file_path}")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not save cache: {e}")

def clear_cache():
    """Clear the resume analysis cache"""
    try:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print(f"🗑️  Cleared resume analysis cache")
        else:
            print(f"📋 No cache file found to clear")
    except Exception as e:
        print(f"❌ Error clearing cache: {e}")

def get_cache_info() -> Dict:
    """Get information about the cache"""
    try:
        if not os.path.exists(CACHE_FILE):
            return {'cached_files': 0, 'cache_size': 0}
        
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
        
        cache_size = os.path.getsize(CACHE_FILE)
        
        return {
            'cached_files': len(cache),
            'cache_size': cache_size,
            'files': list(cache.keys())
        }
    except Exception as e:
        print(f"⚠️  Warning: Could not get cache info: {e}")
        return {'cached_files': 0, 'cache_size': 0}

def find_resume_files() -> List[str]:
    """Find resume files in the current directory"""
    resume_files = []
    current_dir = Path('.')
    
    # Common resume file patterns
    resume_patterns = [
        '*resume*', '*cv*', '*curriculum*', '*vitae*'
    ]
    
    # Common file extensions
    extensions = ['.pdf', '.txt', '.docx', '.doc', '.md']
    
    for pattern in resume_patterns:
        for ext in extensions:
            files = list(current_dir.glob(f"{pattern}{ext}"))
            resume_files.extend([str(f) for f in files])
    
    # Remove duplicates and return
    return list(set(resume_files))

def read_resume_file(file_path: str) -> Optional[str]:
    """Read resume file content"""
    try:
        # For text files
        if file_path.endswith(('.txt', '.md')):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        # For PDF files (basic text extraction)
        elif file_path.endswith('.pdf'):
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    return text
            except ImportError:
                print("⚠️  PyPDF2 not installed. Please install it with: pip install PyPDF2")
                return None
        
        # For Word documents
        elif file_path.endswith(('.docx', '.doc')):
            try:
                from docx import Document
                doc = Document(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                print("⚠️  python-docx not installed. Please install it with: pip install python-docx")
                return None
        
        else:
            print(f"❌ Unsupported file format: {file_path}")
            return None
            
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

def analyze_resume_with_claude(resume_text: str, api_key: str) -> Dict:
    """Use Claude to analyze resume against product management criteria"""
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Product management keywords and functions from flexible_job_finder.py
    pm_keywords = [
        "product manager", "technical product manager", "senior product manager", 
        "growth product manager", "product owner", "associate product manager",
        "product strategy", "product roadmap", "user research", "market research",
        "agile", "scrum", "kanban", "sprint planning", "backlog management",
        "user stories", "requirements gathering", "stakeholder management",
        "data analysis", "analytics", "metrics", "KPIs", "A/B testing",
        "wireframes", "prototyping", "user experience", "UX", "UI",
        "go-to-market", "GTM", "launch", "feature development",
        "customer feedback", "user interviews", "competitive analysis",
        "business case", "ROI", "revenue", "growth", "retention",
        "cross-functional", "engineering", "design", "marketing", "sales"
    ]
    
    prompt = f"""
You are an expert product management recruiter analyzing a resume for product management roles.

RESUME TEXT:
{resume_text}

PRODUCT MANAGEMENT KEYWORDS TO EVALUATE:
{', '.join(pm_keywords)}

Please analyze this resume and provide a structured response in the following JSON format:

{{
    "skills": [
        "skill1",
        "skill2",
        "skill3"
    ],
    "experience_level": "junior|mid_level|senior",
    "has_remote_experience": true/false,
    "has_management_experience": true/false,
    "years_of_experience": number,
    "key_achievements": [
        "achievement1",
        "achievement2"
    ],
    "relevant_industries": [
        "industry1",
        "industry2"
    ],
    "strengths": [
        "strength1",
        "strength2"
    ],
    "areas_for_growth": [
        "area1",
        "area2"
    ],
    "overall_assessment": "brief assessment of fit for PM roles"
}}

Guidelines:
1. Extract ALL relevant skills from the resume that match or relate to the PM keywords
2. Assess experience level based on years, titles, and responsibilities
3. Look for remote work experience
4. Identify management/leadership experience
5. Be comprehensive but accurate - only include skills/experience that are clearly present
6. For experience_level: "junior" (0-2 years), "mid_level" (3-7 years), "senior" (8+ years)
7. Focus on transferable skills and PM-relevant experience

Return ONLY the JSON response, no additional text.
"""
    
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
        
        # Extract JSON from response
        content = response.content[0].text
        import json
        
        # Try to parse the JSON response
        try:
            analysis = json.loads(content)
            return analysis
        except json.JSONDecodeError:
            print("❌ Claude returned invalid JSON. Trying to extract JSON...")
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    analysis = json.loads(json_match.group())
                    return analysis
                except json.JSONDecodeError:
                    print("❌ Could not parse Claude's response")
                    return None
            else:
                print("❌ No JSON found in Claude's response")
                return None
                
    except Exception as e:
        print(f"❌ Error calling Claude API: {e}")
        return None

def analyze_resume_file(file_path: str) -> Optional[Dict]:
    """Analyze a resume file using Claude with caching"""
    
    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY environment variable not set!")
        print("Please set your Anthropic API key:")
        print("export ANTHROPIC_API_KEY='your-api-key-here'")
        return None
    
    # Check for cached analysis first
    cached_analysis = load_cached_analysis(file_path)
    if cached_analysis:
        print(f"✅ Using cached analysis for {file_path}")
        print(f"🔍 Found {len(cached_analysis.get('skills', []))} relevant skills")
        print(f"📊 Experience level: {cached_analysis.get('experience_level', 'Unknown')}")
        return cached_analysis
    
    # Read resume
    resume_text = read_resume_file(file_path)
    if not resume_text:
        return None
    
    print(f"📄 Analyzing resume: {file_path}")
    print(f"📝 Resume length: {len(resume_text)} characters")
    
    # Analyze with Claude
    analysis = analyze_resume_with_claude(resume_text, api_key)
    
    if analysis:
        print("✅ Resume analysis complete!")
        print(f"🔍 Found {len(analysis.get('skills', []))} relevant skills")
        print(f"📊 Experience level: {analysis.get('experience_level', 'Unknown')}")
        
        # Cache the analysis
        save_cached_analysis(file_path, analysis)
        
        return analysis
    else:
        print("❌ Failed to analyze resume")
        return None

def main():
    """Test the resume analyzer"""
    print("🔍 Claude Resume Analyzer for Product Management")
    print("=" * 50)
    
    # Show cache information
    cache_info = get_cache_info()
    print(f"📋 Cache Status: {cache_info['cached_files']} files cached ({cache_info['cache_size']} bytes)")
    
    # Find resume files
    resume_files = find_resume_files()
    
    if not resume_files:
        print("❌ No resume files found!")
        print("Please add your resume to this folder with 'resume' or 'cv' in the filename.")
        print("Supported formats: .pdf, .txt, .docx, .doc, .md")
        return
    
    print(f"📁 Found {len(resume_files)} resume file(s):")
    for file in resume_files:
        print(f"  - {file}")
    
    # Analyze first resume
    analysis = analyze_resume_file(resume_files[0])
    
    if analysis:
        print("\n📊 Analysis Results:")
        print(f"Skills: {', '.join(analysis.get('skills', []))}")
        print(f"Experience Level: {analysis.get('experience_level', 'Unknown')}")
        print(f"Remote Experience: {analysis.get('has_remote_experience', False)}")
        print(f"Management Experience: {analysis.get('has_management_experience', False)}")
        print(f"Years of Experience: {analysis.get('years_of_experience', 'Unknown')}")
        print(f"Overall Assessment: {analysis.get('overall_assessment', 'No assessment provided')}")
        
        # Show updated cache info
        updated_cache_info = get_cache_info()
        print(f"\n💾 Cache updated: {updated_cache_info['cached_files']} files cached")

if __name__ == "__main__":
    main() 