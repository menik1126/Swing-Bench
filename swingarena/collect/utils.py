from __future__ import annotations


import logging
import re
import requests
import time

from bs4 import BeautifulSoup
from ghapi.core import GhApi
from fastcore.net import HTTP404NotFoundError, HTTP403ForbiddenError
from typing import Callable, Iterator, Optional, List, Tuple, Optional, Dict
from unidiff import PatchSet
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests
PR_KEYWORDS = {
    "close",
    "closes",
    "closed",
    "fix",
    "fixes",
    "fixed",
    "resolve",
    "resolves",
    "resolved",
}


class Repo:
    def __init__(self, owner: str, name: str, token: Optional[str] = None):
        """
        Init to retrieve target repository and create ghapi tool

        Args:
            owner (str): owner of target repository
            name (str): name of target repository
            token (str): github token
        """
        self.owner = owner
        self.name = name
        self.token = token
        self.api = GhApi(token=token)
        self.repo = self.call_api(self.api.repos.get, owner=owner, repo=name)

    def call_api(self, func: Callable, **kwargs) -> dict | None:
        """
        API call wrapper with rate limit handling (checks every 5 minutes if rate limit is reset)

        Args:
            func (callable): API function to call
            **kwargs: keyword arguments to pass to API function
        Return:
            values (dict): response object of `func`
        """
        while True:
            try:
                values = func(**kwargs)
                return values
            except HTTP403ForbiddenError:
                while True:
                    rl = self.api.rate_limit.get()
                    logger.info(
                        f"[{self.owner}/{self.name}] Rate limit exceeded for token {self.token[:10]}, "
                        f"waiting for 5 minutes, remaining calls: {rl.resources.core.remaining}"
                    )
                    if rl.resources.core.remaining > 0:
                        break
                    time.sleep(60 * 5)
            except HTTP404NotFoundError:
                logger.info(f"[{self.owner}/{self.name}] Resource not found {kwargs}")
                return None

    def extract_resolved_issues(self, pull: dict) -> list[str]:
        """
        Extract list of issues referenced by a PR

        Args:
            pull (dict): PR dictionary object from GitHub
        Return:
            resolved_issues (list): list of issue numbers referenced by PR
        """
        # Define 1. issue number regex pattern 2. comment regex pattern 3. keywords
        issues_pat = re.compile(r"(\w+)\s+\#(\d+)")
        comments_pat = re.compile(r"(?s)<!--.*?-->")

        # Construct text to search over for issue numbers from PR body and commit messages
        text = pull.title if pull.title else ""
        text += "\n" + (pull.body if pull.body else "")
        commits = self.get_all_loop(
            self.api.pulls.list_commits, pull_number=pull.number, quiet=True
        )
        commit_messages = [commit.commit.message for commit in commits]
        commit_text = "\n".join(commit_messages) if commit_messages else ""
        text += "\n" + commit_text
        # Remove comments from text
        text = comments_pat.sub("", text)
        # Look for issue numbers in text via scraping <keyword, number> patterns
        references = dict(issues_pat.findall(text))
        resolved_issues = list()
        if references:
            for word, issue_num in references.items():
                if word.lower() in PR_KEYWORDS:
                    resolved_issues.append(issue_num)
        return resolved_issues

    def get_all_loop(
        self,
        func: Callable,
        per_page: int = 100,
        num_pages: Optional[int] = None,
        quiet: bool = False,
        **kwargs,
    ) -> Iterator:
        """
        Return all values from a paginated API endpoint.

        Args:
            func (callable): API function to call
            per_page (int): number of values to return per page
            num_pages (int): number of pages to return
            quiet (bool): whether to print progress
            **kwargs: keyword arguments to pass to API function
        """
        page = 1
        args = {
            "owner": self.owner,
            "repo": self.name,
            "per_page": per_page,
            **kwargs,
        }
        while True:
            try:
                # Get values from API call
                values = func(**args, page=page)
                yield from values
                if len(values) == 0:
                    break
                if not quiet:
                    rl = self.api.rate_limit.get()
                    logger.info(
                        f"[{self.owner}/{self.name}] Processed page {page} ({per_page} values per page). "
                        f"Remaining calls: {rl.resources.core.remaining}"
                    )
                if num_pages is not None and page >= num_pages:
                    break
                page += 1
            except Exception as e:
                # Rate limit handling
                logger.error(
                    f"[{self.owner}/{self.name}] Error processing page {page} "
                    f"w/ token {self.token[:10]} - {e}"
                )
                while True:
                    rl = self.api.rate_limit.get()
                    if rl.resources.core.remaining > 0:
                        break
                    logger.info(
                        f"[{self.owner}/{self.name}] Waiting for rate limit reset "
                        f"for token {self.token[:10]}, checking again in 5 minutes"
                    )
                    time.sleep(60 * 5)
        if not quiet:
            logger.info(
                f"[{self.owner}/{self.name}] Processed {(page - 1) * per_page + len(values)} values"
            )

    def get_all_issues(
        self,
        per_page: int = 100,
        num_pages: Optional[int] = None,
        direction: str = "desc",
        sort: str = "created",
        state: str = "closed",
        quiet: bool = False,
    ) -> Iterator:
        """
        Wrapper for API call to get all issues from repo

        Args:
            per_page (int): number of issues to return per page
            num_pages (int): number of pages to return
            direction (str): direction to sort issues
            sort (str): field to sort issues by
            state (str): state of issues to look for
            quiet (bool): whether to print progress
        """
        issues = self.get_all_loop(
            self.api.issues.list_for_repo,
            num_pages=num_pages,
            per_page=per_page,
            direction=direction,
            sort=sort,
            state=state,
            quiet=quiet,
        )
        return issues

    def get_all_pulls(
        self,
        per_page: int = 100,
        num_pages: Optional[int] = None,
        direction: str = "desc",
        sort: str = "created",
        state: str = "closed",
        quiet: bool = False,
    ) -> Iterator:
        """
        Wrapper for API call to get all PRs from repo

        Args:
            per_page (int): number of PRs to return per page
            num_pages (int): number of pages to return
            direction (str): direction to sort PRs
            sort (str): field to sort PRs by
            state (str): state of PRs to look for
            quiet (bool): whether to print progress
        """
        pulls = self.get_all_loop(
            self.api.pulls.list,
            num_pages=num_pages,
            direction=direction,
            per_page=per_page,
            sort=sort,
            state=state,
            quiet=quiet,
        )
        return pulls


