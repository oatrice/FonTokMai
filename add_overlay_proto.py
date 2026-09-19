import re

with open('frontend/src/app/radar-mockups/page.tsx', 'r') as f:
    content = f.read()

# First, make sure Menu and ChevronLeft are imported
if 'Menu,' not in content:
    content = content.replace('import { ', 'import { Menu, ChevronLeft, ')

# Read the existing prototype body to duplicate it
proto_body_match = re.search(r'function RadarMockupsPrototype\(\) \{(.*?)\n\}\n', content, re.DOTALL)
if not proto_body_match:
    print("Could not find RadarMockupsPrototype")
    exit(1)

proto_body = proto_body_match.group(1)

# Now, apply transformations to create RadarMockupsOverlayPrototype

# 1. Add back buttons to renderPlaces and renderAdmin
places_replace = """
      <div className="flex items-center gap-4 mb-8">
        <button onClick={() => setCurrentScreen('map')} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors">
           <ChevronLeft className="w-6 h-6 text-slate-300" />
        </button>
        <h1 className="text-3xl font-semibold text-white tracking-tight m-0">My Places</h1>
      </div>
"""
proto_body = re.sub(r'<h1 className="text-3xl font-semibold mb-8 text-white tracking-tight">My Places</h1>', places_replace.strip(), proto_body)

admin_replace = """
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <button onClick={() => setCurrentScreen('map')} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors">
             <ChevronLeft className="w-6 h-6 text-slate-300" />
          </button>
          <h1 className="text-xl font-bold text-emerald-400 tracking-tight flex items-center gap-2 m-0">
            <Database className="w-5 h-5" />
            Admin
          </h1>
        </div>
        <div className="flex items-center gap-2 text-xs bg-emerald-950/50 text-emerald-500 px-3 py-1 rounded-full border border-emerald-900">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          LIVE
        </div>
      </div>
"""
proto_body = re.sub(r'<div className="flex items-center justify-between mb-8">.*?LIVE\n\s*</div>\n\s*</div>', admin_replace.strip(), proto_body, flags=re.DOTALL)

# 2. Add Top-left Menu button and hidden Admin button to renderMainMap
top_ui_replace = """
      {/* Top UI: Header Dropdown & Overview */}
      <div className="absolute top-12 left-4 right-4 flex justify-between items-start z-30">
        
        <div className="flex items-center gap-2">
          {/* Main Menu Button (replaces bottom nav Places tab) */}
          <button 
            onClick={() => setCurrentScreen('places')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border shadow-lg border-slate-700 text-white"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* Header Dropdown (Seamless Location Browsing) */}
"""
proto_body = proto_body.replace('{/* Top UI: Header Dropdown & Overview */}\n      <div className="absolute top-12 left-4 right-4 flex justify-between items-start z-30">\n        \n        {/* Header Dropdown (Seamless Location Browsing) */}', top_ui_replace)

# Add admin button somewhere on the map (e.g. top right corner below the layer switchers)
overview_replace = """
          <button 
            onClick={() => setLayerMode(prev => prev === 'minimal' ? 'pro' : 'minimal')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border border-slate-700 shadow-lg text-slate-400"
          >
            <Layers className={`w-5 h-5 ${layerMode === 'pro' ? 'text-emerald-400' : 'text-slate-400'}`} />
          </button>
          
          {/* Secret Admin Button */}
          {isAdmin && (
            <button 
              onClick={() => setCurrentScreen('admin')}
              className="mt-2 w-11 h-11 bg-emerald-900/80 backdrop-blur-md rounded-2xl flex items-center justify-center border border-emerald-700/50 shadow-lg text-emerald-400"
            >
              <Bug className="w-5 h-5" />
            </button>
          )}
        </div>
"""
proto_body = proto_body.replace("""
          <button 
            onClick={() => setLayerMode(prev => prev === 'minimal' ? 'pro' : 'minimal')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border border-slate-700 shadow-lg text-slate-400"
          >
            <Layers className={`w-5 h-5 ${layerMode === 'pro' ? 'text-emerald-400' : 'text-slate-400'}`} />
          </button>
        </div>
""".strip(), overview_replace.strip())


# 3. Remove Bottom Navigation from the main layout
bottom_nav_regex = r'\{/\* Bottom Navigation \*/\}.*?\{/\* iOS Home Indicator \*/\}'
proto_body = re.sub(bottom_nav_regex, '{/* iOS Home Indicator */}', proto_body, flags=re.DOTALL)

# Also fix the bottom timeline scrubber position. Since there's no 80px bottom nav, we can push it down slightly to bottom-10 instead of bottom-24
proto_body = proto_body.replace('className="absolute bottom-24 left-4 right-4 z-30"', 'className="absolute bottom-10 left-4 right-4 z-30"')

overlay_comp = f"\nfunction RadarMockupsOverlayPrototype() {{\n{proto_body}\n}}\n"

# Insert the new component right after the existing RadarMockupsPrototype
insert_idx_comp = content.find('\nexport default function RadarMockupsPage() {')
content = content[:insert_idx_comp] + overlay_comp + content[insert_idx_comp:]

# Insert the invocation of the new prototype into the page
insert_idx_page = content.find('{/* ======================= FLOW 1: LOCATION SETUP ======================= */}')
new_flow = """
      {/* ======================= FLOW 0.5: MAP-CENTRIC PROTOTYPE ======================= */}
      <div className="max-w-[1400px] w-full mb-24">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Flow 0.5: Map-Centric (Full-screen Overlay, No Bottom Nav)</h2>
        <p className="text-slate-500 mb-8">เวอร์ชันนี้ซ่อนแท็บด้านล่างทิ้งเพื่อให้แผนที่เต็มจอ และใช้ปุ่ม Menu ซ้ายบนในการเปิดหน้าต่าง Places / Admin แบบเต็มจอ</p>
        <RadarMockupsOverlayPrototype />
      </div>
"""
content = content[:insert_idx_page] + new_flow + "\n" + content[insert_idx_page:]

with open('frontend/src/app/radar-mockups/page.tsx', 'w') as f:
    f.write(content)

