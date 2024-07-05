#!/bin/bash

# Paths
MODULE_NAME="profusion"
SCRIPTS_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
MODULE_DIR="$(dirname $SCRIPTS_DIR)"
SRC_DIR="$MODULE_DIR/src/$MODULE_NAME"
TESTS_DIR="$MODULE_DIR/tests"

BLACK=black
BLACK_OPTS="--line-length 79"
LINTER=/usr/bin/flake8
GITIGNORE_URL="https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore"

# Update .gitignore if older than 30 days
GITIGNORE_PATH="$MODULE_DIR/.gitignore"
if [ ! -f $GITIGNORE_PATH ] || [ `find $GITIGNORE_PATH -mtime +30` ]; then
    echo "Updating .gitignore"
    wget -O $GITIGNORE_PATH $GITIGNORE_URL 2>/dev/null
fi

# Run black
echo "Running black"
$BLACK $BLACK_OPTS $SRC_DIR/*.py $TESTS_DIR/*.py

# Run linter
echo "Running linter"
$LINTER $SRC_DIR/*.py
if [ $? -ne 0 ]; then
    echo "Linting failed"
    exit 1
fi
echo "Linting passed"

# Run tests
echo "Running tests"
python3 -m unittest discover -s $TESTS_DIR
if [ $? -ne 0 ]; then
    echo "Tests failed"
    exit 1
fi

# Clean up
echo "Cleaning up"
find . -type d -name '__pycache__' -exec rm -r {} +
find . -type d -name '*.egg-info' -exec rm -r {} +

echo "Build successful"

exit 0