def extract_problem_statement_and_hints(pull: dict, repo: Repo) -> tuple[str, str]:
    """
    Extract problem statement from issues associated with a pull request

    Args:
        pull (dict): PR dictionary object from GitHub
        repo (Repo): Repo object
    Return:
        text (str): problem statement
        hints (str): hints
    """
    if repo.name == "django":
        return extract_problem_statement_and_hints_django(pull, repo)
    text = ""
    all_hint_texts = list()
    for issue_number in pull["resolved_issues"]:
        issue = repo.call_api(
            repo.api.issues.get,
            owner=repo.owner,
            repo=repo.name,
            issue_number=issue_number,
        )
        if issue is None:
            continue
        title = issue.title if issue.title else ""
        body = issue.body if issue.body else ""
        text += f"{title}\n{body}\n"
        issue_number = issue.number
        hint_texts = _extract_hints(pull, repo, issue_number)
        hint_text = "\n".join(hint_texts)
        all_hint_texts.append(hint_text)
    return text, "\n".join(all_hint_texts) if all_hint_texts else ""


def _extract_hints(pull: dict, repo: Repo, issue_number: int) -> list[str]:
    """
    Extract hints from comments associated with a pull request (before first commit)

    Args:
        pull (dict): PR dictionary object from GitHub
        repo (Repo): Repo object
        issue_number (int): issue number
    Return:
        hints (list): list of hints
    """
    # Get all commits in PR
    commits = repo.get_all_loop(
        repo.api.pulls.list_commits, pull_number=pull["number"], quiet=True
    )
    commits = list(commits)
    if len(commits) == 0:
        # If there are no comments, return no hints
        return []
    # Get time of first commit in PR
    commit_time = commits[0].commit.author.date  # str
    commit_time = time.mktime(time.strptime(commit_time, "%Y-%m-%dT%H:%M:%SZ"))
    # Get all comments in PR
    all_comments = repo.get_all_loop(
        repo.api.issues.list_comments, issue_number=issue_number, quiet=True
    )
    all_comments = list(all_comments)
    # Iterate through all comments, only keep comments created before first commit
    comments = list()
    for comment in all_comments:
        comment_time = time.mktime(
            time.strptime(comment.updated_at, "%Y-%m-%dT%H:%M:%SZ")
        )  # use updated_at instead of created_at
        if comment_time < commit_time:
            comments.append(comment)
        else:
            break
        # only include information available before the first commit was created
    # Keep text from comments
    comments = [comment.body for comment in comments]
    return comments


