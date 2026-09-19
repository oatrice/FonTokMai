import re

with open('frontend/src/app/radar-mockups/page.tsx', 'r') as f:
    content = f.read()

# 1. Update Map Overview to show labels in Prototype (Flow 0) and Overlay Prototype (Flow 0.5)
overview_replacement = """<div className="absolute inset-0 z-10 pointer-events-none">
           <div className="absolute top-[45%] left-[45%] flex flex-col items-center">
             <span className="text-[10px] font-bold text-white bg-slate-900/80 px-2 py-0.5 rounded-full mb-1 border border-blue-500/50">บ้าน</span>
             <MapPin className="text-blue-500 w-6 h-6 fill-blue-500/20 animate-bounce" />
           </div>
           <div className="absolute top-[60%] left-[65%] flex flex-col items-center">
             <span className="text-[10px] font-bold text-white bg-slate-900/80 px-2 py-0.5 rounded-full mb-1 border border-emerald-500/50">ที่ทำงาน</span>
             <MapPin className="text-emerald-500 w-6 h-6 fill-emerald-500/20" />
           </div>
           <div className="absolute top-[30%] left-[40%] flex flex-col items-center">
             <span className="text-[10px] font-bold text-white bg-slate-900/80 px-2 py-0.5 rounded-full mb-1 border border-purple-500/50">โรงเรียนลูก</span>
             <MapPin className="text-purple-500 w-6 h-6 fill-purple-500/20" />
           </div>
         </div>"""

old_overview = """<div className="absolute inset-0 z-10 pointer-events-none">
           <div className="absolute top-[45%] left-[45%]"><MapPin className="text-blue-500 w-6 h-6 fill-blue-500/20 animate-bounce" /></div>
           <div className="absolute top-[60%] left-[65%]"><MapPin className="text-emerald-500 w-6 h-6 fill-emerald-500/20" /></div>
           <div className="absolute top-[30%] left-[40%]"><MapPin className="text-purple-500 w-6 h-6 fill-purple-500/20" /></div>
         </div>"""

content = content.replace(old_overview, overview_replacement)

# 2. Add lat/lng to Add Place form
lat_lng_snippet = """             <div>
               <label className="block text-sm font-semibold text-slate-700 mb-1.5">ชื่อสถานที่</label>
               <input type="text" placeholder="เช่น บ้าน, ที่ทำงาน" defaultValue="ร้านกาแฟประจำ" className="w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none" />
             </div>
             
             <div className="flex justify-between items-center bg-slate-100 border border-slate-200 rounded-xl px-4 py-3 text-sm">
               <span className="text-slate-500 font-medium">พิกัด (Coordinates)</span>
               <span className="text-blue-500 font-mono font-medium">13.7563° N, 100.5018° E</span>
             </div>"""

old_lat_lng = """             <div>
               <label className="block text-sm font-semibold text-slate-700 mb-1.5">ชื่อสถานที่</label>
               <input type="text" placeholder="เช่น บ้าน, ที่ทำงาน" defaultValue="ร้านกาแฟประจำ" className="w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none" />
             </div>"""

content = content.replace(old_lat_lng, lat_lng_snippet)

with open('frontend/src/app/radar-mockups/page.tsx', 'w') as f:
    f.write(content)

