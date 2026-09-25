import re

with open('frontend/src/app/radar-mockups/page.tsx', 'r') as f:
    old_content = f.read()

with open('/tmp/new_protos.tsx', 'r') as f:
    protos_content = f.read()

# Fix imports in old_content
old_imports_line = re.search(r"import \{ .* \} from 'lucide-react';", old_content).group(0)
new_imports_line = "import { Menu, ChevronDown, ChevronUp, ChevronLeft, Activity, AlertCircle, AlertTriangle, BarChart2, Bell, BellOff, Bug, Check, CheckCircle2, ChevronRight, Clock, CloudLightning, CloudRain, Crosshair, Database, Droplets, Gauge, Layers, Map, MapPin, Navigation, Pause, Play, Power, Search, Settings, Shield, ShieldAlert, Sliders, SplitSquareVertical, Star, Sun, Target, Wind, Zap, Plus, Save, BellRing } from 'lucide-react';"
old_content = old_content.replace(old_imports_line, new_imports_line)

# Add type definitions
type_defs = """
type AppScreen = 'map' | 'places' | 'admin' | 'add_place';
type NotificationPolicy = 'always' | 'ask' | 'schedule' | 'silent';
type AdminToolMode = 'none' | 'calibrate' | 'lock';
"""
old_content = old_content.replace(new_imports_line, new_imports_line + "\n" + type_defs)

# Insert the invocation of the new prototypes at the VERY END of RadarMockupsPage return block
injection = """
      <div className="max-w-7xl w-full text-center mt-16 mb-8 border-t-2 border-slate-200 pt-16">
        <h1 className="text-4xl font-bold mb-3 text-slate-900">NEW: App Flows & Interactions</h1>
        <p className="text-slate-500 text-lg">UX Interaction สำหรับ Flow จริงและการเปิดปิด UI แผนที่</p>
      </div>

      <div className="max-w-[1400px] w-full flex flex-col items-center gap-16 mb-24">
        <div className="w-full">
          <h2 className="text-2xl font-bold text-slate-800 mb-2 pb-2">Flow 0: Interactive Prototype (Bottom Navigation)</h2>
          <RadarMockupsPrototype />
        </div>
        <div className="w-full">
          <h2 className="text-2xl font-bold text-slate-800 mb-2 pb-2">Flow 0.5: Map-Centric (Full-screen Overlay, No Bottom Nav)</h2>
          <RadarMockupsOverlayPrototype />
        </div>
      </div>
"""

# Find the LAST occurrence of "    </div>\n  );\n}" in old_content
pattern = "    </div>\n  );\n}"
idx = old_content.rfind(pattern)
if idx != -1:
    old_content = old_content[:idx] + injection + pattern + old_content[idx+len(pattern):]

# Insert prototypes right before export default function
old_content = old_content.replace("export default function RadarMockupsPage() {", protos_content + "\nexport default function RadarMockupsPage() {")

with open('frontend/src/app/radar-mockups/page.tsx', 'w') as f:
    f.write(old_content)

