import os
import sys
import fire
import json
import time
import random
import tarfile
import requests
import calendar
from tqdm import tqdm
from github import Github, Repository, Auth
from typing import Tuple, Union, Optional

from frontend.util import log_or_skip, wrap_repo, time_limit, TimeoutException


def fetch_repo(repo_id: str, timeout: int, hub: Optional[Github]):
    """fetch a repo"""
    hub = hub if hub is not None else Github()
    try:
        with time_limit(timeout):
            repo = hub.get_repo(repo_id)
        return True, repo
    except Exception as e:
        return False, f"Fetch repo failed: {e}"


def fetch_archive(repo: Repository.Repository):
    """fetch the archive of a repo
    latest release -> latest tag -> latest commit
    """
    # try latest release
    try:
        return True, repo.get_latest_release()
    except:
        pass
    # try latest tag
    try:
        return True, next(iter(repo.get_tags()))
    except:
        pass
    # try latest commit
    try:
        commit = next(iter(repo.get_commits()))
        commit.tarball_url = (
            f"https://api.github.com/repos/{repo_id}/tarball/{commit.sha}"
        )
        return True, commit
    except Exception as e:
        return False, f"Fetch archive failed: {e}"


def download_archive(path: str, url: str, timeout: int):
    """download file from url to path with timeout limit"""
    try:
        with time_limit(timeout):
            resp = requests.get(url)
            resp.raise_for_status()
    except Exception as e:
        return False, f"Download failed: {e}"
    with open(path, "wb") as outfile:
        outfile.write(resp.content)
    return True, ""


def download_repo(
    hub: Github, repo_id: str, path: str, fetch_timeout: int, download_timeout: int
):
    """return status:
    0. successed
    1. fetch repo failed
    2. fetch archive failed
    3. download archive failed
    """
    # fetch the repo
    status, repo = fetch_repo(repo_id, timeout=fetch_timeout, hub=hub)
    if not status:
        return 1, (repo,)
    # fetch archive
    status, archive = fetch_archive(repo)
    if not status:
        return 2, (repo, archive)
    # download archive, skip downloading if target path existed
    if os.path.exists(path):
        status = True
    else:
        status, msg = download_archive(path, archive.tarball_url, download_timeout)
    if status:
        return 0, (repo, archive, path)
    return 3, (repo, archive, msg)


def main(
    repo_id_list: str = "ageitgey/face_recognition",
    fetch_timeout: int = 30,
    download_timeout: int = 300,
    delay: Union[Tuple[int], int] = -1,
    oroot: str = "data/repos_tarball/",
    log: Optional[str] = "meta.jsonl",
    limits: int = -1,
    decompress: bool = False,
    oauth: str = None,
):
    if log:
        log = os.path.join(oroot, log)
    # declare github object
    # oauth is provided for rate limit: https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#rate-limiting
    # 5k calls per hours if authorised, otherwise, 60 calls or some
    hub = None
    if oauth:
        try:
            hub = Github(auth=Auth.Token(oauth))
        except:
            pass
    if not hub:
        hub = Github()
    # if repo_id_list is a file then load lines
    # otherwise it is the id of a specific repo
    try:
        repo_id_list = [l.strip() for l in open(repo_id_list, "r").readlines()]
    except:
        repo_id_list = [repo_id_list]
    if limits >= 0:
        repo_id_list = repo_id_list[:limits]
    print(f"Loaded {len(repo_id_list)} repos to be downloaded")
    failed = {"repo": 0, "archive": 0, "download": 0}
    for repo_id in (pbar := tqdm(repo_id_list)):
        # log repo_id and rate limits
        rate = hub.get_rate_limit()
        pbar.set_description(
            f"Downloading {repo_id}, Rate: {rate.core.remaining}/{rate.core.limit}"
        )
        # download repo
        path = os.path.join(oroot, wrap_repo(repo_id)) + ".tar.gz"
        status, results = download_repo(
            hub, repo_id, path, fetch_timeout, download_timeout
        )
        if status == 0:
            repo, archive, path = results
            err_msg = ""
            log_or_skip(
                log,
                repo_id=repo_id,
                repo=repo.clone_url,
                archive=archive.tarball_url,
                download=path,
            )
            if decompress:
                try:
                    tarfile.open(path).extractall(".".join(path.split(".")[:-2]))
                except:
                    pass
        elif status == 1:
            failed["repo"] += 1
            err_msg = results[0]
            log_or_skip(log, repo_id=repo_id, repo=err_msg)
        elif status == 2:
            failed["archive"] += 1
            repo, err_msg = results
            log_or_skip(log, repo_id=repo_id, repo=repo.clone_url, archive=err_msg)
        elif status == 3:
            failed["download"] += 1
            repo, archive, err_msg = results
            log_or_skip(
                log,
                repo_id=repo_id,
                repo=repo.clone_url,
                archive=archive.tarball_url,
                download=err_msg,
            )
        # delay
        sleep_time = delay if isinstance(delay, int) else random.randint(*delay)
        if "rate limit exceeded" in err_msg:
            reset_at = calendar.timegm(rate.core.reset.timetuple())
            sleep_time = reset_at - calendar.timegm(time.gmtime()) + 5
            print(f"Rate limits exceeded, sleep for {sleep_time} seconds")
        if sleep_time > 0:
            time.sleep(sleep_time)

    if sum(failed.values()):
        print("Failed:", {key: val for key, val in failed.items() if val})
    print("Done!")


if __name__ == "__main__":
    fire.Fire(main)
