#!/bin/bash

TARGET=$1
RUSTFLAGS="-C instrument-coverage" LLVM_PROFILE_FILE="$TARGET-%p-%m.profraw" cargo test $TARGET &> /dev/null
grcov $TARGET*.profraw -s . --binary-path ./target/debug/ -t html --branch --ignore-not-existing -o ./target/debug/coverage/$TARGET
rm $TARGET*.profraw

