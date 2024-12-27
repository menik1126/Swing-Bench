#!/bin/bash
# Environment setup for non-docker user.
export UNITSYNCER_HOME=`pwd`
export CORES=`nproc`

export PYTHONPATH=$PYTHONPATH:$UNITSYNCER_HOME