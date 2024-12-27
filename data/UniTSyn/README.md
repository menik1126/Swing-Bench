# UniTSyn

Multilingual **Uni**t **T**est and Function Source **Syn**hronization for CodeLLM.
Code for our ISSTA 2024 paper https://arxiv.org/abs/2402.03396.

## Requirements

- Python 3.10+
- `requirements.txt`
- [rustfmt](https://github.com/rust-lang/rustfmt) to use `frontend/rust/collect_fuzz.py`

### Language Server

To run this script on a new project, you need to install the corresponding language server:

| Language   | Language Server                                                                                        | Frontend | Backend  |
| ---------- | ------------------------------------------------------------------------------------------------------ | -------- | -------- |
| Python     | [pylsp](https://github.com/python-lsp/python-lsp-server)                                               | &#x2714; | &#x2714; |
| Java       | [java-language-server](https://github.com/georgewfraser/java-language-server)\*                        | &#x2714; | &#x2714; |
| JavaScript | [typescript-language-server](https://github.com/typescript-language-server/typescript-language-server) | &#x2714; | &#x2714; |
| Go         | [gopls](https://pkg.go.dev/golang.org/x/tools/gopls)                                                   | &#x2714; | &#x2714; |
| C/C++      | [clangd](https://clangd.llvm.org/installation.html)                                                    | &#x2714; | &#x2714; |

\*NOTE: you need git clone the repo to workdir of this project, then follow the instructions in the repo to install the language server.

You can find language server for other languages at
[language-server-protocol/implementors/servers](https://microsoft.github.io/language-server-protocol/implementors/servers/).
Other languages are not supported yet, but will be as the research progresses.
To support a new language, you need a frontend to do the following:

1. Collect the unit tests locations and focal functions locations in the repo (see `scripts/collect_test.py` and `scripts/collect_focal.py` for Python frontend).
2. Given a `Location` of function declaration, extract the function source code (see `unitsyncer/source_code.py`).

## Setup

```bash
mkdir -p data/focal data/repos data/repos_tarball data/tests
source ./scripts/env.sh
cd frontend/parser & python3 build.py
cd ../..
```

## Run

```bash
python3 scripts/download_repos.py
python3 scripts/decompress_repos.py

python3 frontend/<language>/collect_all.py
python3 main.py
```

## Automated Repo Mining

Automatic repo mining is supported through `scripts/find_repos.py`.  
Note: Please run `source ./scripts/env.sh` from the root of the repo before mining

Current checks that are supported are:

- "stars"
- "latest commit"
- "language"
- "fuzzers"

The corresponding value in `reqs` to check against should be at the same index as the check in `checks_list`.

```bash
# Command template
python3 scripts/find_repos.py --language='<language>' --checks_list='[<checks>]' --reqs='[<values>]' --num_searches='<num_searches>'

# Rust example
python3 scripts/find_repos.py --language='Rust' --checks_list='["stars", "latest commit", "language", "fuzzers"]' --reqs='["10", "2020-1-1", "Rust", None]' --num_searches='1'

# Python example
python3 scripts/find_repos.py --language='Python' --checks_list='["stars", "latest commit", "language"]' --reqs='["10", "2020-1-1", "Python"]' --num_searches='1'
```

Cursors representing where the search left off are saved to `data/repo_cursors/<language>_cursor.txt`. `find_repos.py` will automatically use and update this cursor to avoid mining duplicate repos.

# Reference

Please cite our work in your publications if it helps your research:

```biblatex
@inproceedings{he2024unitsyn,
    author = {He, Yifeng and Huang, Jiabo and Rong, Yuyang and Guo, Yiwen and Wang, Ethan and Chen, Hao},
    title = {UniTSyn: A Large-Scale Dataset Capable of Enhancing the Prowess of Large Language Models for Program Testing},  
    booktitle = {International Symposium on Software Testing and Analysis (ISSTA)},
    date = {2024-09-16/2024-09-20},
    address = {Vienna, Austria},
}
```
