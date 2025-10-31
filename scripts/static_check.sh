#!/bin/bash
python -m pyflakes . || true
python -m pip check || true
