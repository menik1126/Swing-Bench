"""
Finds new repo(s) of the specified language and checks if the repo(s) meet requirements

References

Search query string:
https://docs.github.com/en/search-github/github-code-search/understanding-github-code-search-syntax

For path querying specifically:
https://docs.github.com/en/search-github/github-code-search/understanding-github-code-search-syntax#path-qualifier
"""
from collections import OrderedDict
import datetime
import fire
import os
import sys
from typing import Callable, Optional

from scripts.check_repo_stats import check_requirements, check_map
from scripts.common import get_graphql_data


def search_by_stars(
    language: str, stars_query: str, cursor: str, gql_format: str, bulk_size: int = 100
) -> dict:
    """Returns result from searching by stars"""
    # Use this function for the first 1000 repos
    search_query: str = (
        f"language:{language} stars:{stars_query} archived:false sort:stars"
    )
    return get_graphql_data(gql_format % (search_query, bulk_size, cursor))


def search_by_last_push(
    language: str,
    stars_query: str,
    cursor: str,
    pushed_date: str,
    gql_format: str,
    bulk_size: int = 100,
) -> dict:
    """Returns result from searching by last push date"""
    # pushed_date is used to specify the upper range of the dates
    search_query: str = f"language:{language} stars:{stars_query} pushed:2020-01-01..{pushed_date} archived:false"
    repos: dict = get_graphql_data(gql_format % (search_query, bulk_size, cursor))
    # If search result repositoryCount < 1000, parse the 1000 and move on to next star count
    while True:
        if "errors" in repos:
            sys.exit(f"Fetching repo metadata error: {repos['errors']}")
        elif int(stars_query) < 10:
            sys.exit("No more repos")
        # Keep searching until there are repos in the search result
        elif repos["data"]["search"]["repositoryCount"] != 0:
            break

        cursor = ""
        pushed_date = str(datetime.datetime.now().date())
        stars_query = str(int(stars_query) - 1)
        search_query = f"language:{language} stars:{stars_query} pushed:2020-01-01..{pushed_date} archived:false"
        repos = get_graphql_data(gql_format % (search_query, bulk_size, cursor))
    return repos


