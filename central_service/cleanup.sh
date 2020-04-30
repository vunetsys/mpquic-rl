#!/bin/bash

echo "Cleaning up..."
find . -type d -name "https_quic_*" -exec rm -rf {} +