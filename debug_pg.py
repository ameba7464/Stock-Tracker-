"""Debug script to trace psycopg2 file reads."""
import sys

old_open = open
opened_files = []

def traced_open(*args, **kwargs):
    try:
        filename = str(args[0]) if args else "unknown"
        if 'pg' in filename.lower() or 'conf' in filename.lower():
            opened_files.append(filename)
            print(f"Opening: {filename}", file=sys.stderr)
    except:
        pass
    return old_open(*args, **kwargs)

import builtins
builtins.open = traced_open

try:
    import psycopg2
    conn = psycopg2.connect('postgresql://stock_tracker:stock_tracker_password@127.0.0.1:5432/stock_tracker')
    print("Connected successfully!")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
    
print("\nFiles accessed:")
for f in opened_files:
    print(f"  - {f}")
