import requests
import time

"""
Functions from github ranking repo:
https://github.com/EvanLi/Github-Ranking/blob/master/source/
"""


def check_metadata_decorator(func):
    """Decorator function to check metadata keys and value types returned by Github GraphQL API"""

    def check_metadata(*args, **kwargs):
        required_keys = [
            ("id", str),
            ("owner", dict),
            ("name", str),
            ("url", str),
            ("isArchived", bool),
            ("isFork", bool),
            ("isMirror", bool),
            ("primaryLanguage", dict),
            ("pushedAt", str),
            ("stargazerCount", int),
            ("object", dict),
        ]
        improper_fields = []
        for key, t in required_keys:
            if not (key in args[0] and type(args[0][key]) is t):
                improper_fields.append(key)

        if len(improper_fields) > 0:
            print(f"Metadata JSON does not contain the proper keys: {improper_fields}")
            return False
        return func(*args, **kwargs)

    return check_metadata


def get_access_token():
    with open("./oauth", "r") as f:
        access_token = f.read().strip()
    return access_token


def get_graphql_data(GQL: str) -> dict:
    """
    use graphql to get data
    """
    access_token = get_access_token()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.113 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Authorization": "bearer {}".format(access_token),
    }
    s = requests.session()
    s.keep_alive = False  # don't keep the session
    graphql_api = "https://api.github.com/graphql"
    for _ in range(5):
        time.sleep(2)  # not get so fast
        try:
            # requests.packages.urllib3.disable_warnings() # disable InsecureRequestWarning of verify=False,
            r = requests.post(
                url=graphql_api, json={"query": GQL}, headers=headers, timeout=30
            )
            if r.status_code != 200:
                print(
                    f"Can not retrieve from {GQL}. Response status is {r.status_code}, content is {r.content}."
                )
            else:
                return r.json()
        except Exception as e:
            print(e)
            time.sleep(5)

