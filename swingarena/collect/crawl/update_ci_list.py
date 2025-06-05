from bs4 import BeautifulSoup
import re
import jsonlines
import requests
from datasets import load_dataset
from concurrent.futures import ThreadPoolExecutor
import itertools
import os

# Initialize HTTP session
session = requests.Session()

# Load GitHub tokens from environment variables
tokens = os.getenv("GITHUB_TOKENS", "").split(",")
tokens = [t.strip() for t in tokens if t.strip()]
if not tokens:
    raise ValueError("GITHUB_TOKENS environment variable is empty or not set.")
token_cycle = itertools.cycle(tokens)

def get_token():
    """Get the next GitHub token from the cycle."""
    return next(token_cycle)

def get_html_page(url: str, token) -> str:
    """Fetch HTML page content."""
    headers = {
        "Accept": "text/html",
        "User-Agent": "GitHub-CI-Extractor"
    }
    if token:
        headers["Authorization"] = f"token {token}"
    try:
        response = session.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Failed to fetch HTML from {url}: {e}")
        return ""

def find_workflow_jobs(workflow_html: str, run_id: str):
    """Extract workflow jobs from HTML."""
    ci_names = []
    try:
        soup = BeautifulSoup(workflow_html, "html.parser")
        
        # Get workflow file path
        yml = None
        yml_tables = soup.find_all("table")
        if yml_tables:
            yml = yml_tables[0].get("data-tagsearch-path")
        
        if not yml:
            return []
        
        # Find jobs between summary and usage sections
        action_list = soup.find_all("a", class_="ActionListContent--visual16")
        summary_index = None
        usage_index = None
        for i, item in enumerate(action_list):
            href = item.get("href", "")
            if "/actions/runs/" in href and href.endswith(run_id):
                summary_index = i
            elif href.endswith("/usage"):
                usage_index = i
        if summary_index is not None and usage_index is not None and summary_index < usage_index:
            job_items = action_list[summary_index + 1:usage_index]
            for item in job_items:
                svg = item.find("svg", attrs={"aria-label": True})
                if svg:
                    label_span = item.find("span", class_="ActionListItem-label")
                    if label_span:
                        job_name = label_span.get_text(strip=True)
                        if job_name:
                            ci_names.append((job_name, yml))
        
        # Alternative approach: find by job label classes
        if not ci_names:
            job_labels = soup.find_all("span", class_="ActionListItem-label")
            for label in job_labels:
                job_name = label.get_text(strip=True)
                if job_name and job_name.lower() not in ["summary", "usage", "artifacts"]:
                    ci_names.append((job_name, yml))
        
        # Look for job sections
        if not ci_names:
            job_sections = soup.find_all(class_=lambda c: c and ("job-" in c or "workflow-job" in c))
            for section in job_sections:
                name_elem = section.find(["span", "div", "h3"], class_=lambda c: c and ("name" in c or "title" in c))
                if name_elem:
                    job_name = name_elem.get_text(strip=True)
                    if job_name:
                        ci_names.append((job_name, yml))
    except Exception as e:
        print(f"Error extracting jobs from workflow HTML: {e}")
    return ci_names

def extract_ci_name_list(pull: dict):
    """Extract CI job names and workflow files from a pull request."""
    try:
        repo_full_name = pull["repo"]
        pr_number = pull["instance_id"].split("-")[-1]
    except KeyError as e:
        print(f"Invalid input format, missing key: {e}")
        return []
    
    checks_url = f"https://github.com/{repo_full_name}/pull/{pr_number}/checks"
    print(f"Processing {repo_full_name} {pr_number} at {checks_url}")
    
    # Get checks page
    checks_html = get_html_page(checks_url, get_token())
    if not checks_html:
        print("Failed to fetch checks page")
        return []
    
    # Find workflow run IDs
    runs_url_prefix = f"{repo_full_name}/actions/runs/"
    runs_url_ptn = re.compile(rf"{runs_url_prefix}(\d+)")
    matches = runs_url_ptn.findall(checks_html)
    
    all_ci_names = []
    # Process each unique run ID
    for run_id in set(matches):
        workflow_url = f"https://github.com/{repo_full_name}/actions/runs/{run_id}/workflow"
        workflow_html = get_html_page(workflow_url, get_token())
        if not workflow_html:
            continue
        ci_names = find_workflow_jobs(workflow_html, run_id)
        all_ci_names.extend(ci_names)
    
    # Return unique CI names
    return list(set(all_ci_names))

# Load dataset
ds = load_dataset("SwingBench/SwingBench")["Rust"]
ds = list(ds)
# Write data incrementally
with jsonlines.open("tasks_with_ci.jsonl", "w") as f:
    with ThreadPoolExecutor(max_workers=64) as executor:
        for i, result in enumerate(executor.map(extract_ci_name_list, ds)):
            ds[i]['created_at'] = str(ds[i]['created_at'])
            ds[i]["ci_name_list"] = result
            f.write(ds[i])