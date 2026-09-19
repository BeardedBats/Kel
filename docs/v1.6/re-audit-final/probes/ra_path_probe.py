import sys
sys.path.insert(0, '.')
from kel.workforce import _path_within, authority_within

B = chr(92)  # backslash, kept as a variable to avoid source escapes
cases = [
    ('..', '.'), ('../x', '.'), ('', '.'), ('.', '.'), ('x', '.'),
    ('..', 'src'), ('a/../b', 'src'), ('SRC/child', 'src'), ('src/child ', 'src'),
    (' src/child', 'src'), ('src/child/../..', 'src'), ('src2', 'src'),
    ('C:evil', 'src'), ('//srv/share', 'src'), ('..' + B + '..' + B + 'x', 'src'),
    ('src' + B + '..' + B + 'secrets', 'src'), ('src/../src/child', 'src'),
]
for p, r in cases:
    print('%-22r | %-6r -> %s' % (p, r, _path_within(p, r)))

print('---- authority_within ----')
print('child [..] vs parent [.]:', authority_within({'write_scope': ['..']}, {'write_scope': ['.']}))
print('child [../x] vs parent [.]:', authority_within({'write_scope': ['../x']}, {'write_scope': ['.']}))
print('child [src2] vs parent [src]:', authority_within({'write_scope': ['src2']}, {'write_scope': ['src']}))
print('child [src/../secrets] vs parent [src]:', authority_within({'write_scope': ['src/../secrets']}, {'write_scope': ['src']}))
print('child [src/child] vs parent [src]:', authority_within({'write_scope': ['src/child']}, {'write_scope': ['src']}))
