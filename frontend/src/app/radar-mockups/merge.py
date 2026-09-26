import re

with open('page.tsx', 'r') as f:
    page = f.read()

with open('prototype.tsx', 'r') as f:
    proto = f.read()

# Extract imports from proto
proto_imports = re.findall(r'import .*? from .*?;', proto, re.DOTALL)
page_imports = re.findall(r'import .*? from .*?;', page, re.DOTALL)

# Combine imports
all_lucide = set()
for imp in proto_imports + page_imports:
    if 'lucide-react' in imp:
        matches = re.search(r'\{([^}]+)\}', imp)
        if matches:
            items = [x.strip() for x in matches.group(1).split(',')]
            all_lucide.update(items)

final_imports = f"import React, {{ useState, useEffect }} from 'react';\nimport {{ {', '.join(sorted(list(all_lucide)))} }} from 'lucide-react';\n"

# Extract proto component body
proto_body_match = re.search(r'export default function RadarMockupsPrototype\(\) \{(.*?)\n\}\n*$', proto, re.DOTALL)
proto_comp = ""
if proto_body_match:
    proto_comp = f"""
type AppScreen = 'map' | 'places' | 'admin';
type NotificationPolicy = 'always' | 'ask' | 'schedule' | 'silent';
type SnoozeDuration = 'active' | '1h' | '4h' | '24h';
type AdminToolMode = 'none' | 'calibrate' | 'lock';

function RadarMockupsPrototype() {{
{proto_body_match.group(1)}
}}
"""

# Extract page body
page_body_match = re.search(r'export default function RadarMockupsPage\(\) \{(.*?)\n\}\n*$', page, re.DOTALL)
page_body = page_body_match.group(1)

# Modify page_body to include the prototype at the top
insert_idx = page_body.find('{/* ======================= FLOW 1: LOCATION SETUP ======================= */}')

new_page_body = page_body[:insert_idx] + """
      {/* ======================= FLOW 0: INTERACTIVE PROTOTYPE ======================= */}
      <div className="max-w-[1400px] w-full mb-24">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Flow 0: Interactive Prototype (New Features)</h2>
        <p className="text-slate-500 mb-8">รวมหน้าจอ Admin / My Places / Map Layers ไว้ใน Prototype ตัวนี้</p>
        <RadarMockupsPrototype />
      </div>

""" + page_body[insert_idx:]


final_file = final_imports + proto_comp + "\nexport default function RadarMockupsPage() {\n" + new_page_body + "\n}\n"

with open('merged.tsx', 'w') as f:
    f.write(final_file)

