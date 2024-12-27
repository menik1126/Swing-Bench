# UniTSyncer Evaluation

## Requirements

### Python

Coverage report is provided by [coverage.py](https://coverage.readthedocs.io/en/7.4.0/),
please install it via

```sh
python3 -m pip install coverage
```

### C++

Coverage report is provided by [LLVM toolchain](https://github.com/llvm/llvm-project),
please install it via

```sh
bash -c "$(wget -O - https://apt.llvm.org/llvm.sh)"
```

or from GitHub release.

### Java

Coverage report is provided by [jacoco](https://github.com/jacoco/jacoco),
please download [jacoco-0.8.11.zip] from [its website](https://www.jacoco.org/jacoco/),

### Javascript

We use [istanbuljs/nyc](https://github.com/istanbuljs/nyc) to compute coverage.
Please download it to the system via

```sh
npm install -g nyc
```

We also require [nodejs](https://nodejs.org/en/download/current),
so please also down it.

### Golang

Golang's coverage is build in the compiler, so no need to install additional dependencies.
However, for go, it only supports **statement coverage**.

## Running Evaluation

```sh
python3 execution.py -j test_evaluation.jsonl
```

## Docker

In `UniTSyncer/evaluation`, run

```sh
docker build --tag unitsyncer-eval . -f dockerfiles/Dockerfile.eval
```
