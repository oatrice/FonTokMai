import ast

def extract_methods(filepath, methods_to_extract):
    with open(filepath, "r") as f:
        src = f.read()

    # Just use regex to find start of method and extract block
    # It's easier than AST if we just want to grab raw text
    return src

import re
def extract_def(src, method_name):
    # finds "    def method_name(" and captures until next "    def " or end of class
    pattern = r'(?m)^    (?:@staticmethod\n    )?def ' + method_name + r'\(.*?(?=\n    (?:@staticmethod\n    )?def |\Z)'
    match = re.search(pattern, src, re.DOTALL)
    if match:
        return match.group(0)
    return None

with open('backend/app/services/tmd_radar/tracking.py', 'r') as f:
    tr_src = f.read()

with open('backend/app/services/tmd_radar/multiframe.py', 'r') as f:
    mf_src = f.read()

m1 = extract_def(tr_src, 'generate_radar_tracking_image')
m2 = extract_def(tr_src, 'generate_timeline_image')
m3 = extract_def(tr_src, 'render_rain_summary')
m4 = extract_def(tr_src, 'draw_pin_on_frame')
m5 = extract_def(tr_src, '_resolve_label_collisions')
m6 = extract_def(mf_src, 'generate_multiframe_analysis_image')

print("m1 len:", len(m1) if m1 else "None")
print("m2 len:", len(m2) if m2 else "None")
print("m3 len:", len(m3) if m3 else "None")
print("m4 len:", len(m4) if m4 else "None")
print("m5 len:", len(m5) if m5 else "None")
print("m6 len:", len(m6) if m6 else "None")

