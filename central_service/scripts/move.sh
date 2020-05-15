#!/bin/bash

echo "Moving all https_quic_* folders under experiments/"
find . -iname 'https_quic_*' -type d -exec mv '{}' experiments/ \;