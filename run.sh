#!/bin/bash

source .venv/bin/activate

if command -v brother_eye &> /dev/null; then
    brother_eye "$@"
else
    python -m main "$@"
fi