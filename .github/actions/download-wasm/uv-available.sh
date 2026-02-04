#!/usr/bin/env bash

if command -v uv >/dev/null 2>&1; then
	echo "uv-available=true"
else
	echo "uv-available=false"
fi
