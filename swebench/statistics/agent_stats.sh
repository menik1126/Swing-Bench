#! /bin/bash

python swebench/statistics/agent_stats.py > agent_stats.log
python swebench/statistics/accumulate_agent_stats.py > accumulate_agent_stats.log