def extract_patches(pull: dict, repo: Repo) -> tuple[str, str]:
    """
    Get patch and test patch from PR

    Args:
        pull (dict): PR dictionary object from GitHub
        repo (Repo): Repo object
    Return:
        patch_change_str (str): gold patch
        patch_test_str (str): test patch
    """
    patch = requests.get(pull["diff_url"]).text
    patch_test = ""
    patch_fix = ""
    for hunk in PatchSet(patch):
        if any(
            test_word in hunk.path for test_word in ["test", "tests", "e2e", "testing"]
        ):
            patch_test += str(hunk)
        else:
            patch_fix += str(hunk)
    return patch_fix, patch_test


### MARK: Repo Specific Parsing Functions ###
def extract_problem_statement_and_hints_django(
    pull: dict, repo: Repo
) -> tuple[str, list[str]]:
    """
    Get problem statement and hints from issues associated with a pull request

    Args:
        pull (dict): PR dictionary object from GitHub
        repo (Repo): Repo object
    Return:
        text (str): problem statement
        hints (str): hints
    """
    text = ""
    all_hints_text = list()
    for issue_number in pull["resolved_issues"]:
        url = f"https://code.djangoproject.com/ticket/{issue_number}"
        resp = requests.get(url)
        if resp.status_code != 200:
            continue
        soup = BeautifulSoup(resp.text, "html.parser")

        # Get problem statement (title + body)
        issue_desc = soup.find("div", {"id": "ticket"})
        title = issue_desc.find("h1", class_="searchable").get_text()
        title = re.sub(r"\s+", " ", title).strip()
        body = issue_desc.find("div", class_="description").get_text()
        body = re.sub(r"\n+", "\n", body)
        body = re.sub(r"    ", "\t", body)
        body = re.sub(r"[ ]{2,}", " ", body).strip()
        text += f"{title}\n{body}\n"

        # Get time of first commit in PR
        commits = repo.get_all_loop(
            repo.api.pulls.list_commits, pull_number=pull["number"], quiet=True
        )
        commits = list(commits)
        if len(commits) == 0:
            continue
        commit_time = commits[0].commit.author.date
        commit_time = time.mktime(time.strptime(commit_time, "%Y-%m-%dT%H:%M:%SZ"))

        # Get all comments before first commit
        comments_html = soup.find("div", {"id": "changelog"})
        div_blocks = comments_html.find_all("div", class_="change")
        # Loop through each div block
        for div_block in div_blocks:
            # Find the comment text and timestamp
            comment_resp = div_block.find("div", class_="comment")
            timestamp_resp = div_block.find("a", class_="timeline")
            if comment_resp is None or timestamp_resp is None:
                continue

            comment_text = re.sub(r"\s+", " ", comment_resp.text).strip()
            timestamp = timestamp_resp["title"]
            if timestamp.startswith("See timeline at "):
                timestamp = timestamp[len("See timeline at ") :]
            if "/" in timestamp:
                timestamp = time.mktime(time.strptime(timestamp, "%m/%d/%y %H:%M:%S"))
            elif "," in timestamp:
                timestamp = time.mktime(
                    time.strptime(timestamp, "%b %d, %Y, %I:%M:%S %p")
                )
            else:
                raise ValueError(f"Timestamp format not recognized: {timestamp}")

            # Append the comment and timestamp as a tuple to the comments list
            if timestamp < commit_time:
                all_hints_text.append((comment_text, timestamp))

    return text, all_hints_text

