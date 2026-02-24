import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swingarena.crawl.metainfo import PHPPackageCrawler

def test_php_crawler():
    print("Starting PHP crawler test...")
    
    # Get GitHub tokens from environment
    github_tokens = os.getenv("GITHUB_TOKENS", "").split(",")
    if not github_tokens or not any(github_tokens):
        print("Warning: No GitHub tokens found. Set GITHUB_TOKENS environment variable for better rate limits.")
    
    # Initialize the crawler with a small number of packages for testing
    crawler = PHPPackageCrawler(
        output_dir="test_package_data",
        max_packages=50,  # Only crawl 50 packages for testing
        github_tokens=github_tokens
    )
    
    try:
        print("Crawler initialized, starting crawl...")
        # Run the crawler
        count = crawler.crawl_all()
        print(f"Successfully crawled {count} PHP packages")
        return True
    except Exception as e:
        print(f"Error during crawling: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_php_crawler() 