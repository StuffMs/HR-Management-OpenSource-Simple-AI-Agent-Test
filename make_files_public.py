import sys
from app import drive_helper

# List of file IDs to make public
file_ids = [
    '13z4QzYSYbDQPbs9DoPKYYTTf6bAToicx',
    '162Np2qC3cGPYg7vsJ67lXkXDQPitmedR',
    '1dO2pytE69j_egK-8ryTe1RSBKuumKfy4',
    '1OU_1TqkGonpelr9iaQTdvOW7BHraqU0S',
    '1K2XQYaXT_t01wL895ct-mQpZydet2xva',
    '1jugXLTxhQ8j1g5SBME9PsvXoDquzjBD1',
    '1hJ_ASv7x96tvzTrbKtujYngEIfUXYfTa'
]

# Make each file public
for file_id in file_ids:
    print(f"Making file {file_id} public...")
    drive_helper.make_file_public(file_id)
    
print("Done!")