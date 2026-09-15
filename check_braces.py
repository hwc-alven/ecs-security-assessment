with open(r'N:\codearts\server_src\app_fixed.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Count braces
open_braces = content.count('{')
close_braces = content.count('}')
print('Open braces: %d' % open_braces)
print('Close braces: %d' % close_braces)
print('Difference: %d' % (open_braces - close_braces))

# Find where the imbalance is - track running balance
lines = content.split('\n')
depth = 0
for i, line in enumerate(lines):
    for ch in line:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    if depth < 0:
        print('Negative depth at line %d: %d' % (i+1, depth))
        break

print('Final depth: %d' % depth)

# Show lines around 195-230 to see the removeServer area
print()
print('=== Lines 195-230 ===')
for i in range(194, min(230, len(lines))):
    print('%d: %s' % (i+1, lines[i]))