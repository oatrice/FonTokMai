with open('frontend/src/app/radar-mockups/page.tsx', 'r') as f:
    content = f.read()
if 'Flow 0.5' not in content:
    new_flows = """
      {/* ======================= FLOW 0.5: MAP-CENTRIC PROTOTYPE ======================= */}
      <div className="max-w-[1400px] w-full mb-24">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Flow 0.5: Map-Centric (Full-screen Overlay, No Bottom Nav)</h2>
        <p className="text-slate-500 mb-8">เวอร์ชันนี้สามารถซ่อน UI ได้ด้วยการกดพื้นที่ว่างบนแผนที่ (Method 1) หรือปัด/กดที่ปุ่มมุมการ์ดด้านล่างเพื่อพับเก็บ (Method 2 & 3)</p>
        <RadarMockupsOverlayPrototype />
      </div>
"""
    content = content.replace('{/* ======================= FLOW 1: LOCATION SETUP ======================= */}', new_flows + '\n      {/* ======================= FLOW 1: LOCATION SETUP ======================= */}')
    with open('frontend/src/app/radar-mockups/page.tsx', 'w') as f:
        f.write(content)