def extract_base_job_name(job_name: str) -> str:
    """Extract base job name by removing matrix parameters

    Examples:
        'test (windows-latest, 3.10, conda)' -> 'test'
        'Build wheel and sdist' -> 'Build wheel and sdist'
        'lint / flake8' -> 'lint / flake8'

    Args:
        job_name: Full job name from GitHub API

    Returns:
        Base job name without matrix parameters
    """
    # Remove matrix parameters in parentheses at the end
    if '(' in job_name and job_name.rstrip().endswith(')'):
        return job_name.split('(')[0].strip()
    return job_name


def extract_ci_name_list(pull: dict, token: Optional[str] = None) -> List[Tuple[str, str]]:
    """Extract CI job names and workflow files from a PR using GitHub API

    Args:
        pull: Pull Request data dictionary
        token: GitHub API token (optional, uses environment variable if not provided)

    Returns:
        List of tuples containing (ci_job_name, workflow_file_path)
    """
    try:
        repo_full_name = pull['base']['repo']['full_name']
        pr_number = pull['number']
        owner, repo = repo_full_name.split('/')
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid input format: {e}")
        return []

    # Get token from environment if not provided
    if not token:
        import os
        token = os.getenv('GITHUB_TOKEN') or os.getenv('GITHUB_TOKENS', '').split(',')[0]

    if not token:
        logger.warning("No GitHub token provided, API rate limits may apply")

    try:
        # Initialize GitHub API client
        api = GhApi(token=token) if token else GhApi()

        logger.info(f"Fetching workflow runs for {repo_full_name} PR #{pr_number}")

        # Get the head SHA from the PR
        try:
            pr_data = api.pulls.get(owner=owner, repo=repo, pull_number=pr_number)
            head_sha = pr_data.head.sha
        except Exception as e:
            # Fallback: try to get from pull dict
            head_sha = pull.get('head', {}).get('sha')
            if not head_sha:
                logger.error(f"Could not get head SHA for PR #{pr_number}: {e}")
                return []

        # Get workflow runs for this commit
        all_ci_names = []
        try:
            runs = api.actions.list_workflow_runs_for_repo(
                owner=owner,
                repo=repo,
                head_sha=head_sha,
                per_page=100
            )

            if not runs or not runs.workflow_runs:
                logger.warning(f"No workflow runs found for {repo_full_name} PR #{pr_number}")
                return []

            logger.info(f"Found {len(runs.workflow_runs)} workflow runs")

            # Process each workflow run
            for run in runs.workflow_runs:
                run_id = run.id
                workflow_path = run.path  # e.g., '.github/workflows/test.yml'

                # Get jobs for this workflow run
                try:
                    jobs_response = api.actions.list_jobs_for_workflow_run(
                        owner=owner,
                        repo=repo,
                        run_id=run_id,
                        per_page=100
                    )

                    if jobs_response and jobs_response.jobs:
                        for job in jobs_response.jobs:
                            job_name = job.name
                            # Extract base job name (remove matrix parameters)
                            base_job_name = extract_base_job_name(job_name)
                            all_ci_names.append((base_job_name, workflow_path))

                except Exception as e:
                    logger.warning(f"Could not fetch jobs for run {run_id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching workflow runs: {e}")
            return []

        # Remove duplicates while preserving order
        seen = set()
        unique_ci_names = []
        for item in all_ci_names:
            if item not in seen:
                seen.add(item)
                unique_ci_names.append(item)

        logger.info(f"Extracted {len(unique_ci_names)} unique CI jobs")
        return unique_ci_names

    except Exception as e:
        logger.error(f"Error extracting CI names: {e}")
        return []

