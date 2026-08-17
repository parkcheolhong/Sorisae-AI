#!/usr/bin/env python3
import re

# Read docker-compose.yml
with open('docker-compose.yml', 'r') as f:
    content = f.read()

# Find and fix CORS_ORIGINS
# Pattern: two CORS_ORIGINS lines, one old and one new with wrong indentation
pattern = r'(      CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127\.0\.0\.1:3000,http://127\.0\.0\.1:3005)\s+(CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127\.0\.0\.1:3000,http://127\.0\.0\.1:3005,https://metanova1004\.com,https://xn--114-2p7l635dz3bh5j\.com)'

# Replace with single corrected line
replacement = r'      CORS_ORIGINS: http://localhost:3000,http://localhost:3005,http://127.0.0.1:3000,http://127.0.0.1:3005,https://metanova1004.com,https://xn--114-2p7l635dz3bh5j.com'

content = re.sub(pattern, replacement, content)

# Write back
with open('docker-compose.yml', 'w') as f:
    f.write(content)

print("✓ Fixed docker-compose.yml CORS_ORIGINS")

# Verify
with open('docker-compose.yml', 'r') as f:
    for i, line in enumerate(f, 1):
        if 'CORS_ORIGINS' in line:
            print(f"  Line {i}: {line.rstrip()}")
