#!/usr/bin/env python3

import os
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from swingarena.collect.crawl.metainfo import (
    GoPackageCrawler,
    PHPPackageCrawler,
    JavaMavenCrawler,
    CPlusPlusConanCrawler,
    JavaScriptNPMCrawler
)

# Configuration
OUTPUT_DIR = "repository_data_0430"
MAX_REPOSITORIES = 5000  # Target number of repositories per language
WORKER_THREADS = 25      # Number of parallel workers per language
BATCH_SIZE = 30          # Process repositories in batches of this size
LANGUAGES = ["go", "php", "java", "cpp", "javascript"]  # Languages to crawl in sequence

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("crawler.log")
    ]
)
logger = logging.getLogger("repo_crawler")

def process_language(language, github_tokens):
    start_time = time.time()
    logger.info(f"Starting crawler for {language} language")
    
    crawler_map = {
        'go': GoPackageCrawler,
        'php': PHPPackageCrawler,
        'java': JavaMavenCrawler,
        'cpp': CPlusPlusConanCrawler,
        'javascript': JavaScriptNPMCrawler
    }
    
    # Initialize crawler
    crawler = crawler_map[language](
        output_dir=f"{OUTPUT_DIR}/{language}",
        max_packages=MAX_REPOSITORIES,
        github_tokens=github_tokens
    )
    
    # Get repositories list
    repos = crawler.fetch_popular_packages()
    logger.info(f"Found {len(repos)} {language} repositories to process")
    
    # Process repositories in parallel batches
    total_processed = 0
    
    for i in range(0, len(repos), BATCH_SIZE):
        batch = repos[i:i+BATCH_SIZE]
        logger.info(f"[{language}] Processing batch {i//BATCH_SIZE + 1}/{(len(repos) + BATCH_SIZE - 1)//BATCH_SIZE}")
        
        packages = []
        with ThreadPoolExecutor(max_workers=WORKER_THREADS) as executor:
            futures = {executor.submit(crawler.fetch_package_details, repo): repo for repo in batch}
            
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    package_data = future.result()
                    packages.append(crawler.process_package(package_data))
                    logger.info(f"[{language}] Processed: {repo}")
                except Exception as e:
                    logger.error(f"[{language}] Error processing {repo}: {e}")
        
        # Save batch
        if packages:
            crawler.save_package_batch(packages, language)
            total_processed += len(packages)
            
        # Prevent overwhelming the API
        time.sleep(0.5)
        
        if total_processed >= MAX_REPOSITORIES:
            logger.info(f"[{language}] Reached target of {MAX_REPOSITORIES} repositories")
            break
    
    elapsed = time.time() - start_time
    logger.info(f"Completed {language} crawl: {total_processed} repositories in {elapsed:.2f} seconds")
    return total_processed

def main():
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get GitHub tokens from environment
    github_tokens = os.getenv("GITHUB_TOKENS", "").split(",")
    if not github_tokens or not github_tokens[0]:
        logger.error("No GITHUB_TOKENS found in environment variables. Aborting.")
        logger.error("Set with: export GITHUB_TOKENS=token1,token2,token3")
        return
    
    logger.info(f"Found {len(github_tokens)} GitHub tokens")
    
    # Process each language in sequence
    results = {}
    total_start = time.time()
    
    for lang in LANGUAGES:
        try:
            results[lang] = process_language(lang, github_tokens)
            logger.info(f"Completed {lang}: {results[lang]} repositories")
        except Exception as e:
            logger.error(f"Error processing language {lang}: {e}")
            results[lang] = 0
    
    # Print summary
    total_time = time.time() - total_start
    total_repos = sum(results.values())
    
    logger.info("=" * 60)
    logger.info("CRAWLER SUMMARY")
    logger.info("=" * 60)
    for lang, count in results.items():
        logger.info(f"{lang.upper()}: {count} repositories")
    logger.info("=" * 60)
    logger.info(f"Total repositories: {total_repos}")
    logger.info(f"Total time: {total_time:.2f} seconds")
    logger.info(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main() 