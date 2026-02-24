import os
import json
import time
import random
import logging
import argparse
import asyncio
import aiohttp
import aiofiles
import subprocess
from tqdm import tqdm
from typing import List, Dict, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("github_crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com"
LANGUAGES = [
    "JavaScript", "Python", "Java", 
    "Go", "C++", "Rust", "PHP", "TypeScript",
    "C#", "Ruby", "Swift", "Kotlin",
    "Scala", "Haskell", "Erlang", "Elixir",
    "Lua", "Groovy", "VimL", "OCaml", "R", "Perl"
]

class GitHubCrawler:
    def __init__(
        self, 
        output_dir: str = "github_repos", 
        max_repos_per_lang: int = 100,
        concurrency: int = 10,
        retry_limit: int = 3,
        timeout: int = 30
    ):
        self.tokens = os.environ.get("GITHUB_TOKENS", "").split(",")
        if not self.tokens or not self.tokens[0]:
            raise ValueError("GITHUB_TOKENS environment variable is required")
            
        self.output_dir = output_dir
        self.max_repos_per_lang = max_repos_per_lang
        self.concurrency = concurrency
        self.retry_limit = retry_limit
        self.timeout = timeout
        self.progress_file = os.path.join(output_dir, "progress.json")
        self.semaphore = asyncio.Semaphore(concurrency)
        
        os.makedirs(output_dir, exist_ok=True)
        
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict[str, Any]:
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load progress file: {e}")
        
        return {
            "completed_languages": [],
            "current_language": None,
            "current_page": 1,
            "repos_collected": 0,
            "repos_cloned": [],
            "last_updated": time.time()
        }
    
    async def _save_progress(self) -> None:
        """Save progress file, with error handling"""
        try:
            self.progress["last_updated"] = time.time()
            async with aiofiles.open(self.progress_file, 'w') as f:
                await f.write(json.dumps(self.progress, indent=2))
        except Exception as e:
            logger.error(f"Failed to save progress file: {e}")
    
    async def _get_random_token(self) -> str:
        if not self.tokens:
            raise ValueError("No GitHub tokens available")
        return random.choice(self.tokens)
    
    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        async with self.semaphore:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {await self._get_random_token()}"
            }
            
            for attempt in range(self.retry_limit):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url, 
                            headers=headers, 
                            params=params,
                            timeout=self.timeout
                        ) as response:
                            if response.status == 200:
                                return await response.json()
                            elif response.status == 403:
                                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                                wait_time = max(1, reset_time - time.time())
                                logger.warning(f"API rate limit reached, waiting {wait_time:.2f} seconds before retrying")
                                await asyncio.sleep(wait_time + random.uniform(0.1, 2.0))
                            elif response.status == 404:
                                logger.error(f"Resource not found: {url}")
                                return {}
                            else:
                                logger.error(f"Request failed: {response.status}, {await response.text()}")
                                await asyncio.sleep(1 * (attempt + 1))
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.error(f"Request exception: {e}, attempt: {attempt+1}/{self.retry_limit}")
                    await asyncio.sleep(1 * (attempt + 1))
            
            logger.error(f"Request failed, max retries reached: {url}")
            return {}
    
    async def _fetch_repositories(self, language: str, page: int = 1) -> List[Dict]:
        url = f"{GITHUB_API_URL}/search/repositories"
        params = {
            "q": f"language:{language}",
            "sort": "stars",
            "order": "desc",
            "per_page": 100,
            "page": page
        }
        
        data = await self._make_request(url, params)
        return data.get("items", [])
    
    async def _fetch_repository_details(self, repo_url: str) -> Dict:
        """Get detailed repository information as metadata, with enhanced error handling"""
        try:
            parts = repo_url.rstrip('/').split('/')
            if len(parts) < 5:
                logger.error(f"Invalid repository URL: {repo_url}")
                return {}
                
            owner, repo_name = parts[-2], parts[-1]
            url = f"{GITHUB_API_URL}/repos/{owner}/{repo_name}"
            
            return await self._make_request(url)
        except Exception as e:
            logger.error(f"Failed to fetch repository details for {repo_url}: {e}")
            return {}
    
    async def _save_repository_to_index(self, language_dir: str, repo_data: Dict) -> None:
        index_file_path = os.path.join(language_dir, "repositories.jsonl")
        try:
            async with aiofiles.open(index_file_path, 'a') as jsonl_file:
                await jsonl_file.write(json.dumps(repo_data) + "\n")
        except Exception as e:
            logger.error(f"Failed to update repository index for {repo_data.get('name')}: {e}")
    
    async def _save_repository_data(self, language: str, repos: List[Dict]) -> None:
        """Process each repository separately, ensuring one error does not affect others"""
        # Ensure language directory exists
        language_dir = os.path.join(self.output_dir, language)
        os.makedirs(language_dir, exist_ok=True)
        
        for repo in repos:
            try:
                repo_data = {
                    "name": repo.get("name", ""),
                    "full_name": repo.get("full_name", ""),
                    "url": repo.get("html_url", ""),
                    "language": language,
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "description": repo.get("description", ""),
                    "created_at": repo.get("created_at", ""),
                    "updated_at": repo.get("updated_at", "")
                }
                
                repo_id = f"{language}/{repo_data['name']}"
                if repo_id in self.progress.get("repos_cloned", []):
                    logger.info(f"Repository {repo_id} already processed, skipping")
                    continue
                
                success = await self._clone_repository_with_metadata(repo_data, language_dir)
                
                if success:
                    await self._save_repository_to_index(language_dir, repo_data)                    
                    if "repos_cloned" not in self.progress:
                        self.progress["repos_cloned"] = []
                    self.progress["repos_cloned"].append(repo_id)
                    await self._save_progress()
            except Exception as e:
                logger.error(f"Failed to process repository {repo.get('name', 'unknown')}: {e}")
                continue

    async def _clone_repository_with_metadata(self, repo_data: Dict, language_dir: str) -> bool:
        """Clone repository and create metadata file, return success status"""
        if not repo_data.get("name") or not repo_data.get("url"):
            logger.error(f"Invalid repository data: {repo_data}")
            return False
            
        repo_name = repo_data["name"]
        repo_url = repo_data["url"]
        repo_dir = os.path.join(language_dir, repo_name)
        
        
        if os.path.exists(repo_dir):
            logger.info(f"Repository {repo_name} already exists, skipping clone")
        else:
            logger.info(f"Cloning {repo_url} to {repo_dir}")
            try:
                process = await asyncio.create_subprocess_exec(
                    "git", "clone", repo_url, repo_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.error(f"Failed to clone {repo_url}: {stderr.decode()}")
                    return False
            except Exception as e:
                logger.error(f"Exception during cloning {repo_url}: {e}")
                return False
        
        try:
            details = await self._fetch_repository_details(repo_url)
            metadata = {
                **repo_data,
                "license": None,
                "topics": [],
                "open_issues_count": 0,
                "default_branch": "main",
                "archived": False,
                "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if details:
                if "license" in details and details["license"]:
                    metadata["license"] = details["license"].get("name")
                
                metadata["topics"] = details.get("topics", [])
                metadata["open_issues_count"] = details.get("open_issues_count", 0)
                metadata["default_branch"] = details.get("default_branch", "main")
                metadata["archived"] = details.get("archived", False)
            
            metadata_path = os.path.join(repo_dir, "metadata.json")
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(metadata, indent=2))
                
            return True
        except Exception as e:
            logger.error(f"Failed to create metadata for {repo_name}: {e}")
            return False
    
    async def crawl_language(self, language: str) -> None:
        if language in self.progress["completed_languages"]:
            logger.info(f"Language {language} already crawled, skipping")
            return

        language_dir = os.path.join(self.output_dir, language)
        os.makedirs(language_dir, exist_ok=True)
        
        start_page = 1
        repos_collected = 0

        if language == self.progress["current_language"]:
            start_page = self.progress["current_page"]
            repos_collected = self.progress["repos_collected"]
            logger.info(f"Resuming crawl for {language}, page: {start_page}, already collected: {repos_collected}")
        else:
            self.progress["current_language"] = language
            self.progress["current_page"] = start_page
            self.progress["repos_collected"] = repos_collected
            await self._save_progress()
        
        page = start_page
        pbar = tqdm(total=self.max_repos_per_lang, initial=repos_collected, desc=f"Crawling {language}")
        
        try:
            while repos_collected < self.max_repos_per_lang:
                repos = await self._fetch_repositories(language, page)
                
                if not repos:
                    logger.info(f"No more repositories for language {language}")
                    break
                
                remaining = self.max_repos_per_lang - repos_collected
                repos_to_save = repos[:remaining]
                
                for repo in repos_to_save:
                    await self._save_repository_data(language, [repo])
                    repos_collected += 1
                    pbar.update(1)
                    
                    self.progress["repos_collected"] = repos_collected
                    await self._save_progress()
                    
                    if repos_collected >= self.max_repos_per_lang:
                        break
                
                page += 1
                self.progress["current_page"] = page
                await self._save_progress()
                
                if repos_collected >= self.max_repos_per_lang or len(repos) < 100:
                    break
                
                await asyncio.sleep(random.uniform(0.5, 2.0))
        except Exception as e:
            logger.error(f"Error crawling {language}: {e}")
        finally:
            pbar.close()
            
            if repos_collected >= self.max_repos_per_lang or not repos:
                self.progress["completed_languages"].append(language)
                
            self.progress["current_language"] = None
            self.progress["current_page"] = 1
            self.progress["repos_collected"] = 0
            await self._save_progress()
            
            logger.info(f"Finished crawling {language}, collected {repos_collected} repositories")
    
    async def crawl_all_languages(self) -> None:
        for language in LANGUAGES:
            try:
                await self.crawl_language(language)
                await asyncio.sleep(random.uniform(1.0, 3.0))
            except Exception as e:
                logger.error(f"Failed to crawl language {language}: {e}")
    
    async def crawl_parallel(self, languages: List[str] = None) -> None:
        if not languages:
            languages = [lang for lang in LANGUAGES if lang not in self.progress["completed_languages"]]
        
        logger.info(f"Preparing to crawl {len(languages)} languages in parallel")
        
        tasks = [self.crawl_language(language) for language in languages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for language, result in zip(languages, results):
            if isinstance(result, Exception):
                logger.error(f"Language {language} crawl failed with exception: {result}")
        
        logger.info("All language crawling tasks completed")

async def main():
    parser = argparse.ArgumentParser(description="GitHub Repository Crawler")
    parser.add_argument("--output", type=str, default="github_repos", help="Output directory")
    parser.add_argument("--max-repos", type=int, default=100, help="Maximum number of repositories to crawl per language")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent requests")
    parser.add_argument("--languages", type=str, help="Languages to crawl (comma-separated), all supported languages if not specified")
    parser.add_argument("--parallel", action="store_true", help="Whether to crawl multiple languages in parallel")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout for HTTP requests in seconds")
    parser.add_argument("--retry", type=int, default=3, help="Number of retry attempts for failed requests")
    
    args = parser.parse_args()
    
    languages_to_crawl = None
    if args.languages:
        languages_to_crawl = [lang.strip() for lang in args.languages.split(",")]
    
    try:
        crawler = GitHubCrawler(
            output_dir=args.output,
            max_repos_per_lang=args.max_repos,
            concurrency=args.concurrency,
            retry_limit=args.retry,
            timeout=args.timeout
        )
        
        if args.parallel:
            await crawler.crawl_parallel(languages_to_crawl)
        else:
            if languages_to_crawl:
                for language in languages_to_crawl:
                    await crawler.crawl_language(language)
            else:
                await crawler.crawl_all_languages()
                
    except KeyboardInterrupt:
        logger.info("Crawler stopped by user")
    except Exception as e:
        logger.critical(f"Critical error in crawler: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())