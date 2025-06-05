import requests
import time
import json
import logging
import os
import re
from bs4 import BeautifulSoup
from typing import Optional, Dict, List, Any
from urllib.parse import urljoin, quote
from dataclasses import dataclass
from datetime import datetime
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle

@dataclass
class PackageData:
    id: str
    name: str
    language: str
    description: Optional[str]
    downloads: int
    stars: int
    created_at: Optional[str]
    updated_at: Optional[str]
    version: Optional[str]
    repository: Optional[str]
    license: Optional[str]
    homepage: Optional[str]
    keywords: List[str]
    authors: List[str]

class BasePackageCrawler:
    def __init__(
        self,
        output_dir: str = "package_data",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30,
        max_packages: int = 5000,
        github_tokens: Optional[List[str]] = None,
        log_level: int = logging.INFO
    ):
        self.output_dir = output_dir
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.max_packages = max_packages
        self.session = requests.Session()
        self.total_collected = 0
        
        # Setup GitHub tokens
        self.github_tokens = github_tokens or os.getenv("GH_TOKENS", "").split(",")
        if not self.github_tokens or not any(self.github_tokens):
            self.logger.warning("No GitHub tokens provided. API rate limits will be restricted.")
            self.github_tokens = [""]  # Use empty token as fallback
        self.token_iterator = cycle(self.github_tokens)  # Create a round-robin iterator for tokens
        
        os.makedirs(output_dir, exist_ok=True)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def make_request(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        default_headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        if headers:
            default_headers.update(headers)
            
        # Add GitHub token if requesting from GitHub API
        if "api.github.com" in url:
            token = next(self.token_iterator)
            if token:
                default_headers["Authorization"] = f"token {token}"
            
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, params=params, headers=default_headers, timeout=self.timeout)
                
                if response.status_code == 200:
                    # First check if URL contains pkg.go.dev - if so, return HTML content
                    if "pkg.go.dev" in url:
                        return {"html_content": response.text}
                    
                    # For other URLs (like GitHub API), try JSON
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        return {"html_content": response.text}
                
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 5
                    self.logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
            except requests.RequestException as e:
                self.logger.error(f"Request failed: {e}. Attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                return {}

        self.logger.error(f"Failed to fetch from {url} after all retry attempts")
        return {}
    
    def save_package_batch(self, packages: List[PackageData], language: str):
        output_file = os.path.join(self.output_dir, f"{language}_packages.jsonl")
        
        with open(output_file, 'a', encoding='utf-8') as f:
            for package in packages:
                f.write(json.dumps(vars(package), ensure_ascii=False) + '\n')
                
        self.total_collected += len(packages)
        self.logger.info(f"Saved batch of {len(packages)} {language} packages. Total collected: {self.total_collected}")
    
    def crawl_all(self):
        pass

class RustCratesCrawler(BasePackageCrawler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://crates.io/api/v1/crates"
        self.per_page = 90
    
    def fetch_page(self, page_param: Optional[str] = None) -> dict:
        url = self.base_url
        if page_param:
            url = urljoin(url, f"?{page_param}")
        else:
            url = f"{url}?per_page={self.per_page}"
        
        return self.make_request(url)
    
    def process_crate(self, crate: Dict) -> PackageData:
        return PackageData(
            id=crate.get("id", ""),
            name=crate.get("name", ""),
            language="rust",
            description=crate.get("description"),
            downloads=crate.get("downloads", 0),
            stars=crate.get("recent_downloads", 0),  # Using recent_downloads as a proxy
            created_at=crate.get("created_at"),
            updated_at=crate.get("updated_at"),
            version=crate.get("max_version"),
            repository=crate.get("repository"),
            license=crate.get("license"),
            homepage=crate.get("homepage"),
            keywords=crate.get("keywords", []),
            authors=crate.get("authors", [])
        )
    
    def crawl_all(self):
        next_page = None
        
        try:
            while self.total_collected < self.max_packages:
                response = self.fetch_page(next_page)
                crates_data = response.get("crates", [])
                
                if not crates_data:
                    self.logger.warning("No crates data in response")
                    break
                
                packages = [self.process_crate(crate) for crate in crates_data]
                self.save_package_batch(packages, "rust")
                
                meta = response.get("meta", {})
                next_page = meta.get("next_page")
                
                if not next_page:
                    break
                
                time.sleep(0.1)  # Be nice to the server
                
                if self.total_collected >= self.max_packages:
                    break
        
        except Exception as e:
            self.logger.error(f"Error during crawling Rust crates: {e}")
        
        self.logger.info(f"Rust crates crawling completed. Total collected: {self.total_collected}")
        return self.total_collected

class PythonPyPICrawler(BasePackageCrawler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://pypi.org/pypi"
        
    def fetch_package_info(self, package_name: str) -> Dict:
        url = f"{self.base_url}/{package_name}/json"
        return self.make_request(url)
    
    def fetch_top_packages(self) -> List[str]:
        # Get top packages from PyPI Stats JSON
        top_packages = []
        try:
            # Using PyPI Stats JSON that lists popular packages
            response = requests.get("https://hugovk.github.io/top-pypi-packages/top-pypi-packages-30-days.json")
            response.raise_for_status()
            data = response.json()
            for item in data.get("rows", []):
                if len(top_packages) >= self.max_packages:
                    break
                top_packages.append(item.get("project"))
            
            return top_packages
        except Exception as e:
            self.logger.error(f"Error fetching top Python packages: {e}")
            return []
    
    def process_package(self, package_data: Dict) -> PackageData:
        info = package_data.get("info", {})
        stats = package_data.get("urls", [])
        
        download_count = 0
        for url_data in stats:
            download_count += url_data.get("downloads", 0)
        
        # Try to extract repository from project_urls
        repository = None
        project_urls = info.get("project_urls") or {}
        for key, value in project_urls.items():
            if repository is None and any(kw in key.lower() for kw in ["source", "code", "github", "gitlab"]):
                repository = value
                break
        
        return PackageData(
            id=info.get("name", "").lower(),
            name=info.get("name", ""),
            language="python",
            description=info.get("summary"),
            downloads=download_count,
            stars=0,  # PyPI doesn't have star counts
            created_at=info.get("created") or None,
            updated_at=info.get("last_modified") or None,
            version=info.get("version"),
            repository=repository,
            license=info.get("license"),
            homepage=info.get("home_page") or info.get("project_url"),
            keywords=info.get("keywords", "").split() if info.get("keywords") else [],
            authors=[info.get("author")] if info.get("author") else []
        )
    
    def crawl_all(self):
        try:
            top_packages = self.fetch_top_packages()
            self.logger.info(f"Found {len(top_packages)} top Python packages")
            
            packages = []
            for package_name in top_packages:
                if self.total_collected >= self.max_packages:
                    break
                    
                package_data = self.fetch_package_info(package_name)
                if package_data:
                    packages.append(self.process_package(package_data))
                    
                    if len(packages) >= 100:  # Save in batches
                        self.save_package_batch(packages, "python")
                        packages = []
                        
                time.sleep(0.1)  # Be nice to the server
            
            # Save any remaining packages
            if packages:
                self.save_package_batch(packages, "python")
                
        except Exception as e:
            self.logger.error(f"Error during crawling Python packages: {e}")
        
        self.logger.info(f"Python packages crawling completed. Total collected: {self.total_collected}")
        return self.total_collected

class JavaScriptNPMCrawler(BasePackageCrawler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def fetch_popular_packages(self) -> List[str]:
        popular_packages = []
        seen_repos = set()  # Track unique repositories
        page = 1
        
        try:
            # Use GitHub API to get popular JavaScript repositories
            while len(popular_packages) < self.max_packages:
                github_search_url = "https://api.github.com/search/repositories"
                params = {
                    "q": "language:javascript stars:>100",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                    "page": page
                }
                
                # Add GitHub token for authentication
                token = next(self.token_iterator)
                headers = {"Accept": "application/vnd.github.v3+json"}
                if token:
                    headers["Authorization"] = f"token {token}"
                
                self.logger.info(f"Fetching page {page} of GitHub JavaScript repositories...")
                response = self.make_request(github_search_url, params=params, headers=headers)
                
                if not response or not isinstance(response, dict) or "items" not in response:
                    self.logger.error(f"Invalid response from GitHub API: {response}")
                    break
                
                items = response.get("items", [])
                if not items:  # No more results
                    self.logger.info("No more repositories found.")
                    break
                
                for item in items:
                    full_name = item.get("full_name")
                    if full_name:
                        repo_path = f"github.com/{full_name}"
                        if repo_path not in seen_repos:
                            seen_repos.add(repo_path)
                            popular_packages.append(repo_path)
                            stars = item.get("stargazers_count", 0)
                            self.logger.info(f"Found JavaScript package: {repo_path} (Stars: {stars})")
                            
                            if len(popular_packages) >= self.max_packages:
                                break
                
                # Check if we've reached the end of results
                total_count = response.get("total_count", 0)
                if page * 100 >= total_count:
                    self.logger.info(f"Reached end of results ({total_count} total repositories)")
                    break
                
                page += 1
                # Be nice to GitHub API rate limits
                time.sleep(1.5)
            
            self.logger.info(f"Found total of {len(popular_packages)} unique JavaScript packages")
            return popular_packages[:self.max_packages]
            
        except Exception as e:
            self.logger.error(f"Error fetching popular JavaScript packages: {e}")
            self.logger.error(traceback.format_exc())
            return []
    
    def fetch_package_details(self, package_path: str) -> Dict[str, Any]:
        package_data = {
            "path": package_path,
            "name": package_path.split("/")[-1],
            "description": None,
            "stars": 0,
            "repository": f"https://{package_path}",
            "version": "",
            "license": ""
        }
        
        # If the package is from GitHub, get repository information directly
        if package_path.startswith("github.com/"):
            try:
                # Extract repository path (owner/repo)
                repo_path = "/".join(package_path.split("/")[1:3])  # Take first two parts after github.com
                if repo_path:
                    github_api_url = f"https://api.github.com/repos/{repo_path}"
                    
                    # Add GitHub token for authentication
                    token = next(self.token_iterator)
                    headers = {"Accept": "application/vnd.github.v3+json"}
                    if token:
                        headers["Authorization"] = f"token {token}"
                    
                    self.logger.info(f"Fetching GitHub data from: {github_api_url}")
                    github_response = self.make_request(github_api_url, headers=headers)
                    
                    if isinstance(github_response, dict):
                        package_data["stars"] = github_response.get("stargazers_count", 0)
                        package_data["description"] = github_response.get("description")
                        package_data["repository"] = github_response.get("html_url", package_data["repository"])
                        package_data["license"] = github_response.get("license", {}).get("name")
                        package_data["created_at"] = github_response.get("created_at")
                        package_data["updated_at"] = github_response.get("updated_at")
                        package_data["homepage"] = github_response.get("homepage")
                        package_data["language"] = github_response.get("language")
                        
                        # Get topics (keywords)
                        topics_url = f"{github_api_url}/topics"
                        topics_response = self.make_request(topics_url, headers=headers)
                        if isinstance(topics_response, dict) and "names" in topics_response:
                            package_data["keywords"] = topics_response.get("names", [])
                            
                        # Get owner information
                        owner = github_response.get("owner", {})
                        if owner and "login" in owner:
                            package_data["authors"] = [owner.get("login")]
                            
                        # Try to fetch package.json for more info - quietly handle 404 errors
                        try:
                            contents_url = f"{github_api_url}/contents/package.json"
                            contents_headers = headers.copy()
                            contents_headers["Accept"] = "application/vnd.github.v3.raw"
                            
                            self.logger.debug(f"Checking for package.json at: {contents_url}")
                            contents_response = self.session.get(contents_url, headers=contents_headers, timeout=self.timeout)
                            
                            if contents_response.status_code == 200:
                                try:
                                    npm_data = json.loads(contents_response.text)
                                    
                                    # Extract version
                                    if "version" in npm_data:
                                        package_data["version"] = npm_data["version"]
                                    
                                    # Extract name if available
                                    if "name" in npm_data:
                                        package_data["name"] = npm_data["name"]
                                    
                                    # Extract additional keywords if available
                                    if "keywords" in npm_data and not package_data.get("keywords"):
                                        package_data["keywords"] = npm_data["keywords"]
                                    
                                    # Extract authors
                                    if "author" in npm_data:
                                        if isinstance(npm_data["author"], dict) and "name" in npm_data["author"]:
                                            package_data["authors"] = [npm_data["author"]["name"]]
                                        elif isinstance(npm_data["author"], str):
                                            package_data["authors"] = [npm_data["author"]]
                                except Exception as e:
                                    self.logger.debug(f"Error parsing package.json: {e}")
                        except requests.RequestException:
                            # Silently ignore request exceptions for package.json
                            pass
            except Exception as e:
                self.logger.error(f"Error fetching GitHub data: {e}")
        
        # Try to get npm registry data for more accurate download counts
        try:
            if package_data.get("name"):
                npm_name = package_data["name"]
                npm_url = f"https://registry.npmjs.org/{npm_name}"
                npm_response = self.make_request(npm_url)
                
                if isinstance(npm_response, dict):
                    # Get latest version
                    if "dist-tags" in npm_response and "latest" in npm_response["dist-tags"]:
                        package_data["version"] = npm_response["dist-tags"]["latest"]
                        
                    # Try to get download count from npm API
                    try:
                        download_url = f"https://api.npmjs.org/downloads/point/last-month/{npm_name}"
                        download_response = self.make_request(download_url)
                        if isinstance(download_response, dict) and "downloads" in download_response:
                            package_data["downloads"] = download_response["downloads"]
                    except:
                        pass  # Silently ignore errors in fetching download counts
        except:
            # Silently ignore errors in npm registry lookup
            pass
        
        return package_data
    
    def process_package(self, package_data: Dict) -> PackageData:
        return PackageData(
            id=package_data.get("path", ""),
            name=package_data.get("name", ""),
            language="javascript",
            description=package_data.get("description", ""),
            downloads=package_data.get("downloads", 0),
            stars=package_data.get("stars", 0),
            created_at=package_data.get("created_at"),
            updated_at=package_data.get("updated_at"),
            version=package_data.get("version", ""),
            repository=package_data.get("repository", ""),
            license=package_data.get("license", ""),
            homepage=package_data.get("homepage", ""),
            keywords=package_data.get("keywords", []),
            authors=package_data.get("authors", [])
        )
    
    def crawl_all(self):
        try:
            # Fetch list of popular packages
            popular_packages = self.fetch_popular_packages()
            self.logger.info(f"Found {len(popular_packages)} JavaScript packages")
            
            # Process packages in batches using parallel processing
            batch_size = 10
            num_workers = min(10, len(popular_packages))
            
            for i in range(0, len(popular_packages), batch_size):
                batch = popular_packages[i:i+batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(popular_packages) + batch_size - 1)//batch_size}")
                
                packages = []
                
                # Process packages in parallel
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {executor.submit(self.fetch_package_details, package_path): package_path for package_path in batch}
                    
                    for future in as_completed(futures):
                        package_path = futures[future]
                        try:
                            package_data = future.result()
                            packages.append(self.process_package(package_data))
                            self.logger.info(f"Processed {package_path}")
                        except Exception as e:
                            self.logger.error(f"Error processing {package_path}: {e}")
                
                # Save batch of packages
                if packages:
                    self.save_package_batch(packages, "javascript")
                
                # Sleep a bit between batches to avoid overwhelming APIs
                time.sleep(2)
                
                if self.total_collected >= self.max_packages:
                    break
                
        except Exception as e:
            self.logger.error(f"Error during crawling JavaScript packages: {e}")
            self.logger.error(traceback.format_exc())
        
        self.logger.info(f"JavaScript packages crawling completed. Total collected: {self.total_collected}")
        return self.total_collected

class GoPackageCrawler(BasePackageCrawler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = "https://pkg.go.dev/search"
        self.pkg_url = "https://pkg.go.dev"
    
    def fetch_popular_packages(self) -> List[str]:
        popular_packages = []
        seen_repos = set()  # Track unique repositories
        page = 1
        
        try:
            # Use GitHub API to get popular Go repositories
            while len(popular_packages) < self.max_packages:
                github_search_url = "https://api.github.com/search/repositories"
                params = {
                    "q": "language:go stars:>100",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                    "page": page
                }
                
                # Add GitHub token for authentication
                token = next(self.token_iterator)
                headers = {"Accept": "application/vnd.github.v3+json"}
                if token:
                    headers["Authorization"] = f"token {token}"
                
                self.logger.info(f"Fetching page {page} of GitHub Go repositories...")
                response = self.make_request(github_search_url, params=params, headers=headers)
                
                if not response or not isinstance(response, dict) or "items" not in response:
                    self.logger.error(f"Invalid response from GitHub API: {response}")
                    break
                
                items = response.get("items", [])
                if not items:  # No more results
                    self.logger.info("No more repositories found.")
                    break
                
                for item in items:
                    full_name = item.get("full_name")
                    if full_name:
                        repo_path = f"github.com/{full_name}"
                        if repo_path not in seen_repos:
                            seen_repos.add(repo_path)
                            popular_packages.append(repo_path)
                            stars = item.get("stargazers_count", 0)
                            self.logger.info(f"Found Go package: {repo_path} (Stars: {stars})")
                            
                            if len(popular_packages) >= self.max_packages:
                                break
                
                # Check if we've reached the end of results
                total_count = response.get("total_count", 0)
                if page * 100 >= total_count:
                    self.logger.info(f"Reached end of results ({total_count} total repositories)")
                    break
                
                page += 1
                # Be nice to GitHub API rate limits
                time.sleep(1.5)
            
            self.logger.info(f"Found total of {len(popular_packages)} unique Go packages")
            return popular_packages[:self.max_packages]
            
        except Exception as e:
            self.logger.error(f"Error fetching popular Go packages: {e}")
            self.logger.error(traceback.format_exc())
            return []
    
    def fetch_package_details(self, package_path: str) -> Dict[str, Any]:
        package_data = {
            "path": package_path,
            "name": package_path.split("/")[-1],
            "description": None,
            "stars": 0,
            "repository": f"https://{package_path}",
            "version": "",
            "license": ""
        }
        
        # If the package is from GitHub, get repository information directly
        if package_path.startswith("github.com/"):
            try:
                # Extract repository path (owner/repo)
                repo_path = "/".join(package_path.split("/")[1:3])  # Take first two parts after github.com
                if repo_path:
                    github_api_url = f"https://api.github.com/repos/{repo_path}"
                    
                    # Add GitHub token for authentication
                    token = next(self.token_iterator)
                    headers = {"Accept": "application/vnd.github.v3+json"}
                    if token:
                        headers["Authorization"] = f"token {token}"
                    
                    self.logger.info(f"Fetching GitHub data from: {github_api_url}")
                    github_response = self.make_request(github_api_url, headers=headers)
                    
                    if isinstance(github_response, dict):
                        package_data["stars"] = github_response.get("stargazers_count", 0)
                        package_data["description"] = github_response.get("description")
                        package_data["repository"] = github_response.get("html_url", package_data["repository"])
                        package_data["license"] = github_response.get("license", {}).get("name")
                        package_data["created_at"] = github_response.get("created_at")
                        package_data["updated_at"] = github_response.get("updated_at")
                        package_data["homepage"] = github_response.get("homepage")
                        package_data["language"] = github_response.get("language")
                        
                        # Get topics (keywords)
                        topics_url = f"{github_api_url}/topics"
                        topics_response = self.make_request(topics_url, headers=headers)
                        if isinstance(topics_response, dict) and "names" in topics_response:
                            package_data["keywords"] = topics_response.get("names", [])
                            
                        # Get owner information
                        owner = github_response.get("owner", {})
                        if owner and "login" in owner:
                            package_data["authors"] = [owner.get("login")]
            except Exception as e:
                self.logger.error(f"Error fetching GitHub data: {e}")
        
        # Try to fetch additional metadata from pkg.go.dev
        try:
            url = f"{self.pkg_url}/{package_path}"
            response = self.make_request(url)
            
            # If we got HTML content from pkg.go.dev, parse it for version info
            if "html_content" in response:
                html_content = response.get("html_content", "")
                soup = BeautifulSoup(html_content, "html.parser")
                
                # Extract version
                version_elem = soup.select_one(".go-Main-headerBreadcrumb span")
                if version_elem:
                    version_text = version_elem.get_text(strip=True)
                    if version_text.startswith("v"):
                        package_data["version"] = version_text
        except Exception as e:
            self.logger.error(f"Error fetching Go package details: {e}")
        
        return package_data
    
    def process_package(self, package_data: Dict) -> PackageData:
        return PackageData(
            id=package_data.get("path", ""),
            name=package_data.get("name", ""),
            language="go",
            description=package_data.get("description", ""),
            downloads=0,  # Not available
            stars=package_data.get("stars", 0),
            created_at=package_data.get("created_at"),
            updated_at=package_data.get("updated_at"),
            version=package_data.get("version", ""),
            repository=package_data.get("repository", ""),
            license=package_data.get("license", ""),
            homepage=package_data.get("homepage", ""),
            keywords=package_data.get("keywords", []),
            authors=package_data.get("authors", [])
        )
    
    def crawl_all(self):
        try:
            # Fetch list of popular packages
            popular_packages = self.fetch_popular_packages()
            self.logger.info(f"Found {len(popular_packages)} Go packages")
            
            # Process packages in batches using parallel processing
            batch_size = 10
            num_workers = min(10, len(popular_packages))
            
            for i in range(0, len(popular_packages), batch_size):
                batch = popular_packages[i:i+batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(popular_packages) + batch_size - 1)//batch_size}")
                
                packages = []
                
                # Process packages in parallel
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {executor.submit(self.fetch_package_details, package_path): package_path for package_path in batch}
                    
                    for future in as_completed(futures):
                        package_path = futures[future]
                        try:
                            package_data = future.result()
                            packages.append(self.process_package(package_data))
                            self.logger.info(f"Processed {package_path}")
                        except Exception as e:
                            self.logger.error(f"Error processing {package_path}: {e}")
                
                # Save batch of packages
                if packages:
                    self.save_package_batch(packages, "go")
                
                # Sleep a bit between batches to avoid overwhelming APIs
                time.sleep(2)
                
                if self.total_collected >= self.max_packages:
                    break
                
        except Exception as e:
            self.logger.error(f"Error during crawling Go packages: {e}")
            self.logger.error(traceback.format_exc())
        
        self.logger.info(f"Go packages crawling completed. Total collected: {self.total_collected}")
        return self.total_collected

class JavaMavenCrawler(BasePackageCrawler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Maven Repository URL
        self.base_url = "https://search.maven.org"
    
    def fetch_popular_packages(self) -> List[str]:
        popular_packages = []
        seen_repos = set()  # Track unique repositories
        page = 1
        
        try:
            # Use GitHub API to get popular Java repositories
            while len(popular_packages) < self.max_packages:
                github_search_url = "https://api.github.com/search/repositories"
                params = {
                    "q": "language:java stars:>100",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                    "page": page
                }
                
                # Add GitHub token for authentication
                token = next(self.token_iterator)
                headers = {"Accept": "application/vnd.github.v3+json"}
                if token:
                    headers["Authorization"] = f"token {token}"
                
                self.logger.info(f"Fetching page {page} of GitHub Java repositories...")
                response = self.make_request(github_search_url, params=params, headers=headers)
                
                if not response or not isinstance(response, dict) or "items" not in response:
                    self.logger.error(f"Invalid response from GitHub API: {response}")
                    break
                
                items = response.get("items", [])
                if not items:  # No more results
                    self.logger.info("No more repositories found.")
                    break
                
                for item in items:
                    full_name = item.get("full_name")
                    if full_name:
                        repo_path = f"github.com/{full_name}"
                        if repo_path not in seen_repos:
                            seen_repos.add(repo_path)
                            popular_packages.append(repo_path)
                            stars = item.get("stargazers_count", 0)
                            self.logger.info(f"Found Java package: {repo_path} (Stars: {stars})")
                            
                            if len(popular_packages) >= self.max_packages:
                                break
                
                # Check if we've reached the end of results
                total_count = response.get("total_count", 0)
                if page * 100 >= total_count:
                    self.logger.info(f"Reached end of results ({total_count} total repositories)")
                    break
                
                page += 1
                # Be nice to GitHub API rate limits
                time.sleep(1.5)
            
            self.logger.info(f"Found total of {len(popular_packages)} unique Java packages")
            return popular_packages[:self.max_packages]
            
        except Exception as e:
            self.logger.error(f"Error fetching popular Java packages: {e}")
            self.logger.error(traceback.format_exc())
            return []
    
    def fetch_package_details(self, package_path: str) -> Dict[str, Any]:
        package_data = {
            "path": package_path,
            "name": package_path.split("/")[-1],
            "description": None,
            "stars": 0,
            "repository": f"https://{package_path}",
            "version": "",
            "license": ""
        }
        
        # If the package is from GitHub, get repository information directly
        if package_path.startswith("github.com/"):
            try:
                # Extract repository path (owner/repo)
                repo_path = "/".join(package_path.split("/")[1:3])  # Take first two parts after github.com
                if repo_path:
                    github_api_url = f"https://api.github.com/repos/{repo_path}"
                    
                    # Add GitHub token for authentication
                    token = next(self.token_iterator)
                    headers = {"Accept": "application/vnd.github.v3+json"}
                    if token:
                        headers["Authorization"] = f"token {token}"
                    
                    self.logger.info(f"Fetching GitHub data from: {github_api_url}")
                    github_response = self.make_request(github_api_url, headers=headers)
                    
                    if isinstance(github_response, dict):
                        package_data["stars"] = github_response.get("stargazers_count", 0)
                        package_data["description"] = github_response.get("description")
                        package_data["repository"] = github_response.get("html_url", package_data["repository"])
                        package_data["license"] = github_response.get("license", {}).get("name")
                        package_data["created_at"] = github_response.get("created_at")
                        package_data["updated_at"] = github_response.get("updated_at")
                        package_data["homepage"] = github_response.get("homepage")
                        package_data["language"] = github_response.get("language")
                        
                        # Get topics (keywords)
                        topics_url = f"{github_api_url}/topics"
                        topics_response = self.make_request(topics_url, headers=headers)
                        if isinstance(topics_response, dict) and "names" in topics_response:
                            package_data["keywords"] = topics_response.get("names", [])
                            
                        # Get owner information
                        owner = github_response.get("owner", {})
                        if owner and "login" in owner:
                            package_data["authors"] = [owner.get("login")]
                            
                        # Try to fetch pom.xml for more info - quietly handle 404 errors
                        try:
                            # Check for pom.xml in root directory
                            contents_url = f"{github_api_url}/contents/pom.xml"
                            contents_headers = headers.copy()
                            contents_headers["Accept"] = "application/vnd.github.v3.raw"
                            
                            self.logger.debug(f"Checking for pom.xml at: {contents_url}")
                            contents_response = self.session.get(contents_url, headers=contents_headers, timeout=self.timeout)
                            
                            if contents_response.status_code == 200:
                                pom_content = contents_response.text
                                
                                # Extract version
                                version_match = re.search(r"<version>(.*?)</version>", pom_content)
                                if version_match:
                                    package_data["version"] = version_match.group(1)
                                
                                # Extract artifact ID if name is not already set
                                if package_data["name"] == repo_path.split("/")[-1]:
                                    artifact_match = re.search(r"<artifactId>(.*?)</artifactId>", pom_content)
                                    if artifact_match:
                                        package_data["name"] = artifact_match.group(1)
                                        
                                # Extract group ID
                                group_match = re.search(r"<groupId>(.*?)</groupId>", pom_content)
                                if group_match:
                                    group_id = group_match.group(1)
                                    # Add to keywords for better identification
                                    if "keywords" not in package_data:
                                        package_data["keywords"] = []
                                    package_data["keywords"].append(f"groupId:{group_id}")
                        except requests.RequestException:
                            # Silently ignore request exceptions for pom.xml
                            pass
            except Exception as e:
                self.logger.error(f"Error fetching GitHub data: {e}")
        
        # Try to fetch Maven metadata if we can guess the format
        try:
            if package_path.startswith("github.com/"):
                repo_parts = package_path.split("/")[1:3]
                if len(repo_parts) >= 2:
                    # Try common formats for Maven groupId/artifactId
                    possible_formats = [
                        # Format: com.github.{owner}.{repo}
                        f"com.github.{repo_parts[0]}.{repo_parts[1]}",
                        # Format: io.github.{owner}.{repo}
                        f"io.github.{repo_parts[0]}.{repo_parts[1]}",
                        # Format: {owner}.{repo}
                        f"{repo_parts[0]}.{repo_parts[1]}",
                        # Format: org.{owner}.{repo}
                        f"org.{repo_parts[0]}.{repo_parts[1]}"
                    ]
                    
                    for group_id in possible_formats:
                        try:
                            url = f"https://search.maven.org/solrsearch/select?q=g:%22{group_id}%22&rows=1&wt=json"
                            response = self.make_request(url)
                            
                            if isinstance(response, dict) and "response" in response:
                                docs = response.get("response", {}).get("docs", [])
                                if docs:
                                    doc = docs[0]
                                    if "a" in doc:  # artifactId
                                        package_data["name"] = doc["a"]
                                    if "latestVersion" in doc:
                                        package_data["version"] = doc["latestVersion"]
                                    break  # Found Maven data
                        except:
                            continue
        except Exception as e:
            self.logger.debug(f"Error fetching Maven data: {e}")
        
        return package_data
    
    def process_package(self, package_data: Dict) -> PackageData:
        return PackageData(
            id=package_data.get("path", ""),
            name=package_data.get("name", ""),
            language="java",
            description=package_data.get("description", ""),
            downloads=package_data.get("downloads", 0),
            stars=package_data.get("stars", 0),
            created_at=package_data.get("created_at"),
            updated_at=package_data.get("updated_at"),
            version=package_data.get("version", ""),
            repository=package_data.get("repository", ""),
            license=package_data.get("license", ""),
            homepage=package_data.get("homepage", ""),
            keywords=package_data.get("keywords", []),
            authors=package_data.get("authors", [])
        )
    
    def crawl_all(self):
        try:
            # Fetch list of popular packages
            popular_packages = self.fetch_popular_packages()
            self.logger.info(f"Found {len(popular_packages)} Java packages")
            
            # Process packages in batches using parallel processing
            batch_size = 10
            num_workers = min(10, len(popular_packages))
            
            for i in range(0, len(popular_packages), batch_size):
                batch = popular_packages[i:i+batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(popular_packages) + batch_size - 1)//batch_size}")
                
                packages = []
                
                # Process packages in parallel
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {executor.submit(self.fetch_package_details, package_path): package_path for package_path in batch}
                    
                    for future in as_completed(futures):
                        package_path = futures[future]
                        try:
                            package_data = future.result()
                            packages.append(self.process_package(package_data))
                            self.logger.info(f"Processed {package_path}")
                        except Exception as e:
                            self.logger.error(f"Error processing {package_path}: {e}")
                
                # Save batch of packages
                if packages:
                    self.save_package_batch(packages, "java")
                
                # Sleep a bit between batches to avoid overwhelming APIs
                time.sleep(2)
                
                if self.total_collected >= self.max_packages:
                    break
                
        except Exception as e:
            self.logger.error(f"Error during crawling Java packages: {e}")
            self.logger.error(traceback.format_exc())
        
        self.logger.info(f"Java packages crawling completed. Total collected: {self.total_collected}")
        return self.total_collected

class CPlusPlusConanCrawler(BasePackageCrawler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def fetch_popular_packages(self) -> List[str]:
        popular_packages = []
        seen_repos = set()  # Track unique repositories
        page = 1
        
        try:
            # Use GitHub API to get popular C++ repositories
            while len(popular_packages) < self.max_packages:
                github_search_url = "https://api.github.com/search/repositories"
                params = {
                    "q": "language:cpp stars:>100",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                    "page": page
                }
                
                # Add GitHub token for authentication
                token = next(self.token_iterator)
                headers = {"Accept": "application/vnd.github.v3+json"}
                if token:
                    headers["Authorization"] = f"token {token}"
                
                self.logger.info(f"Fetching page {page} of GitHub C++ repositories...")
                response = self.make_request(github_search_url, params=params, headers=headers)
                
                if not response or not isinstance(response, dict) or "items" not in response:
                    self.logger.error(f"Invalid response from GitHub API: {response}")
                    break
                
                items = response.get("items", [])
                if not items:  # No more results
                    self.logger.info("No more repositories found.")
                    break
                
                for item in items:
                    full_name = item.get("full_name")
                    if full_name:
                        repo_path = f"github.com/{full_name}"
                        if repo_path not in seen_repos:
                            seen_repos.add(repo_path)
                            popular_packages.append(repo_path)
                            stars = item.get("stargazers_count", 0)
                            self.logger.info(f"Found C++ package: {repo_path} (Stars: {stars})")
                            
                            if len(popular_packages) >= self.max_packages:
                                break
                
                # Check if we've reached the end of results
                total_count = response.get("total_count", 0)
                if page * 100 >= total_count:
                    self.logger.info(f"Reached end of results ({total_count} total repositories)")
                    break
                
                page += 1
                # Be nice to GitHub API rate limits
                time.sleep(1.5)
            
            self.logger.info(f"Found total of {len(popular_packages)} unique C++ packages")
            return popular_packages[:self.max_packages]
            
        except Exception as e:
            self.logger.error(f"Error fetching popular C++ packages: {e}")
            self.logger.error(traceback.format_exc())
            return []
    
    def fetch_package_details(self, package_path: str) -> Dict[str, Any]:
        package_data = {
            "path": package_path,
            "name": package_path.split("/")[-1],
            "description": None,
            "stars": 0,
            "repository": f"https://{package_path}",
            "version": "",
            "license": ""
        }
        
        # If the package is from GitHub, get repository information directly
        if package_path.startswith("github.com/"):
            try:
                # Extract repository path (owner/repo)
                repo_path = "/".join(package_path.split("/")[1:3])  # Take first two parts after github.com
                if repo_path:
                    github_api_url = f"https://api.github.com/repos/{repo_path}"
                    
                    # Add GitHub token for authentication
                    token = next(self.token_iterator)
                    headers = {"Accept": "application/vnd.github.v3+json"}
                    if token:
                        headers["Authorization"] = f"token {token}"
                    
                    self.logger.info(f"Fetching GitHub data from: {github_api_url}")
                    github_response = self.make_request(github_api_url, headers=headers)
                    
                    if isinstance(github_response, dict):
                        package_data["stars"] = github_response.get("stargazers_count", 0)
                        package_data["description"] = github_response.get("description")
                        package_data["repository"] = github_response.get("html_url", package_data["repository"])
                        package_data["license"] = github_response.get("license", {}).get("name")
                        package_data["created_at"] = github_response.get("created_at")
                        package_data["updated_at"] = github_response.get("updated_at")
                        package_data["homepage"] = github_response.get("homepage")
                        package_data["language"] = github_response.get("language")
                        
                        # Get topics (keywords)
                        topics_url = f"{github_api_url}/topics"
                        topics_response = self.make_request(topics_url, headers=headers)
                        if isinstance(topics_response, dict) and "names" in topics_response:
                            package_data["keywords"] = topics_response.get("names", [])
                            
                        # Get owner information
                        owner = github_response.get("owner", {})
                        if owner and "login" in owner:
                            package_data["authors"] = [owner.get("login")]
                            
                        # Try to fetch CMakeLists.txt for more info - quietly handle 404 errors
                        try:
                            # Check for CMakeLists.txt
                            cmake_url = f"{github_api_url}/contents/CMakeLists.txt"
                            cmake_headers = headers.copy()
                            cmake_headers["Accept"] = "application/vnd.github.v3.raw"
                            
                            self.logger.debug(f"Checking for CMakeLists.txt at: {cmake_url}")
                            cmake_response = self.session.get(cmake_url, headers=cmake_headers, timeout=self.timeout)
                            
                            if cmake_response.status_code == 200:
                                cmake_content = cmake_response.text
                                
                                # Extract version from CMakeLists.txt
                                version_match = re.search(r'set\s*\(\s*VERSION\s+([0-9]+\.[0-9]+\.[0-9]+)\s*\)', cmake_content, re.IGNORECASE)
                                if version_match:
                                    package_data["version"] = version_match.group(1)
                                else:
                                    # Try another common pattern
                                    version_match = re.search(r'project\s*\([^\)]*VERSION\s+([0-9]+\.[0-9]+\.[0-9]+)', cmake_content, re.IGNORECASE)
                                    if version_match:
                                        package_data["version"] = version_match.group(1)
                        except requests.RequestException:
                            # Silently ignore request exceptions for CMakeLists.txt
                            pass
            except Exception as e:
                self.logger.error(f"Error fetching GitHub data: {e}")
        
        return package_data
    
    def process_package(self, package_data: Dict) -> PackageData:
        return PackageData(
            id=package_data.get("path", ""),
            name=package_data.get("name", ""),
            language="c++",
            description=package_data.get("description", ""),
            downloads=0,  # Not typically available for C++ packages
            stars=package_data.get("stars", 0),
            created_at=package_data.get("created_at"),
            updated_at=package_data.get("updated_at"),
            version=package_data.get("version", ""),
            repository=package_data.get("repository", ""),
            license=package_data.get("license", ""),
            homepage=package_data.get("homepage", ""),
            keywords=package_data.get("keywords", []),
            authors=package_data.get("authors", [])
        )
    
    def crawl_all(self):
        try:
            # Fetch list of popular packages
            popular_packages = self.fetch_popular_packages()
            self.logger.info(f"Found {len(popular_packages)} C++ packages")
            
            # Process packages in batches using parallel processing
            batch_size = 10
            num_workers = min(10, len(popular_packages))
            
            for i in range(0, len(popular_packages), batch_size):
                batch = popular_packages[i:i+batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(popular_packages) + batch_size - 1)//batch_size}")
                
                packages = []
                
                # Process packages in parallel
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {executor.submit(self.fetch_package_details, package_path): package_path for package_path in batch}
                    
                    for future in as_completed(futures):
                        package_path = futures[future]
                        try:
                            package_data = future.result()
                            packages.append(self.process_package(package_data))
                            self.logger.info(f"Processed {package_path}")
                        except Exception as e:
                            self.logger.error(f"Error processing {package_path}: {e}")
                
                # Save batch of packages
                if packages:
                    self.save_package_batch(packages, "c++")
                
                # Sleep a bit between batches to avoid overwhelming APIs
                time.sleep(2)
                
                if self.total_collected >= self.max_packages:
                    break
                
        except Exception as e:
            self.logger.error(f"Error during crawling C++ packages: {e}")
            self.logger.error(traceback.format_exc())
        
        self.logger.info(f"C++ packages crawling completed. Total collected: {self.total_collected}")
        return self.total_collected

class PHPPackageCrawler(BasePackageCrawler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://packagist.org"
    
    def fetch_popular_packages(self) -> List[str]:
        popular_packages = []
        seen_repos = set()  # Track unique repositories
        page = 1
        
        try:
            # Use GitHub API to get popular PHP repositories
            while len(popular_packages) < self.max_packages:
                github_search_url = "https://api.github.com/search/repositories"
                params = {
                    "q": "language:php stars:>100",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 100,
                    "page": page
                }
                
                # Add GitHub token for authentication
                token = next(self.token_iterator)
                headers = {"Accept": "application/vnd.github.v3+json"}
                if token:
                    headers["Authorization"] = f"token {token}"
                
                self.logger.info(f"Fetching page {page} of GitHub PHP repositories...")
                response = self.make_request(github_search_url, params=params, headers=headers)
                
                if not response or not isinstance(response, dict) or "items" not in response:
                    self.logger.error(f"Invalid response from GitHub API: {response}")
                    break
                
                items = response.get("items", [])
                if not items:  # No more results
                    self.logger.info("No more repositories found.")
                    break
                
                for item in items:
                    full_name = item.get("full_name")
                    if full_name:
                        repo_path = f"github.com/{full_name}"
                        if repo_path not in seen_repos:
                            seen_repos.add(repo_path)
                            popular_packages.append(repo_path)
                            stars = item.get("stargazers_count", 0)
                            self.logger.info(f"Found PHP package: {repo_path} (Stars: {stars})")
                            
                            if len(popular_packages) >= self.max_packages:
                                break
                
                # Check if we've reached the end of results
                total_count = response.get("total_count", 0)
                if page * 100 >= total_count:
                    self.logger.info(f"Reached end of results ({total_count} total repositories)")
                    break
                
                page += 1
                # Be nice to GitHub API rate limits
                time.sleep(1.5)
            
            self.logger.info(f"Found total of {len(popular_packages)} unique PHP packages")
            return popular_packages[:self.max_packages]
            
        except Exception as e:
            self.logger.error(f"Error fetching popular PHP packages: {e}")
            self.logger.error(traceback.format_exc())
            return []
    
    def fetch_package_details(self, package_path: str) -> Dict[str, Any]:
        package_data = {
            "path": package_path,
            "name": package_path.split("/")[-1],
            "description": None,
            "stars": 0,
            "repository": f"https://{package_path}",
            "version": "",
            "license": ""
        }
        
        # If the package is from GitHub, get repository information directly
        if package_path.startswith("github.com/"):
            try:
                # Extract repository path (owner/repo)
                repo_path = "/".join(package_path.split("/")[1:3])  # Take first two parts after github.com
                if repo_path:
                    github_api_url = f"https://api.github.com/repos/{repo_path}"
                    
                    # Add GitHub token for authentication
                    token = next(self.token_iterator)
                    headers = {"Accept": "application/vnd.github.v3+json"}
                    if token:
                        headers["Authorization"] = f"token {token}"
                    
                    self.logger.info(f"Fetching GitHub data from: {github_api_url}")
                    github_response = self.make_request(github_api_url, headers=headers)
                    
                    if isinstance(github_response, dict):
                        package_data["stars"] = github_response.get("stargazers_count", 0)
                        package_data["description"] = github_response.get("description")
                        package_data["repository"] = github_response.get("html_url", package_data["repository"])
                        package_data["license"] = github_response.get("license", {}).get("name")
                        package_data["created_at"] = github_response.get("created_at")
                        package_data["updated_at"] = github_response.get("updated_at")
                        package_data["homepage"] = github_response.get("homepage")
                        package_data["language"] = github_response.get("language")
                        
                        # Get topics (keywords)
                        topics_url = f"{github_api_url}/topics"
                        topics_response = self.make_request(topics_url, headers=headers)
                        if isinstance(topics_response, dict) and "names" in topics_response:
                            package_data["keywords"] = topics_response.get("names", [])
                            
                        # Get owner information
                        owner = github_response.get("owner", {})
                        if owner and "login" in owner:
                            package_data["authors"] = [owner.get("login")]
                            
                        # Try to fetch composer.json for more info - quietly handle 404 errors
                        try:
                            contents_url = f"{github_api_url}/contents/composer.json"
                            contents_headers = headers.copy()
                            contents_headers["Accept"] = "application/vnd.github.v3.raw"
                            
                            self.logger.debug(f"Checking for composer.json at: {contents_url}")
                            contents_response = self.session.get(contents_url, headers=contents_headers, timeout=self.timeout)
                            
                            if contents_response.status_code == 200:
                                try:
                                    composer_data = json.loads(contents_response.text)
                                    
                                    # Extract version
                                    if "version" in composer_data:
                                        package_data["version"] = composer_data["version"]
                                    
                                    # Extract keywords if not already present
                                    if "keywords" in composer_data and not package_data.get("keywords"):
                                        package_data["keywords"] = composer_data["keywords"]
                                    
                                    # Extract authors
                                    if "authors" in composer_data:
                                        authors = []
                                        for author in composer_data["authors"]:
                                            if "name" in author:
                                                authors.append(author["name"])
                                        if authors:
                                            package_data["authors"] = authors
                                except Exception as e:
                                    self.logger.debug(f"Error parsing composer.json: {e}")
                        except requests.RequestException:
                            # Silently ignore request exceptions for composer.json
                            pass
            except Exception as e:
                self.logger.error(f"Error fetching GitHub data: {e}")
        
        # Try to fetch additional metadata from Packagist - quietly handle 404 errors
        try:
            # Extract vendor/package format
            if package_path.startswith("github.com/"):
                repo_parts = package_path.split("/")[1:3]
                if len(repo_parts) >= 2:
                    packagist_name = f"{repo_parts[0]}/{repo_parts[1]}"
                    url = f"https://packagist.org/packages/{packagist_name}.json"
                    
                    self.logger.debug(f"Checking Packagist data at: {url}")
                    packagist_response = self.session.get(url, timeout=self.timeout)
                    
                    if packagist_response.status_code == 200:
                        try:
                            response_data = packagist_response.json()
                            if "package" in response_data:
                                package_info = response_data.get("package", {})
                                
                                # Update package data with Packagist info
                                if "description" in package_info and not package_data.get("description"):
                                    package_data["description"] = package_info["description"]
                                
                                if "downloads" in package_info:
                                    package_data["downloads"] = package_info["downloads"].get("total", 0)
                                
                                if "favers" in package_info:
                                    package_data["stars"] = package_info["favers"]
                                
                                if "versions" in package_info:
                                    versions = package_info["versions"]
                                    if versions:
                                        latest_version = next(iter(versions))
                                        if "version" in versions[latest_version]:
                                            package_data["version"] = versions[latest_version]["version"]
                        except ValueError:
                            # Silently ignore JSON parsing errors
                            pass
        except requests.RequestException:
            # Silently ignore request exceptions for Packagist
            pass
        
        return package_data
    
    def process_package(self, package_data: Dict) -> PackageData:
        return PackageData(
            id=package_data.get("path", ""),
            name=package_data.get("name", ""),
            language="php",
            description=package_data.get("description", ""),
            downloads=package_data.get("downloads", 0),
            stars=package_data.get("stars", 0),
            created_at=package_data.get("created_at"),
            updated_at=package_data.get("updated_at"),
            version=package_data.get("version", ""),
            repository=package_data.get("repository", ""),
            license=package_data.get("license", ""),
            homepage=package_data.get("homepage", ""),
            keywords=package_data.get("keywords", []),
            authors=package_data.get("authors", [])
        )
    
    def crawl_all(self):
        try:
            # Fetch list of popular packages
            popular_packages = self.fetch_popular_packages()
            self.logger.info(f"Found {len(popular_packages)} PHP packages")
            
            # Process packages in batches using parallel processing
            batch_size = 10
            num_workers = min(10, len(popular_packages))
            
            for i in range(0, len(popular_packages), batch_size):
                batch = popular_packages[i:i+batch_size]
                self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(popular_packages) + batch_size - 1)//batch_size}")
                
                packages = []
                
                # Process packages in parallel
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {executor.submit(self.fetch_package_details, package_path): package_path for package_path in batch}
                    
                    for future in as_completed(futures):
                        package_path = futures[future]
                        try:
                            package_data = future.result()
                            packages.append(self.process_package(package_data))
                            self.logger.info(f"Processed {package_path}")
                        except Exception as e:
                            self.logger.error(f"Error processing {package_path}: {e}")
                
                # Save batch of packages
                if packages:
                    self.save_package_batch(packages, "php")
                
                # Sleep a bit between batches to avoid overwhelming APIs
                time.sleep(2)
                
                if self.total_collected >= self.max_packages:
                    break
                
        except Exception as e:
            self.logger.error(f"Error during crawling PHP packages: {e}")
            self.logger.error(traceback.format_exc())
        
        self.logger.info(f"PHP packages crawling completed. Total collected: {self.total_collected}")
        return self.total_collected

class MetaPackageCrawler:
    def __init__(
        self,
        output_dir: str = "package_data",
        languages: List[str] = None,
        max_packages_per_lang: int = 1000,
        max_workers: int = 3
    ):
        self.output_dir = output_dir
        self.languages = languages or ["python", "rust", "javascript", "go", "java", "c++", "php"]
        self.max_packages_per_lang = max_packages_per_lang
        self.max_workers = max_workers
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
    
    def get_crawler_for_language(self, language: str) -> BasePackageCrawler:
        if language == "rust":
            return RustCratesCrawler(output_dir=self.output_dir, max_packages=self.max_packages_per_lang)
        elif language == "python":
            return PythonPyPICrawler(output_dir=self.output_dir, max_packages=self.max_packages_per_lang)
        elif language == "javascript":
            return JavaScriptNPMCrawler(output_dir=self.output_dir, max_packages=self.max_packages_per_lang)
        elif language == "go":
            return GoPackageCrawler(output_dir=self.output_dir, max_packages=self.max_packages_per_lang)
        elif language == "java":
            return JavaMavenCrawler(output_dir=self.output_dir, max_packages=self.max_packages_per_lang)
        elif language == "c++":
            return CPlusPlusConanCrawler(output_dir=self.output_dir, max_packages=self.max_packages_per_lang)
        elif language == "php":
            return PHPPackageCrawler(output_dir=self.output_dir, max_packages=self.max_packages_per_lang)
        else:
            raise ValueError(f"Unsupported language: {language}")
    
    def crawl_all_languages(self):
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_lang = {
                executor.submit(self.crawl_language, lang): lang 
                for lang in self.languages
            }
            
            for future in as_completed(future_to_lang):
                language = future_to_lang[future]
                try:
                    count = future.result()
                    results[language] = count
                except Exception as e:
                    self.logger.error(f"Error crawling {language}: {e}")
                    results[language] = 0
        
        self.logger.info("All crawling completed")
        return results
    
    def crawl_language(self, language: str) -> int:
        try:
            self.logger.info(f"Starting crawler for {language}")
            crawler = self.get_crawler_for_language(language)
            count = crawler.crawl_all()
            self.logger.info(f"Completed crawler for {language}. Collected {count} packages")
            return count
        except Exception as e:
            self.logger.error(f"Error in {language} crawler: {e}")
            return 0

def main():
    crawler = MetaPackageCrawler(
        output_dir="package_data",
        max_packages_per_lang=10,
        max_workers=3
    )
    
    try:
        results = crawler.crawl_all_languages()
        print("Crawling completed with the following results:")
        for language, count in results.items():
            print(f"{language}: {count} packages")
    except KeyboardInterrupt:
        print("Crawling interrupted by user")
    except Exception as e:
        print(f"Error during crawling: {e}")

if __name__ == "__main__":
    main()