#! /bin/bash

python Swingbench/statistics/agent_stats.py --language rust > agent_stats_rust.log
python Swingbench/statistics/agent_stats.py --language python > agent_stats_python.log
python Swingbench/statistics/agent_stats.py --language go > agent_stats_go.log
python Swingbench/statistics/agent_stats.py --language cpp > agent_stats_cpp.log