def find_repos(
    language: str,
    requirements: list[Callable[[dict, Optional[str]], bool]],
    reqs: list[str],
) -> int:
    """Searches for new repos based on query parameters and checks if they fit the requirements given while resources are available

    Args:
        search_query (list[str]): queries to narrow down the search
        requirements (list[callable]): List of requirement callables that check if repo meets requirement
        reqs (list[str]): List of values to check against for each callable
            - each req will be called with the callable of the same index in requirements

    Returns:
        int: number of remaining queries
    """

    gql_format = """
    query {
        rateLimit{
            cost
            remaining
            resetAt
        }
        search(query: "%s", type: REPOSITORY, first:%d %s) {
            repositoryCount
            pageInfo { endCursor }
            edges {
                node {
                    ...on Repository {
                        id
                        owner {
                            login
                        }
                        name
                        url
                        isArchived
                        isFork
                        isMirror
                        primaryLanguage {
                            name
                        }
                        pushedAt
                        stargazerCount
                        object(expression: "HEAD:") {
                            ... on Tree {
                                entries {
                                    name
                                    type
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """

    # Read in last used cursor
    # Cursor can specify where to start looking in search results, save to a file to know where to start searching next time
    if not os.path.exists(f"./data/repo_cursors/{language.lower()}_cursor.txt"):
        f = open(f"./data/repo_cursors/{language.lower()}_cursor.txt", "x")
        f.close()
    with open(f"./data/repo_cursors/{language.lower()}_cursor.txt", "r") as f:
        try:
            cursor, stars_query, last_stargazerCount, pushed_date, last_pushed_date = (
                f.read().strip().split("|")
            )
        except ValueError:
            cursor = ""
            stars_query = ">=10"
            last_stargazerCount = ""
            pushed_date = ""
            last_pushed_date = ""

    try:
        with open("./count.txt", "r") as f:
            repo_count = int(f.read())
    except:
        repo_count = 0

    bulk_size = 100  # How many repos to get at a time
    # Set cursor if it exists
    if cursor != "":
        cursor = f', after:"{cursor}"'

    if not stars_query.isnumeric():
        repos = search_by_stars(language, stars_query, cursor, gql_format, bulk_size)
    else:
        repos = search_by_last_push(
            language, stars_query, cursor, pushed_date, gql_format, bulk_size
        )
    if "errors" in repos:
        sys.exit(f"Fetching repo metadata error: {repos['errors']}")

    print(f'{repos["data"]["rateLimit"]}\n')

    new_cursor = repos["data"]["search"]["pageInfo"]["endCursor"]

    # Check repos
    repos_to_save = []
    edges = repos["data"]["search"]["edges"]
    for repo in edges:
        repo_count += 1
        repo_data = repo["node"]
        repo_name = f"{repo_data['owner']['login']}/{repo_data['name']}"
        if check_requirements(repo_name, requirements, reqs, repo_data):
            repos_to_save.append(repo_name)

    # Write each repo to a file
    print(f"Writing new repos to ./data/repo_meta/{language}.txt")
    save_repos_to_file(language.lower(), repos_to_save)

    # Save last stargazerCount and push date if search yielded any repos
    last_pushed_date = ""
    if len(edges) > 0:
        last_stargazerCount = edges[-1]["node"]["stargazerCount"]
        # If optimization was done in search_by_last_push, want to update stars_query
        if stars_query.isnumeric():
            stars_query = last_stargazerCount
        # Gets just the date portion of the date string
        last_pushed_date = edges[-1]["node"]["pushedAt"].split("T")[0]

    # Will only hit here once no more results, i.e. once all 1000 results from the search by stars have been parsed, switch to search by last push date
    # Set up for searching by last push date
    if new_cursor is None:
        new_cursor = ""
        if not stars_query.isnumeric():
            # Just finished searching by stars
            pushed_date = str(datetime.datetime.now().date())
            stars_query = last_stargazerCount
        else:
            # Either done with search or starting searching by last push date from a new star count
            if int(stars_query) < 10 or (
                int(stars_query) == 10
                and repos["data"]["search"]["repositoryCount"] < 1000
            ):
                # No more search results that can match criteria
                print("No more search results")
                sys.exit(1)
            elif repos["data"]["search"]["repositoryCount"] < 1000:
                # Start going through the push dates of a new star count
                stars_query = str(int(stars_query) - 1)
                pushed_date = str(datetime.datetime.now().date())
            else:
                # Go to next group of repos
                pushed_date = last_pushed_date

    with open(f"./data/repo_cursors/{language.lower()}_cursor.txt", "w") as f:
        # <cursor>|<stars_query>|<last_stargazerCount>|<pushed_date>|<last_pushed_date>
        f.write(
            f"{new_cursor}|{stars_query}|{last_stargazerCount}|{pushed_date}|{last_pushed_date}"
        )

    with open(f"./count.txt", "w") as f:
        f.write(str(repo_count))

    return int(repos["data"]["rateLimit"]["remaining"])


def save_repos_to_file(language: str, repos_list: list[str]) -> None:
    """Save the repository names to a file named new_<language>.txt in the data/repo_meta directory."""
    file_path = f"./data/repo_meta/{language}.txt"
    # Using "a" to append to the file if it already exists
    with open(file_path, "a") as file:
        for repo_name in repos_list:
            file.write(repo_name + "\n")

    # use OrderedDict to reduce repetition and keep the ordering
    with open(file_path, "r") as file:
        unique_repos = OrderedDict.fromkeys(file.read().splitlines())

    # write back to original txt
    with open(file_path, "w") as file:
        for repo in unique_repos:
            file.write(f"{repo}\n")


# Pass checks_list and reqs with this template: --checks_list='<list>' --reqs='<list>'
# Ex. --reqs='["0", "2020-1-1"]'
# If checking Rust fuzz path, put null in place of where the req should be in the reqs list
def main(
    language: str = "Java",
    checks_list: list[str] = ["stars", "latest commit"],
    reqs: list[str] = ["10", "2020-1-1"],  # Year format should be <year>-<month>-<day>
    num_searches: int = 1,  # How much of the rate limit to use (5000 max)
):
    # Set up requirement callables and reqs
    checks = [check_map[check] for check in checks_list]

    for _ in range(num_searches):
        if find_repos(language, checks, reqs) <= 0:
            print("Rate limit exhausted")
            break


if __name__ == "__main__":
    fire.Fire(main)

