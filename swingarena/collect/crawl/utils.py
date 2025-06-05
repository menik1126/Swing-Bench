import requests
from collections import Counter

def query_rate_limit(token):
    url = "https://api.github.com/rate_limit"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to query rate limit. Status code: {response.status_code}"}

def count_distribution(ds, key):
    """
    Count the distribution of a key in the dataset.
    Args:
        ds: list of dicts
        key: str, the key to count the distribution of
    Returns:
        dict, the distribution of the key
    """
    repo_count = Counter(repo)
    count_distribution = Counter(repo_count.values())
    count_distribution = dict(sorted(count_distribution.items()))
    return count_distribution