import requests
import time
import json
from typing import Optional
import logging
from dataclasses import dataclass
from urllib.parse import urljoin
from datetime import datetime

@dataclass
class CrateData:
    id: str
    name: str
    description: Optional[str]
    downloads: int
    created_at: str
    updated_at: str
    repository: Optional[str]

class CratesCrawler:
    def __init__(
        self,
        base_url: str = "https://crates.io/api/v1/crates",
        output_file: str = f"crates_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl",
        per_page: int = 90,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 30
    ):
        self.base_url = base_url
        self.output_file = output_file
        self.per_page = per_page
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.session = requests.Session()
        self.total_collected = 0
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def fetch_page(self, page_param: Optional[str] = None) -> dict:
        url = self.base_url
        if page_param:
            url = urljoin(url, f"?{page_param}")
        else:
            url = f"{url}?per_page={self.per_page}"

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                
                if response.status_code == 200:
                    return response.json()
                
                if response.status_code == 429:
                    wait_time = (attempt + 1) * 5
                    self.logger.warning(f"Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                
            except requests.RequestException as e:
                self.logger.error(f"Request failed: {e}. Attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                raise

        raise Exception("Failed to fetch page after all retry attempts")

    def save_crates_batch(self, crates_data: list):
        with open(self.output_file, 'a', encoding='utf-8') as f:
            for crate in crates_data:
                crate_obj = CrateData(
                    id=crate["id"],
                    name=crate["name"],
                    description=crate.get("description"),
                    downloads=crate.get("downloads", 0),
                    created_at=crate.get("created_at"),
                    updated_at=crate.get("updated_at"),
                    repository=crate.get("repository")
                )
                f.write(json.dumps(vars(crate_obj), ensure_ascii=False) + '\n')
                
        self.total_collected += len(crates_data)
        self.logger.info(f"Saved batch of {len(crates_data)} crates. Total collected: {self.total_collected}")

    def crawl_all(self):
        next_page = None

        try:
            while True:
                response = self.fetch_page(next_page)
                crates_data = response.get("crates", [])
                
                if not crates_data:
                    self.logger.warning("No crates data in response")
                    break

                self.save_crates_batch(crates_data)

                meta = response.get("meta", {})
                next_page = meta.get("next_page")
                
                if not next_page:
                    break
                
                time.sleep(0.1)  # Be nice to the server

        except KeyboardInterrupt:
            self.logger.info("Crawling interrupted by user. Progress saved.")
        except Exception as e:
            self.logger.error(f"Error during crawling: {e}")
            raise

        self.logger.info(f"Crawling completed. Total crates collected: {self.total_collected}")
        return self.total_collected

def main():
    crawler = CratesCrawler()
    try:
        total_crates = crawler.crawl_all()
        print(f"Successfully collected {total_crates} crates")
        print(f"Data saved to {crawler.output_file}")
        
    except Exception as e:
        print(f"Crawling failed: {e}")

if __name__ == "__main__":
    main()