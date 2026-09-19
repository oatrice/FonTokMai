import React from 'react';
import { MapPin, CloudRain, Clock, Wind, AlertCircle, Droplets, Sun, Navigation, Play, ChevronRight, Activity, BarChart2, Search, Crosshair, Star, Map, Layers, Check, ThermometerSun } from 'lucide-react';

export default function RadarMockupsPage() {
  return (
    <div className="min-h-screen bg-slate-50 p-8 flex flex-col items-center font-sans">
      <div className="max-w-7xl w-full text-center mb-12">
        <h1 className="text-3xl font-semibold mb-3 text-slate-900">Mobile UI Flow & Style Variants</h1>
        <p className="text-slate-500">เปรียบเทียบ 3 สไตล์: A (Glass), B (Minimal Light), C (Immersive Gradient)</p>
      </div>

      {/* ======================= FLOW 1: LOCATION SETUP ======================= */}
      <div className="max-w-[1400px] w-full mb-20">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Step 1: Location Setup (ขอพิกัดปัจจุบัน / ค้นหาสถานที่)</h2>
        <div className="flex flex-wrap justify-center gap-10 mt-8">
          
          {/* 1 - Style A: Glassmorphism */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-blue-600">Style A: Glassmorphism (Dark)</h3>
            <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-xl flex flex-col">
              <div className="absolute inset-0 bg-cover bg-center opacity-30 blur-md grayscale" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
              <div className="absolute inset-0 bg-slate-950/60" />
              <div className="relative z-10 w-full h-full flex flex-col pt-20 px-6">
                <h1 className="text-2xl font-semibold mb-6 text-white text-center">ค้นหาพิกัด</h1>
                <div className="relative mb-6">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                  <input type="text" placeholder="พิมพ์ชื่อเขต, จังหวัด..." className="w-full bg-slate-800/80 border border-slate-700 rounded-2xl py-4 pl-12 pr-4 text-white placeholder-slate-400 focus:outline-none backdrop-blur-md" />
                </div>
                <button className="flex items-center gap-4 bg-blue-600/20 border border-blue-500/30 rounded-2xl p-4 w-full mb-4 hover:bg-blue-600/30">
                  <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0">
                    <Crosshair className="w-5 h-5 text-blue-400" />
                  </div>
                  <div className="text-left flex-1">
                    <h3 className="font-semibold text-blue-400 text-sm">ใช้ตำแหน่งปัจจุบัน</h3>
                    <p className="text-xs text-blue-300/70 mt-0.5">ระบบจะขอสิทธิ์ GPS</p>
                  </div>
                </button>
                <button className="flex items-center gap-4 bg-slate-800/40 border border-slate-600/40 rounded-2xl p-4 w-full mb-8 hover:bg-slate-700/50">
                  <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center shrink-0">
                    <Map className="w-5 h-5 text-slate-300" />
                  </div>
                  <div className="text-left flex-1">
                    <h3 className="font-semibold text-slate-200 text-sm">ปักหมุดบนแผนที่</h3>
                    <p className="text-xs text-slate-400 mt-0.5">เลือกพิกัดด้วยตัวเอง</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-500" />
                </button>
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">บันทึกไว้</h3>
                <button className="flex items-center gap-4 bg-slate-800/50 border border-slate-700/50 rounded-2xl p-4 w-full text-left backdrop-blur-sm">
                  <div className="w-10 h-10 rounded-full bg-slate-700/50 flex items-center justify-center shrink-0">
                    <Star className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-200 text-sm">บ้าน</h4>
                    <p className="text-xs text-slate-400 mt-0.5">บางนา, กรุงเทพฯ</p>
                  </div>
                </button>
              </div>
            </div>
          </div>

          {/* 1 - Style B: Minimal Light */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-emerald-600">Style B: Minimal (Light)</h3>
            <div className="w-[375px] h-[812px] bg-white rounded-[40px] border-[8px] border-slate-200 overflow-hidden relative shadow-xl flex flex-col pt-20 px-6">
              <h1 className="text-2xl font-bold mb-6 text-slate-900">ค้นหาพิกัด</h1>
              <div className="relative mb-6 shadow-sm">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input type="text" placeholder="ค้นหาเขต, จังหวัด..." className="w-full bg-slate-50 border border-slate-200 rounded-xl py-4 pl-12 pr-4 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <button className="flex items-center gap-4 bg-blue-50 border border-blue-100 rounded-xl p-4 w-full mb-3 hover:bg-blue-100/50">
                <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                  <Navigation className="w-5 h-5 text-blue-600" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="font-semibold text-blue-700 text-sm">ตำแหน่งปัจจุบัน</h3>
                  <p className="text-xs text-blue-600/70 mt-0.5">แตะเพื่ออนุญาต GPS</p>
                </div>
              </button>
              <button className="flex items-center gap-4 bg-white border border-slate-200 rounded-xl p-4 w-full mb-8 shadow-sm hover:bg-slate-50">
                <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                  <Map className="w-5 h-5 text-slate-600" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="font-semibold text-slate-700 text-sm">ปักหมุดบนแผนที่</h3>
                  <p className="text-xs text-slate-500 mt-0.5">เลือกพิกัดด้วยตัวเอง</p>
                </div>
                <ChevronRight className="w-5 h-5 text-slate-300" />
              </button>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">ที่บันทึกไว้</h3>
              <button className="flex items-center gap-4 border-b border-slate-100 p-4 w-full text-left bg-white">
                <div className="w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center shrink-0">
                  <Star className="w-5 h-5 text-amber-500" />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800 text-sm">บ้าน</h4>
                  <p className="text-xs text-slate-500 mt-0.5">บางนา, กรุงเทพฯ</p>
                </div>
              </button>
            </div>
          </div>

          {/* 1 - Style C: Immersive Gradient (New) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-purple-600">Style C: Immersive Gradient</h3>
            <div className="w-[375px] h-[812px] bg-gradient-to-br from-indigo-900 via-purple-900 to-slate-900 rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-xl flex flex-col pt-20 px-6">
              
              <div className="absolute top-0 right-0 w-64 h-64 bg-fuchsia-500/20 rounded-full blur-3xl mix-blend-screen"></div>
              
              <h1 className="text-3xl font-bold mb-6 text-white tracking-tight relative z-10">ค้นหาพื้นที่</h1>
              
              <div className="relative mb-6 z-10">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
                <input type="text" placeholder="พิมพ์ชื่อสถานที่..." className="w-full bg-white/10 border border-white/20 rounded-full py-4 pl-12 pr-4 text-white placeholder-white/50 focus:outline-none focus:bg-white/20 backdrop-blur-lg transition-all" />
              </div>

              <button className="flex items-center gap-4 bg-white/10 border border-white/20 rounded-3xl p-5 w-full mb-3 hover:bg-white/20 backdrop-blur-md transition-all z-10 group">
                <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center shrink-0 shadow-lg">
                  <Crosshair className="w-6 h-6 text-white" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="font-bold text-white text-base">ตำแหน่งปัจจุบัน</h3>
                  <p className="text-xs text-purple-200 mt-0.5 opacity-80">เปิดใช้งาน GPS</p>
                </div>
              </button>

              <button className="flex items-center gap-4 bg-black/20 border border-white/10 rounded-3xl p-5 w-full mb-8 hover:bg-black/30 backdrop-blur-md transition-all z-10">
                <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                  <Map className="w-5 h-5 text-white/80" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="font-semibold text-white/90 text-sm">แผนที่แบบโต้ตอบ</h3>
                  <p className="text-xs text-white/50 mt-0.5">ปักหมุดด้วยตัวเอง</p>
                </div>
              </button>

              <h3 className="text-xs font-medium text-white/40 uppercase tracking-widest mb-3 z-10 pl-2">สถานที่บันทึกไว้</h3>
              <button className="flex items-center gap-4 bg-transparent border-b border-white/10 pb-4 w-full text-left z-10">
                <div className="w-10 h-10 rounded-full bg-amber-500/20 flex items-center justify-center shrink-0 border border-amber-500/30">
                  <Star className="w-5 h-5 text-amber-300" />
                </div>
                <div>
                  <h4 className="font-medium text-white text-base">บ้าน</h4>
                  <p className="text-xs text-white/50 mt-0.5">บางนา, กรุงเทพฯ</p>
                </div>
              </button>
            </div>
          </div>

        </div>
      </div>


      {/* ======================= FLOW 1.5: INTERACTIVE MAP PICKER ======================= */}
      <div className="max-w-[1400px] w-full mb-20">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Step 1.5: Map Picker (เลื่อนแผนที่ปักหมุด)</h2>
        <div className="flex flex-wrap justify-center gap-10 mt-8">
          
          {/* 1.5 - Style A */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-blue-600">Style A: Glassmorphism</h3>
            <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-xl flex flex-col">
              <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url('https://api.maptiler.com/maps/streets-v2-dark/static/100.523,13.73,14/400x800.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
              
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center drop-shadow-2xl z-20 pointer-events-none">
                <div className="bg-blue-600 text-white text-xs font-bold px-3 py-1.5 rounded-lg mb-2 shadow-lg animate-bounce whitespace-nowrap">เลื่อนแผนที่เพื่อปักหมุด</div>
                <MapPin className="w-10 h-10 text-rose-500 drop-shadow-md" fill="white" />
                <div className="w-2 h-1 bg-black/30 rounded-full mt-1 blur-[1px]"></div>
              </div>

              <div className="relative z-10 p-5 pt-14 flex items-center justify-between">
                 <button className="w-10 h-10 rounded-full bg-slate-800/80 backdrop-blur flex items-center justify-center border border-slate-700 text-white">
                   <ChevronRight className="w-5 h-5 rotate-180" />
                 </button>
                 <div className="flex bg-slate-800/80 backdrop-blur rounded-full px-4 py-2 border border-slate-700 shadow-sm">
                   <Search className="w-4 h-4 text-slate-400 mr-2 mt-0.5" />
                   <span className="text-sm text-slate-200">สยามสแควร์</span>
                 </div>
              </div>

              <div className="mt-auto relative z-10 p-6 bg-slate-900/95 backdrop-blur-md rounded-t-3xl border-t border-slate-700 shadow-[0_-10px_20px_rgba(0,0,0,0.3)]">
                <div className="mb-4">
                  <h4 className="text-slate-400 text-xs uppercase tracking-wide mb-1">พิกัดที่เลือก</h4>
                  <p className="text-white font-medium text-lg">ปทุมวัน, กรุงเทพมหานคร</p>
                </div>
                <button className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-4 rounded-2xl flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(37,99,235,0.4)]">
                  <Check className="w-5 h-5" /> ยืนยันพิกัดนี้
                </button>
              </div>
            </div>
          </div>
          
          {/* 1.5 - Style B */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-emerald-600">Style B: Minimal (Light)</h3>
            <div className="w-[375px] h-[812px] bg-slate-200 rounded-[40px] border-[8px] border-slate-300 overflow-hidden relative shadow-xl flex flex-col">
              <div className="absolute inset-0 bg-cover bg-center" style={{ backgroundImage: "url('https://api.maptiler.com/maps/streets-v2-light/static/100.523,13.73,14/400x800.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
              
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center drop-shadow-xl z-20 pointer-events-none">
                <div className="bg-slate-900 text-white text-xs font-bold px-3 py-1.5 rounded-full mb-2 shadow-md animate-bounce whitespace-nowrap">เลื่อนเพื่อปักหมุด</div>
                <MapPin className="w-10 h-10 text-blue-600 drop-shadow-sm" fill="white" />
                <div className="w-2 h-1 bg-black/20 rounded-full mt-1 blur-[1px]"></div>
              </div>

              <div className="relative z-10 p-5 pt-14 flex items-center justify-between">
                 <button className="w-10 h-10 rounded-full bg-white flex items-center justify-center shadow-sm border border-slate-100 text-slate-600">
                   <ChevronRight className="w-5 h-5 rotate-180" />
                 </button>
                 <div className="flex bg-white rounded-full px-4 py-2 shadow-sm border border-slate-100">
                   <Search className="w-4 h-4 text-slate-400 mr-2 mt-0.5" />
                   <span className="text-sm text-slate-700 font-medium">สยามสแควร์</span>
                 </div>
              </div>

              <div className="mt-auto relative z-10 p-6 bg-white rounded-t-3xl shadow-[0_-10px_20px_rgba(0,0,0,0.05)] border-t border-slate-100">
                <div className="mb-4 text-center">
                  <p className="text-slate-800 font-bold text-lg">ปทุมวัน, กรุงเทพมหานคร</p>
                  <p className="text-slate-500 text-xs mt-1">13.746°N, 100.532°E</p>
                </div>
                <button className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2">
                  ยืนยันพิกัดนี้
                </button>
              </div>
            </div>
          </div>

          {/* 1.5 - Style C: Immersive Gradient */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-purple-600">Style C: Immersive Gradient</h3>
            <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-xl flex flex-col">
              {/* Map background but tinted */}
              <div className="absolute inset-0 bg-cover bg-center mix-blend-overlay opacity-50" style={{ backgroundImage: "url('https://api.maptiler.com/maps/streets-v2-dark/static/100.523,13.73,14/400x800.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/80 via-purple-900/80 to-slate-900/90 pointer-events-none" />
              
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center drop-shadow-2xl z-20 pointer-events-none">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center border-2 border-white/40 shadow-[0_0_20px_rgba(255,255,255,0.2)]">
                  <div className="w-4 h-4 bg-white rounded-full shadow-inner animate-pulse"></div>
                </div>
              </div>

              <div className="relative z-10 p-5 pt-14 flex items-center justify-between">
                 <button className="w-12 h-12 rounded-full bg-white/10 backdrop-blur-lg flex items-center justify-center border border-white/20 text-white shadow-lg">
                   <ChevronRight className="w-6 h-6 rotate-180" />
                 </button>
                 <div className="flex bg-white/10 backdrop-blur-lg rounded-full px-5 py-3 border border-white/20 shadow-lg flex-1 ml-4">
                   <Search className="w-5 h-5 text-white/60 mr-3" />
                   <span className="text-base text-white/90">ค้นหาพิกัด...</span>
                 </div>
              </div>

              <div className="mt-auto relative z-10 p-6 bg-white/10 backdrop-blur-xl rounded-t-[40px] border-t border-white/20 shadow-[0_-20px_40px_rgba(0,0,0,0.4)]">
                <div className="mb-6 text-center pt-2">
                  <h4 className="text-white/60 text-sm font-medium mb-1">พื้นที่ที่เลือก</h4>
                  <p className="text-white font-bold text-2xl tracking-tight">ปทุมวัน</p>
                  <p className="text-white/40 text-sm mt-1">กรุงเทพมหานคร</p>
                </div>
                <button className="w-full bg-white text-indigo-900 hover:bg-slate-100 font-bold py-5 rounded-full flex items-center justify-center gap-2 text-lg shadow-[0_10px_20px_rgba(255,255,255,0.2)] transition-transform active:scale-95">
                  <MapPin className="w-5 h-5" /> ตกลง
                </button>
              </div>
            </div>
          </div>
          
        </div>
      </div>


      {/* ======================= FLOW 2: MAIN RADAR NOWCAST (HYBRID) ======================= */}
      <div className="max-w-[1400px] w-full">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Step 2: Main Radar Nowcast (Hybrid Overlay + Dashboard)</h2>
        <p className="text-slate-500 mb-8">ซ้อนภาพ Vector ทับ Raw Static Image พร้อมแสดง 6 Frames, Radar Latest, และ Timeline BarChart</p>
        
        <div className="flex flex-wrap justify-center gap-10">
          
          {/* 2 - Style A: HYBRID (Glassmorphism) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-blue-600">Style A: Glassmorphism</h3>
            <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-2xl flex flex-col">
              <div className="h-[55%] relative bg-slate-800 w-full overflow-hidden">
                <div className="absolute inset-0 bg-cover bg-center opacity-30" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                
                {/* RADAR LATEST BADGE */}
                <div className="absolute top-6 left-4 bg-slate-900/80 backdrop-blur-md rounded-lg px-3 py-1.5 border border-slate-700/50 flex flex-col z-20 shadow-md">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">TMD Radar Latest</span>
                  <span className="text-sm font-mono text-white flex items-center gap-1.5">
                     <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
                     14:20 น. (Now)
                  </span>
                </div>

                <button className="absolute top-6 right-4 bg-emerald-900/80 backdrop-blur-md rounded-full p-2.5 border border-emerald-500/50 shadow-lg text-emerald-400 z-20">
                  <Layers className="w-4 h-4" />
                </button>

                {/* RAW IMAGE */}
                <div className="absolute inset-0 flex items-center justify-center mix-blend-screen opacity-60 z-0">
                   <div className="w-48 h-48 relative -mt-10 -ml-10">
                     <div className="absolute w-full h-full" style={{ backgroundImage: 'radial-gradient(circle, #f00 0%, #ff0 30%, #0f0 60%, transparent 100%)', filter: 'url(#pixelate) blur(1px)', clipPath: 'circle(40% at 30% 30%)' }}></div>
                   </div>
                </div>

                {/* VECTOR */}
                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10">
                  <div className="absolute inset-0 rounded-full border-2 border-amber-400 bg-amber-500/10"></div>
                  <div className="absolute top-1/4 left-1/4 w-16 h-16 rounded-full border-2 border-rose-400 bg-rose-500/10"></div>
                  <svg className="absolute top-1/2 left-1/2 w-48 h-48 overflow-visible" style={{ transform: 'translate(-10px, -10px)' }}>
                     <path d="M 0 0 L 100 -50 L 150 -70" fill="none" stroke="#3b82f6" strokeWidth="3" strokeDasharray="6 4" strokeLinecap="round" />
                  </svg>
                </div>
                
                <div className="absolute top-1/4 right-1/4 flex flex-col items-center z-20">
                  <MapPin className="w-7 h-7 text-white drop-shadow-md" fill="#3b82f6" />
                </div>
              </div>

              {/* BOTTOM SHEET DATA */}
              <div className="flex-1 bg-slate-900 p-5 rounded-t-3xl -mt-6 relative z-30 border-t border-slate-700/50 shadow-[0_-10px_20px_rgba(0,0,0,0.3)] flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-rose-500 shadow-[0_0_10px_#f43f5e]"></div>
                    <h3 className="font-semibold text-lg text-white">ฝนหนักกำลังมา</h3>
                  </div>
                  <span className="text-rose-400 font-mono font-medium bg-rose-500/10 px-2 py-1 rounded border border-rose-500/20 text-xs">ETA: 20m</span>
                </div>

                {/* Timeline BarChart */}
                <div className="w-full mb-5">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Intensity (Next 2 hrs)</span>
                  </div>
                  <div className="h-12 flex items-end gap-1.5 w-full border-b border-slate-800 pb-1">
                    <div className="flex-1 bg-slate-800 rounded-t h-[10%]"></div>
                    <div className="flex-1 bg-blue-500/40 rounded-t h-[30%]"></div>
                    <div className="w-px h-full bg-rose-500/50 mx-1 relative"><span className="absolute -top-4 -left-3 text-[9px] font-mono text-rose-400">NOW</span></div>
                    <div className="flex-1 bg-blue-500 rounded-t h-[50%]"></div>
                    <div className="flex-1 bg-amber-400 rounded-t h-[80%]"></div>
                    <div className="flex-1 bg-rose-500 rounded-t h-[95%] shadow-[0_0_8px_#e11d48]"></div>
                    <div className="flex-1 bg-amber-400 rounded-t h-[60%]"></div>
                    <div className="flex-1 bg-slate-800 rounded-t h-[15%]"></div>
                  </div>
                </div>

                {/* 6 Frames Playback */}
                <div className="bg-slate-800/80 backdrop-blur-md rounded-2xl p-4 border border-slate-700/50 flex flex-col gap-3 mt-auto">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-semibold text-slate-300">ภาพย้อนหลัง (Past 6 Frames)</span>
                    <span className="text-xs font-mono text-blue-400">-10 นาที</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <button className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center shrink-0 hover:bg-blue-500 transition shadow-sm">
                      <Play className="w-4 h-4 text-white ml-0.5" />
                    </button>
                    <div className="flex-1 h-1.5 bg-slate-700 rounded-full relative">
                      <div className="absolute left-0 top-0 bottom-0 w-[80%] bg-blue-500 rounded-full"></div>
                      <div className="absolute left-[80%] top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 bg-white rounded-full shadow border-2 border-blue-500"></div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>

          {/* 2 - Style B: HYBRID (Minimal Light) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-emerald-600">Style B: Minimal (Light)</h3>
            <div className="w-[375px] h-[812px] bg-slate-100 rounded-[40px] border-[8px] border-slate-200 overflow-hidden relative shadow-2xl flex flex-col">
              <div className="h-[55%] relative bg-slate-200 w-full overflow-hidden">
                <div className="absolute inset-0 bg-cover bg-center opacity-70" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-light/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                
                {/* RADAR LATEST BADGE */}
                <div className="absolute top-6 left-4 bg-white shadow-sm rounded-lg px-3 py-1.5 border border-slate-200 flex flex-col z-20">
                  <span className="text-[9px] text-slate-400 font-bold uppercase">Radar Latest</span>
                  <span className="text-sm font-semibold text-slate-700">14:20 น.</span>
                </div>

                <button className="absolute top-6 right-4 bg-emerald-50 rounded-full p-2.5 border border-emerald-200 shadow-sm text-emerald-600 z-20">
                  <Layers className="w-4 h-4" />
                </button>

                {/* RAW IMAGE */}
                <div className="absolute inset-0 flex items-center justify-center opacity-50 mix-blend-multiply z-0">
                   <div className="w-48 h-48 relative -mt-10 -ml-10">
                     <div className="absolute w-full h-full" style={{ backgroundImage: 'radial-gradient(circle, #f00 0%, #f90 30%, #0f0 60%, transparent 100%)', filter: 'url(#pixelate) blur(1px)', clipPath: 'circle(40% at 30% 30%)' }}></div>
                   </div>
                </div>

                {/* VECTOR */}
                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10">
                  <div className="absolute inset-0 rounded-full border-2 border-orange-400 bg-transparent"></div>
                  <div className="absolute top-1/4 left-1/4 w-16 h-16 rounded-full border-2 border-red-500 bg-transparent"></div>
                  <svg className="absolute top-1/2 left-1/2 w-48 h-48 overflow-visible" style={{ transform: 'translate(-10px, -10px)' }}>
                     <path d="M 0 0 L 100 -50 L 150 -70" fill="none" stroke="#2563eb" strokeWidth="3" strokeDasharray="6 4" strokeLinecap="round" />
                  </svg>
                </div>
                
                <div className="absolute top-1/4 right-1/4 flex flex-col items-center z-20">
                  <MapPin className="w-7 h-7 text-blue-600 drop-shadow-sm" fill="white" />
                </div>
              </div>

              {/* BOTTOM SHEET DATA */}
              <div className="flex-1 bg-white p-6 rounded-t-3xl -mt-6 relative z-30 shadow-[0_-10px_20px_rgba(0,0,0,0.05)] flex flex-col border-t border-slate-100">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-bold text-xl text-slate-900">ฝนหนักกำลังมา</h3>
                  <span className="text-red-600 font-bold bg-red-50 px-2 py-1 rounded-lg text-sm">ใน 20 นาที</span>
                </div>
                <p className="text-slate-500 text-sm mb-5">ระดับ 45+ dBZ, ต่อเนื่อง 1 ชั่วโมง</p>

                {/* Timeline BarChart */}
                <div className="w-full mb-6">
                  <div className="h-10 flex items-end gap-1.5 w-full border-b-2 border-slate-100 pb-1">
                    <div className="flex-1 bg-slate-100 rounded-t h-[20%]"></div>
                    <div className="flex-1 bg-blue-200 rounded-t h-[30%]"></div>
                    <div className="w-0.5 h-full bg-slate-300 mx-1"></div>
                    <div className="flex-1 bg-blue-500 rounded-t h-[50%]"></div>
                    <div className="flex-1 bg-orange-400 rounded-t h-[80%]"></div>
                    <div className="flex-1 bg-red-500 rounded-t h-[95%] shadow-sm"></div>
                    <div className="flex-1 bg-orange-400 rounded-t h-[60%]"></div>
                    <div className="flex-1 bg-slate-100 rounded-t h-[15%]"></div>
                  </div>
                  <div className="flex justify-between text-[10px] font-semibold text-slate-400 mt-1 uppercase">
                    <span>Now</span>
                    <span>1 Hr</span>
                    <span>2 Hr</span>
                  </div>
                </div>

                {/* 6 Frames Playback */}
                <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100 flex flex-col gap-3 mt-auto">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-slate-700">ภาพย้อนหลัง 6 เฟรม</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <button className="w-10 h-10 rounded-full bg-slate-900 flex items-center justify-center shrink-0 hover:bg-slate-800 transition shadow-sm">
                      <Play className="w-4 h-4 text-white ml-0.5" />
                    </button>
                    <div className="flex-1 h-1.5 bg-slate-200 rounded-full relative">
                      <div className="absolute left-0 top-0 bottom-0 w-[80%] bg-blue-600 rounded-full"></div>
                      <div className="absolute left-[80%] top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 bg-white rounded-full shadow border border-slate-200"></div>
                    </div>
                    <span className="text-xs font-bold text-slate-500 w-12 text-right">-10m</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 2 - Style C: HYBRID (Immersive Gradient) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-purple-600">Style C: Immersive Gradient</h3>
            <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-2xl flex flex-col">
              
              <div className="h-[60%] relative bg-gradient-to-b from-indigo-900 to-purple-900 w-full overflow-hidden">
                <div className="absolute inset-0 bg-cover bg-center mix-blend-overlay opacity-40" style={{ backgroundImage: "url('https://api.maptiler.com/maps/streets-v2-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                
                {/* RADAR LATEST BADGE */}
                <div className="absolute top-12 left-0 w-full flex justify-center z-20 pointer-events-none">
                  <div className="bg-black/20 backdrop-blur-xl rounded-full px-4 py-2 border border-white/10 flex items-center gap-2 shadow-lg">
                    <Activity className="w-4 h-4 text-white/70" />
                    <span className="text-xs font-medium text-white/90">Radar Update: 14:20 น.</span>
                  </div>
                </div>

                <button className="absolute top-12 right-4 bg-white/10 backdrop-blur-md rounded-full p-2.5 border border-white/20 shadow-lg text-white z-20">
                  <Layers className="w-4 h-4" />
                </button>

                {/* RAW IMAGE */}
                <div className="absolute inset-0 flex items-center justify-center opacity-70 mix-blend-plus-lighter z-0">
                   <div className="w-48 h-48 relative -mt-10 -ml-10">
                     <div className="absolute w-full h-full" style={{ backgroundImage: 'radial-gradient(circle, #f0f 0%, #0ff 40%, transparent 80%)', filter: 'url(#pixelate) blur(4px)', clipPath: 'circle(40% at 30% 30%)' }}></div>
                   </div>
                </div>

                {/* VECTOR */}
                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10">
                  <div className="absolute inset-0 rounded-full border border-white/40 bg-white/5 shadow-[inset_0_0_20px_rgba(255,255,255,0.1)]"></div>
                  <svg className="absolute top-1/2 left-1/2 w-48 h-48 overflow-visible" style={{ transform: 'translate(-10px, -10px)' }}>
                     <path d="M 0 0 L 100 -50 L 150 -70" fill="none" stroke="rgba(255,255,255,0.8)" strokeWidth="3" strokeDasharray="10 5" strokeLinecap="round" />
                  </svg>
                </div>
                
                <div className="absolute top-1/4 right-1/4 flex flex-col items-center z-20">
                  <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center border border-white/40 shadow-lg">
                    <div className="w-3 h-3 bg-white rounded-full shadow-inner"></div>
                  </div>
                </div>
              </div>

              {/* BOTTOM SHEET DATA */}
              <div className="flex-1 bg-black/40 backdrop-blur-2xl p-6 rounded-t-[40px] -mt-10 relative z-30 border-t border-white/10 shadow-[0_-20px_40px_rgba(0,0,0,0.5)] flex flex-col">
                <div className="flex flex-col items-center mb-6">
                  <h3 className="font-bold text-3xl text-white tracking-tight mb-1">ฝนตกหนัก</h3>
                  <p className="text-white/60 text-base font-medium">จะถึงตำแหน่งคุณใน 20 นาที</p>
                </div>

                {/* Timeline BarChart */}
                <div className="w-full mb-6">
                  <div className="h-12 flex items-end gap-1.5 w-full pb-1">
                    <div className="flex-1 bg-white/10 rounded-full h-[20%]"></div>
                    <div className="flex-1 bg-white/30 rounded-full h-[30%]"></div>
                    <div className="w-0.5 h-full bg-white/50 mx-1 rounded-full relative"></div>
                    <div className="flex-1 bg-blue-400 rounded-full h-[50%]"></div>
                    <div className="flex-1 bg-fuchsia-400 rounded-full h-[80%] shadow-[0_0_15px_rgba(232,121,249,0.5)]"></div>
                    <div className="flex-1 bg-fuchsia-500 rounded-full h-[95%] shadow-[0_0_20px_rgba(217,70,239,0.8)]"></div>
                    <div className="flex-1 bg-blue-400 rounded-full h-[60%]"></div>
                    <div className="flex-1 bg-white/10 rounded-full h-[15%]"></div>
                  </div>
                </div>

                {/* 6 Frames Playback */}
                <div className="bg-white/5 backdrop-blur-lg rounded-3xl p-5 border border-white/10 flex flex-col gap-4 mt-auto shadow-inner">
                  <div className="flex items-center gap-4">
                    <button className="w-12 h-12 rounded-full bg-white text-indigo-900 flex items-center justify-center shrink-0 shadow-lg hover:scale-105 transition-transform">
                      <Play className="w-5 h-5 ml-1" />
                    </button>
                    <div className="flex-1 flex flex-col gap-2">
                      <div className="flex justify-between items-center px-1">
                        <span className="text-xs font-medium text-white/70">6 Frames History</span>
                        <span className="text-xs font-bold text-white">-10m</span>
                      </div>
                      <div className="w-full h-1.5 bg-white/10 rounded-full relative">
                        <div className="absolute left-0 top-0 bottom-0 w-[80%] bg-white rounded-full shadow-[0_0_10px_rgba(255,255,255,0.5)]"></div>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}
