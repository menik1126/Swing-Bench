"""util functions for UniTSyncer frontend"""
import os
import sys
import ast
import json
import time
import signal
import datetime
import functools
import contextlib
from tqdm import tqdm
from typing import (
    Optional,
    Callable,
    List,
    Any,
    Dict,
    Iterable,
    Set,
    Tuple,
    TypeVar,
)
from pathos.multiprocessing import ProcessPool
import subprocess


class Timing:
    """providing timing as context or functions"""

    queue: list = []

    def __enter__(self):
        self.tic()
        return self

    def __exit__(self, *args):
        self.tac()

    @staticmethod
    def tic():
        Timing.queue.append(time.time())

    @staticmethod
    def tac():
        assert Timing.queue, "Call Timing.tic before"
        start_at = Timing.queue.pop()
        print(f"Elapsed {datetime.timedelta(seconds=time.time() - start_at)}")


def log_or_skip(path: Optional[str] = None, handler=json.dumps, **kwargs):
    """log kwargs if path is provided with handler for preprocessing"""
    if not path:
        return
    with open(path, "a") as outfile:
        to_log = kwargs
        if handler:
            to_log = handler(to_log)
        outfile.write(f"{to_log}\n")


def wrap_repo(name: str):
    """wrap repo name from username/repo into username?repo"""
    return "-".join(name.split("/"))


class TimeoutException(Exception):
    """Wrapper Exception for Frontend Timeout"""

    pass  # pylint: disable=unnecessary-pass


@contextlib.contextmanager
def time_limit(seconds: float):
    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.setitimer(signal.ITIMER_REAL, seconds)
    signal.signal(signal.SIGALRM, signal_handler)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


def timestamp(frmt="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.now().strftime(frmt)


def timeout_wrapper(handler: Callable, timeout: int = -1):
    """return None if timeout instead of raising error"""

    def inner(*args, **kwargs):
        if timeout <= 0:
            return handler(*args, **kwargs)
        try:
            with time_limit(timeout):
                return handler(*args, **kwargs)
        except TimeoutException:
            pass
        return None

    return inner


def mp_map_repos(handler: Callable, repo_id_list: List[str], nprocs: int = 0, **kwargs):
    """conduct an unorder map at the level of repo using handler
    make sure handler take a string of repo_id as the first ordered arg
    other args can be passed as named args by kwargs
    """
    results = []
    if nprocs < 1:
        for repo_id in (pbar := tqdm(repo_id_list)):
            pbar.set_description(f"{timestamp()} Processing {repo_id}")
            results.append(handler(repo_id, **kwargs))
    else:
        with ProcessPool(nprocs) as p:
            with tqdm(total=len(repo_id_list)) as pbar:
                for status in p.uimap(
                    functools.partial(handler, **kwargs), repo_id_list
                ):
                    results.append(status)
                    pbar.set_description(timestamp())
                    pbar.update()
    return results


def run_with_timeout(func: Callable):
    """run a function with timeout"""

    def wrapper(*args, timeout=-1, **kwargs):
        if timeout <= 0:
            return func(*args, **kwargs)
        try:
            with time_limit(timeout):
                return func(*args, **kwargs)
        except TimeoutException:
            pass
        return None

    return wrapper


__T = TypeVar("__T")
__R = TypeVar("__R")


def parallel_subprocess(
    iterable: Iterable[__T],
    jobs: int,
    subprocess_creator: Callable[[__T], subprocess.Popen],
    on_exit: Optional[Callable[[subprocess.Popen], __R]] = None,
    use_tqdm=True,
    tqdm_leave=True,
    tqdm_msg="",
) -> Dict[__T, __R]:
    """
    Creates `jobs` subprocesses that run in parallel.
    `iter` contains input that is send to each subprocess.
    `subprocess_creator` creates the subprocess and returns a `Popen`.
    After each subprocess ends, `on_exit` will go collect user defined input and return.
    The return valus is a dictionary of inputs and outputs.

    User has to guarantee elements in `iter` is unique, or the output may be incorrect.
    """
    ret = {}
    processes: Set[Tuple[subprocess.Popen, __T]] = set()
    if use_tqdm:
        iterable = tqdm(iterable, leave=tqdm_leave, desc=tqdm_msg)
    for _input in iterable:
        processes.add((subprocess_creator(_input), _input))
        if len(processes) >= jobs:
            # wait for a child process to exit
            os.wait()
            exited_processes = [(p, i) for p, i in processes if p.poll() is not None]
            for p, i in exited_processes:
                processes.remove((p, i))
                if on_exit is not None:
                    ret[i] = on_exit(p)
    # wait for remaining processes to exit
    for p, i in processes:
        p.wait()
        # let `on_exit` to decide wait for or kill the process
        if on_exit is not None:
            ret[i] = on_exit(p)
    return ret