# Create a session with retry capability
session = requests.Session()
retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)


def make_github_request(url: str, params: Optional[Dict] = None, token: Optional[str] = None) -> Dict:
    """Send GET request to GitHub API
    
    Args:
        url: API endpoint URL
        params: Request parameters
        token: GitHub API token
        
    Returns:
        API response JSON
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-CI-Extractor"
    }
    if token:
        headers["Authorization"] = f"token {token}"
        
    try:
        response = session.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 403 and "rate limit" in response.text.lower():
            reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
            wait_time = max(0, reset_time - time.time()) + 1
            logger.warning(f"Rate limit exceeded. Waiting {wait_time:.1f} seconds")
            time.sleep(wait_time)
            return make_github_request(url, params, token)  # Retry
        else:
            logger.error(f"HTTP error: {e}")
            return {}
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return {}


def get_html_page(url: str, token: Optional[str] = None) -> str:
    """Get HTML page content
    
    Args:
        url: Page URL
        token: GitHub API token
        
    Returns:
        HTML content
    """
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
        logger.error(f"Failed to fetch HTML from {url}: {e}")
        return ""


def find_workflow_jobs(workflow_html: str, run_id: str) -> List[Tuple[str, str]]:
    """Extract workflow jobs from workflow HTML
    
    Args:
        workflow_html: Workflow page HTML content
        run_id: Run ID for reference
        
    Returns:
        List of (job_name, workflow_file) tuples
    """
    ci_names = []
    try:
        soup = BeautifulSoup(workflow_html, "html.parser")
        
        # Get workflow file path
        yml = None
        yml_tables = soup.find_all('table')
        if yml_tables and len(yml_tables) > 0:
            yml = yml_tables[0].get('data-tagsearch-path')
        
        if not yml:
            return []
        
        # Method 1: Find jobs between summary and usage sections
        action_list = soup.find_all("a", class_="ActionListContent--visual16")
        
        summary_index = None
        usage_index = None
        
        for i, item in enumerate(action_list):
            href = item.get('href', '')
            if '/actions/runs/' in href and href.endswith(run_id):
                summary_index = i
            elif href.endswith('/usage'):
                usage_index = i
        
        if summary_index is not None and usage_index is not None and summary_index < usage_index:
            job_items = action_list[summary_index + 1:usage_index]
            for item in job_items:
                svg = item.find('svg', attrs={'aria-label': True})
                if svg:
                    label_span = item.find('span', class_='ActionListItem-label')
                    if label_span:
                        job_name = label_span.get_text(strip=True)
                        if job_name:
                            ci_names.append((job_name, yml))
        
        # Method 2: Alternative approach - find by job label classes
        if not ci_names:
            job_labels = soup.find_all('span', class_='ActionListItem-label')
            for label in job_labels:
                job_name = label.get_text(strip=True)
                if job_name and job_name.lower() not in ['summary', 'usage', 'artifacts']:
                    ci_names.append((job_name, yml))
        
        # Method 3: Look for job sections
        if not ci_names:
            job_sections = soup.find_all(class_=lambda c: c and ('job-' in c or 'workflow-job' in c))
            for section in job_sections:
                name_elem = section.find(['span', 'div', 'h3'], class_=lambda c: c and ('name' in c or 'title' in c))
                if name_elem:
                    job_name = name_elem.get_text(strip=True)
                    if job_name:
                        ci_names.append((job_name, yml))
                        
    except Exception as e:
        logger.warning(f"Error extracting jobs from workflow HTML: {e}")
    
    return ci_names

if __name__ == '__main__':
    pull = dict()
    pull['base'] = dict()
    pull['base']['repo'] = dict()
    pull['base']['repo']['full_name'] = 'astral-sh/uv'
    pull['number'] = 11833
    print(extract_ci_name_list(pull))
    