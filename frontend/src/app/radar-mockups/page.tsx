'use client';

import React, { useState, useEffect } from 'react';
import { MapPin, CloudRain, Clock, Wind, AlertCircle, Droplets, Sun, Navigation, Play, Pause, ChevronRight, Activity, BarChart2, Search, Crosshair, Star, Map, Layers, Check, Target, Bug, SplitSquareVertical } from 'lucide-react';

export default function RadarMockupsPage() {
  // Animation State for 6 Frames Playback
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(4); // Default to -5m
  const times = ['-25m', '-20m', '-15m', '-10m', '-5m', 'NOW'];
  const progressPercent = (frameIndex / 5) * 100;

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(() => {
        setFrameIndex((prev) => (prev + 1) % 6);
      }, 1000); // 1 frame per second
    }
    return () => clearInterval(interval);
  }, [isPlaying]);

  // Bottom Sheet Snap Points State (Demonstrated on Style A & B)
  const [snapState, setSnapState] = useState<'collapsed' | 'half' | 'expanded'>('expanded');

  const toggleSnap = () => {
    if (snapState === 'collapsed') setSnapState('half');
    else if (snapState === 'half') setSnapState('expanded');
    else setSnapState('collapsed');
  };

  const getBottomSheetHeight = () => {
    if (snapState === 'collapsed') return '90px'; // Only Headline
    if (snapState === 'half') return '220px'; // Headline + Timeline
    return '360px'; // Headline + Timeline + Slider
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8 flex flex-col items-center font-sans pb-32">
      <div className="max-w-7xl w-full text-center mb-12">
        <h1 className="text-3xl font-semibold mb-3 text-slate-900">Mobile UI Flow & Style Variants</h1>
        <p className="text-slate-500">เปรียบเทียบ 4 สไตล์: A (Glass), B (Minimal Light), C (Material 3 Pastel), D (Warm Dark / Earth)</p>
        <div className="mt-4 inline-flex items-center gap-4 bg-white px-6 py-3 rounded-full shadow-sm border border-slate-200">
           <span className="text-sm font-medium text-slate-600">Global Controls:</span>
           <button 
             onClick={() => setIsPlaying(!isPlaying)}
             className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-sm font-bold transition-colors ${isPlaying ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}
           >
             {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
             {isPlaying ? 'Pause Animation' : 'Play Animation'}
           </button>
           <button 
             onClick={toggleSnap}
             className="flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-100 text-slate-700 text-sm font-bold hover:bg-slate-200 transition-colors"
           >
             Toggle Bottom Sheet Snap: {snapState.toUpperCase()}
           </button>
        </div>
      </div>

      {/* ======================= FLOW 1: LOCATION SETUP ======================= */}
      <div className="max-w-[1400px] w-full mb-24">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Step 1: Location Setup</h2>
        <div className="flex flex-wrap justify-center gap-10 mt-8">
          
          {/* 1 - Style A: Glassmorphism */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-blue-600">Style A: Glassmorphism</h3>
            <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-xl flex flex-col">
              <div className="absolute inset-0 bg-cover bg-center opacity-30 blur-md grayscale" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
              <div className="absolute inset-0 bg-slate-950/60" />
              <div className="relative z-10 w-full h-full flex flex-col pt-20 px-6">
                <h1 className="text-3xl font-semibold mb-8 text-white text-center">ค้นหาพิกัด</h1>
                
                {/* SEARCH INPUT (Increased Visual Weight) */}
                <div className="relative mb-3 shadow-[0_0_20px_rgba(59,130,246,0.15)]">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-300" />
                  <input type="text" placeholder="พิมพ์ชื่อเขต, จังหวัด..." className="w-full bg-slate-800/90 border-2 border-blue-500/40 rounded-2xl py-4 pl-12 pr-4 text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 backdrop-blur-md font-medium" />
                </div>

                {/* CURRENT LOCATION (Decreased Visual Weight to Text Button) */}
                <button className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-blue-400 hover:text-blue-300 hover:bg-blue-500/10 transition-colors mb-6 mx-auto">
                  <Crosshair className="w-4 h-4" />
                  <span className="text-sm font-semibold">ใช้ตำแหน่งปัจจุบัน (GPS)</span>
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
              <h1 className="text-3xl font-bold mb-8 text-slate-900 text-center">ค้นหาพิกัด</h1>
              
              {/* SEARCH INPUT */}
              <div className="relative mb-3 shadow-md">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-blue-600" />
                <input type="text" placeholder="ค้นหาเขต, จังหวัด..." className="w-full bg-white border-2 border-slate-200 rounded-xl py-4 pl-12 pr-4 text-slate-900 placeholder-slate-400 focus:outline-none focus:border-blue-500 shadow-sm font-medium" />
              </div>

              {/* CURRENT LOCATION (Text Button) */}
              <button className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-blue-600 hover:bg-blue-50 transition-colors mb-6 mx-auto">
                <Navigation className="w-4 h-4" />
                <span className="text-sm font-bold">ใช้ตำแหน่งปัจจุบัน (GPS)</span>
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

              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 px-2">ที่บันทึกไว้</h3>
              <button className="flex items-center gap-4 p-4 w-full text-left bg-slate-50 rounded-xl border border-slate-100">
                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center shrink-0">
                  <Star className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <h4 className="font-semibold text-slate-800 text-sm">บ้าน</h4>
                  <p className="text-xs text-slate-500 mt-0.5">บางนา, กรุงเทพฯ</p>
                </div>
              </button>
            </div>
          </div>

          {/* 1 - Style C: Material You / Pastel */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-orange-600">Style C: Material 3 (Pastel)</h3>
            <div className="w-[375px] h-[812px] bg-orange-50/50 rounded-[40px] border-[8px] border-slate-200 overflow-hidden relative shadow-xl flex flex-col pt-20 px-6">
              <h1 className="text-4xl font-medium mb-8 text-stone-900 tracking-tight">คุณอยู่ที่ไหน?</h1>
              
              {/* SEARCH INPUT */}
              <div className="relative mb-3">
                <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-stone-700" />
                <input type="text" placeholder="พิมพ์ชื่อสถานที่..." className="w-full bg-orange-100/70 border-none rounded-full py-5 pl-14 pr-6 text-stone-900 placeholder-stone-500 focus:outline-none focus:bg-orange-100 font-medium text-lg transition-colors" />
              </div>

              {/* CURRENT LOCATION */}
              <button className="flex items-center justify-center gap-2 py-3 px-4 rounded-full text-orange-700 hover:bg-orange-100 transition-colors mb-6 mx-auto">
                <Crosshair className="w-5 h-5" />
                <span className="text-sm font-medium">ใช้ตำแหน่งปัจจุบัน</span>
              </button>

              <button className="flex items-center gap-5 bg-stone-100/80 rounded-[28px] p-5 w-full mb-8 hover:bg-stone-200/80 transition-colors">
                <div className="w-12 h-12 rounded-full bg-orange-200 flex items-center justify-center shrink-0 text-orange-800">
                  <Map className="w-6 h-6" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="font-medium text-stone-900 text-base">ปักหมุดบนแผนที่</h3>
                  <p className="text-sm text-stone-500 mt-0.5">ระบุจุดด้วยตัวเอง</p>
                </div>
              </button>

              <h3 className="text-sm font-medium text-stone-500 mb-3 ml-2">บันทึกไว้</h3>
              <button className="flex items-center gap-5 bg-stone-100/50 rounded-[28px] p-5 w-full text-left">
                <div className="w-12 h-12 rounded-full bg-stone-200 flex items-center justify-center shrink-0">
                  <Star className="w-6 h-6 text-stone-600" />
                </div>
                <div>
                  <h4 className="font-medium text-stone-900 text-base">บ้าน</h4>
                  <p className="text-sm text-stone-500 mt-0.5">บางนา, กรุงเทพฯ</p>
                </div>
              </button>
            </div>
          </div>

          {/* 1 - Style D: Meteorological Dark */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-slate-400">Style D: Meteorological Dark</h3>
            <div className="w-[375px] h-[812px] rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-xl flex flex-col pt-20 px-6 bg-[#13171f]">

              <h1 className="text-3xl font-medium mb-8 text-white tracking-tight relative z-10">ค้นหาพิกัด</h1>
              
              <div className="relative mb-3 z-10">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input type="text" placeholder="พิมพ์ชื่อสถานที่..."
                  className="w-full border border-slate-700 rounded-2xl py-4 pl-12 pr-5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 bg-slate-800/40" />
              </div>

              {/* CURRENT LOCATION (Prominent) */}
              <button className="flex items-center justify-center gap-2 py-4 px-4 rounded-2xl bg-blue-600 text-white hover:bg-blue-500 transition-colors mb-6 mx-auto w-full z-10 font-semibold shadow-lg shadow-blue-900/20">
                <Crosshair className="w-5 h-5" />
                <span>ใช้ตำแหน่งปัจจุบัน (GPS)</span>
              </button>

              <button className="flex items-center gap-4 rounded-2xl p-4 w-full mb-8 z-10 transition-colors hover:bg-slate-800/80 bg-slate-800/30 border border-slate-700">
                <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-slate-800 border border-slate-700">
                  <Map className="w-5 h-5 text-blue-400" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="font-medium text-slate-200 text-sm">ปักหมุดบนแผนที่</h3>
                  <p className="text-xs text-slate-500 mt-0.5">เลือกพิกัดด้วยตัวเอง</p>
                </div>
                <ChevronRight className="w-5 h-5 text-slate-600" />
              </button>

              <h3 className="text-xs font-medium text-slate-500 uppercase tracking-widest mb-3 z-10">บันทึกไว้</h3>
              <button className="flex items-center gap-4 rounded-2xl p-4 w-full text-left z-10 bg-slate-800/30 border border-slate-700">
                <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-slate-800 border border-slate-700">
                  <Star className="w-5 h-5 text-amber-500" />
                </div>
                <div>
                  <h4 className="font-medium text-slate-200 text-sm">บ้าน</h4>
                  <p className="text-xs text-slate-500 mt-0.5">บางนา, กรุงเทพฯ</p>
                </div>
              </button>
            </div>
          </div>

          {/* 1 - Style E: Dynamic Weather (Clear Sky) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-sky-500">Style E: Dynamic (Clear Sky)</h3>
            <div className="w-[375px] h-[812px] rounded-[40px] border-[8px] border-slate-200 overflow-hidden relative shadow-xl flex flex-col pt-20 px-6 bg-gradient-to-b from-sky-100 to-white">

              <h1 className="text-3xl font-semibold mb-8 text-sky-900 tracking-tight relative z-10">ค้นหาพิกัด</h1>
              
              <div className="relative mb-3 z-10">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-sky-600" />
                <input type="text" placeholder="พิมพ์ชื่อสถานที่..."
                  className="w-full border-0 rounded-2xl py-4 pl-12 pr-5 text-sky-900 placeholder-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-300 bg-white shadow-sm" />
              </div>

              {/* CURRENT LOCATION (Prominent) */}
              <button className="flex items-center justify-center gap-2 py-4 px-4 rounded-2xl bg-sky-500 text-white hover:bg-sky-400 transition-colors mb-6 mx-auto w-full z-10 font-semibold shadow-md shadow-sky-200">
                <Crosshair className="w-5 h-5" />
                <span>ใช้ตำแหน่งปัจจุบัน (GPS)</span>
              </button>

              <button className="flex items-center gap-4 rounded-2xl p-4 w-full mb-8 z-10 transition-colors hover:bg-sky-50 bg-white/80 border border-sky-100 shadow-sm">
                <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-sky-100">
                  <Map className="w-5 h-5 text-sky-600" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="font-semibold text-sky-900 text-sm">ปักหมุดบนแผนที่</h3>
                  <p className="text-xs text-sky-500 mt-0.5">เลือกพิกัดด้วยตัวเอง</p>
                </div>
                <ChevronRight className="w-5 h-5 text-sky-300" />
              </button>

              <h3 className="text-xs font-bold text-sky-400 uppercase tracking-widest mb-3 z-10">บันทึกไว้</h3>
              <button className="flex items-center gap-4 rounded-2xl p-4 w-full text-left z-10 bg-white/80 border border-sky-100 shadow-sm">
                <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-amber-50">
                  <Star className="w-5 h-5 text-amber-500" />
                </div>
                <div>
                  <h4 className="font-semibold text-sky-900 text-sm">บ้าน</h4>
                  <p className="text-xs text-sky-500 mt-0.5">บางนา, กรุงเทพฯ</p>
                </div>
              </button>
            </div>
          </div>

          {/* 1 - Style F: Dynamic Weather (Storm Alert) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-red-600">Style F: Dynamic (Storm Alert)</h3>
            <div className="w-[375px] h-[812px] rounded-[40px] border-[8px] border-slate-900 overflow-hidden relative shadow-xl flex flex-col pt-20 px-6 bg-[#211616]">

              <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-b from-red-900/40 to-transparent"></div>

              <h1 className="text-3xl font-semibold mb-8 text-rose-50 tracking-tight relative z-10">ค้นหาพิกัด</h1>
              
              <div className="relative mb-3 z-10">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-rose-400" />
                <input type="text" placeholder="พิมพ์ชื่อสถานที่..."
                  className="w-full border border-rose-900/50 rounded-2xl py-4 pl-12 pr-5 text-rose-100 placeholder-rose-500/50 focus:outline-none focus:border-rose-500 bg-rose-950/20" />
              </div>

              {/* CURRENT LOCATION (Prominent) */}
              <button className="flex items-center justify-center gap-2 py-4 px-4 rounded-2xl bg-rose-600 text-white hover:bg-rose-500 transition-colors mb-6 mx-auto w-full z-10 font-semibold shadow-lg shadow-rose-900/20">
                <Crosshair className="w-5 h-5" />
                <span>ใช้ตำแหน่งปัจจุบัน (GPS)</span>
              </button>

              <button className="flex items-center gap-4 rounded-2xl p-4 w-full mb-8 z-10 transition-colors hover:bg-rose-950/50 bg-rose-950/30 border border-rose-900/50">
                <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-rose-900/40 text-rose-400">
                  <Map className="w-5 h-5" />
                </div>
                <div className="text-left flex-1">
                  <h3 className="font-medium text-rose-100 text-sm">ปักหมุดบนแผนที่</h3>
                  <p className="text-xs text-rose-400/70 mt-0.5">เลือกพิกัดด้วยตัวเอง</p>
                </div>
                <ChevronRight className="w-5 h-5 text-rose-700" />
              </button>

              <h3 className="text-xs font-medium text-rose-500/70 uppercase tracking-widest mb-3 z-10">บันทึกไว้</h3>
              <button className="flex items-center gap-4 rounded-2xl p-4 w-full text-left z-10 bg-rose-950/30 border border-rose-900/50">
                <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 bg-rose-900/40">
                  <Star className="w-5 h-5 text-amber-500" />
                </div>
                <div>
                  <h4 className="font-medium text-rose-100 text-sm">บ้าน</h4>
                  <p className="text-xs text-rose-400/70 mt-0.5">บางนา, กรุงเทพฯ</p>
                </div>
              </button>
            </div>
          </div>

        </div>
      </div>

      {/* ======================= FLOW 2: MAIN RADAR NOWCAST (HYBRID) ======================= */}
      <div className="max-w-[1400px] w-full mb-24">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Step 2: Main Radar Nowcast (Hybrid Overlay + Dashboard)</h2>
        <p className="text-slate-500 mb-8">ซ้อนภาพ Vector ทับ Raw Static Image พร้อมแสดง 6 Frames Animation และ Timeline BarChart แบบแบ่งสัดส่วนที่ชัดเจนขึ้น</p>
        
        <div className="flex flex-wrap justify-center gap-10">
          
          {/* 2 - Style A: HYBRID (Glassmorphism) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-blue-600">Style A: Glassmorphism</h3>
            <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-2xl flex flex-col">
              
              {/* MAP AREA */}
              <div className="relative bg-slate-800 w-full overflow-hidden transition-all duration-300 ease-in-out" style={{ height: `calc(100% - ${getBottomSheetHeight()})` }}>
                <div className="absolute inset-0 bg-cover bg-center opacity-30" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                
                {/* RADAR LATEST BADGE */}
                <div className="absolute top-6 left-4 bg-slate-900/80 backdrop-blur-md rounded-lg px-3 py-1.5 border border-slate-700/50 flex flex-col z-20 shadow-md">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">TMD Radar Latest</span>
                  <span className="text-sm font-mono text-white flex items-center gap-1.5">
                     <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse"></span>
                     14:20 น.
                  </span>
                </div>

                <button className="absolute top-6 right-4 bg-emerald-900/80 backdrop-blur-md rounded-full p-2.5 border border-emerald-500/50 shadow-lg text-emerald-400 z-20">
                  <Layers className="w-4 h-4" />
                </button>

                {/* RAW IMAGE */}
                <div className="absolute inset-0 flex items-center justify-center mix-blend-screen opacity-60 z-0">
                   <div className="w-48 h-48 relative -mt-10 -ml-10">
                     <div className="absolute w-full h-full transition-transform duration-500" style={{ backgroundImage: 'radial-gradient(circle, #f00 0%, #ff0 30%, #0f0 60%, transparent 100%)', filter: 'url(#pixelate) blur(1px)', clipPath: 'circle(40% at 30% 30%)', transform: `scale(${1 + frameIndex * 0.02})` }}></div>
                   </div>
                </div>

                {/* VECTOR */}
                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10 transition-transform duration-500" style={{ transform: `scale(${1 + frameIndex * 0.05})` }}>
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

              {/* BOTTOM SHEET DATA (WITH SNAP POINTS) */}
              <div 
                className="bg-slate-900 rounded-t-3xl relative z-30 border-t border-slate-700/50 shadow-[0_-15px_30px_rgba(0,0,0,0.4)] flex flex-col transition-all duration-300 ease-in-out" 
                style={{ height: getBottomSheetHeight() }}
              >
                {/* Drag Handle Indicator */}
                <div className="w-full pt-3 pb-2 flex justify-center cursor-pointer" onClick={toggleSnap}>
                  <div className="w-12 h-1.5 bg-slate-700 rounded-full"></div>
                </div>

                <div className="px-6 flex flex-col h-full overflow-hidden">
                  
                  {/* SNAP 1: Collapsed (Headline) */}
                  <div className="flex items-center justify-between mb-8 shrink-0">
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full bg-rose-500 shadow-[0_0_12px_#f43f5e] animate-pulse"></div>
                      <h3 className="font-semibold text-xl text-white">ฝนหนักกำลังมา</h3>
                    </div>
                    <span className="text-rose-400 font-mono font-medium bg-rose-500/10 px-3 py-1.5 rounded-lg border border-rose-500/20 text-sm">ETA: 20m</span>
                  </div>

                  {/* SNAP 2: Half (Timeline BarChart) */}
                  <div className="w-full mb-8 shrink-0 opacity-100 transition-opacity duration-300">
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-[11px] text-slate-400 font-medium uppercase tracking-widest">Intensity (Next 2 hrs)</span>
                    </div>
                    {/* Fixed Typography and Layout: Added gap-1, removed rounded-t slightly for a real chart look */}
                    <div className="h-16 flex items-end gap-1 w-full border-b border-slate-800 pb-2 relative">
                      <div className="flex-1 bg-slate-800 rounded-sm h-[10%]"></div>
                      <div className="flex-1 bg-blue-500/40 rounded-sm h-[30%]"></div>
                      
                      {/* NOW Indicator Line */}
                      <div className="absolute bottom-0 left-[25%] top-[-10px] w-px bg-rose-500/80 z-10">
                         <span className="absolute -top-4 -translate-x-1/2 text-[10px] font-bold text-rose-400 bg-slate-900 px-1">NOW</span>
                      </div>
                      
                      <div className="flex-1 bg-blue-500 rounded-sm h-[50%]"></div>
                      <div className="flex-1 bg-amber-400 rounded-sm h-[80%]"></div>
                      <div className="flex-1 bg-rose-500 rounded-sm h-[95%] shadow-[0_0_12px_#e11d48]"></div>
                      <div className="flex-1 bg-amber-400 rounded-sm h-[60%]"></div>
                      <div className="flex-1 bg-blue-500/40 rounded-sm h-[20%]"></div>
                      <div className="flex-1 bg-slate-800 rounded-sm h-[15%]"></div>
                    </div>
                  </div>

                  {/* SNAP 3: Expanded (6 Frames Playback) */}
                  <div className="bg-slate-800/60 rounded-2xl p-5 border border-slate-700/50 flex flex-col gap-4 mt-auto shrink-0 mb-6">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-semibold text-slate-300">ภาพย้อนหลัง (Past 6 Frames)</span>
                      <span className="text-sm font-mono font-bold text-blue-400 w-12 text-right">{times[frameIndex]}</span>
                    </div>
                    
                    {/* Fixed Layout: Smaller play button, thicker line */}
                    <div className="flex items-center gap-5">
                      <button 
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition shadow-md border ${isPlaying ? 'bg-amber-500 border-amber-400' : 'bg-blue-600 border-blue-500 hover:bg-blue-500'}`}
                      >
                        {isPlaying ? <Pause className="w-4 h-4 text-white" /> : <Play className="w-4 h-4 text-white ml-0.5" />}
                      </button>
                      
                      <div className="flex-1 h-2.5 bg-slate-900 rounded-full relative border border-slate-700/50 shadow-inner">
                        <div 
                          className="absolute left-0 top-0 bottom-0 bg-blue-500 rounded-full transition-all duration-300 ease-linear shadow-[0_0_8px_rgba(59,130,246,0.6)]"
                          style={{ width: `${progressPercent}%` }}
                        ></div>
                        <div 
                          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 bg-white rounded-full shadow-md border-2 border-blue-500 transition-all duration-300 ease-linear"
                          style={{ left: `${progressPercent}%` }}
                        ></div>
                      </div>
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
              
              <div className="relative bg-slate-200 w-full overflow-hidden transition-all duration-300 ease-in-out" style={{ height: `calc(100% - ${getBottomSheetHeight()})` }}>
                <div className="absolute inset-0 bg-cover bg-center opacity-70" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-light/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                
                <div className="absolute top-6 left-4 bg-white shadow-sm rounded-lg px-3 py-1.5 border border-slate-200 flex flex-col z-20">
                  <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wide">Radar Latest</span>
                  <span className="text-sm font-semibold text-slate-700">14:20 น.</span>
                </div>

                <div className="absolute inset-0 flex items-center justify-center opacity-50 mix-blend-multiply z-0">
                   <div className="w-48 h-48 relative -mt-10 -ml-10 transition-transform duration-500" style={{ transform: `scale(${1 + frameIndex * 0.02})` }}>
                     <div className="absolute w-full h-full" style={{ backgroundImage: 'radial-gradient(circle, #f00 0%, #f90 30%, #0f0 60%, transparent 100%)', filter: 'url(#pixelate) blur(1px)', clipPath: 'circle(40% at 30% 30%)' }}></div>
                   </div>
                </div>

                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10 transition-transform duration-500" style={{ transform: `scale(${1 + frameIndex * 0.05})` }}>
                  <div className="absolute inset-0 rounded-full border-2 border-orange-400 bg-transparent"></div>
                  <div className="absolute top-1/4 left-1/4 w-16 h-16 rounded-full border-2 border-red-500 bg-transparent"></div>
                </div>
                
                <div className="absolute top-1/4 right-1/4 flex flex-col items-center z-20">
                  <MapPin className="w-7 h-7 text-blue-600 drop-shadow-sm" fill="white" />
                </div>
              </div>

              <div 
                className="bg-white rounded-t-3xl relative z-30 shadow-[0_-10px_30px_rgba(0,0,0,0.08)] flex flex-col border-t border-slate-100 transition-all duration-300 ease-in-out"
                style={{ height: getBottomSheetHeight() }}
              >
                <div className="w-full pt-3 pb-2 flex justify-center cursor-pointer" onClick={toggleSnap}>
                  <div className="w-12 h-1.5 bg-slate-200 rounded-full"></div>
                </div>

                <div className="px-6 flex flex-col h-full overflow-hidden">
                  
                  <div className="flex items-center justify-between mb-6 shrink-0">
                    <div>
                      <h3 className="font-bold text-2xl text-slate-900 tracking-tight">ฝนหนักกำลังมา</h3>
                      <p className="text-slate-500 text-sm mt-1">ระดับ 45+ dBZ, ต่อเนื่อง 1 ชั่วโมง</p>
                    </div>
                    <span className="text-red-600 font-bold bg-red-50 px-3 py-2 rounded-xl text-sm border border-red-100 shadow-sm">ใน 20 นาที</span>
                  </div>

                  <div className="w-full mb-8 shrink-0">
                    {/* Impeccable Layout: gap-1 between bars */}
                    <div className="h-16 flex items-end gap-1 w-full border-b-2 border-slate-100 pb-2 relative">
                      <div className="flex-1 bg-slate-100 rounded-sm h-[20%]"></div>
                      <div className="flex-1 bg-blue-100 rounded-sm h-[30%]"></div>
                      
                      <div className="absolute bottom-0 left-[25%] top-[-10px] w-0.5 bg-slate-300 z-10"></div>
                      
                      <div className="flex-1 bg-blue-500 rounded-sm h-[50%]"></div>
                      <div className="flex-1 bg-orange-400 rounded-sm h-[80%]"></div>
                      <div className="flex-1 bg-red-500 rounded-sm h-[95%] shadow-sm"></div>
                      <div className="flex-1 bg-orange-400 rounded-sm h-[60%]"></div>
                      <div className="flex-1 bg-slate-100 rounded-sm h-[15%]"></div>
                    </div>
                    <div className="flex justify-between text-[11px] font-bold text-slate-400 mt-2 uppercase tracking-wide">
                      <span>Now</span>
                      <span>1 Hr</span>
                      <span>2 Hr</span>
                    </div>
                  </div>

                  <div className="bg-slate-50 rounded-2xl p-5 border border-slate-100 flex flex-col gap-4 mt-auto shrink-0 mb-6">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-bold text-slate-700">ภาพย้อนหลัง 6 เฟรม</span>
                      <span className="text-sm font-bold text-slate-500 w-12 text-right">{times[frameIndex]}</span>
                    </div>
                    <div className="flex items-center gap-5">
                      <button 
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition shadow-sm ${isPlaying ? 'bg-orange-100 text-orange-600 border border-orange-200' : 'bg-slate-900 text-white hover:bg-slate-800'}`}
                      >
                        {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
                      </button>
                      <div className="flex-1 h-2.5 bg-slate-200 rounded-full relative shadow-inner">
                        <div 
                          className="absolute left-0 top-0 bottom-0 bg-blue-600 rounded-full transition-all duration-300 ease-linear"
                          style={{ width: `${progressPercent}%` }}
                        ></div>
                        <div 
                          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 bg-white rounded-full shadow border border-slate-300 transition-all duration-300 ease-linear"
                          style={{ left: `${progressPercent}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 2 - Style C: Material 3 (Pastel) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-orange-600">Style C: Material 3 (Pastel)</h3>
            <div className="w-[375px] h-[812px] bg-orange-50/50 rounded-[40px] border-[8px] border-slate-200 overflow-hidden relative shadow-2xl flex flex-col">
              
              <div className="relative bg-orange-100/50 w-full overflow-hidden transition-all duration-300 ease-in-out" style={{ height: `calc(100% - ${getBottomSheetHeight()})` }}>
                {/* Simulated map background for material style */}
                <div className="absolute inset-0 bg-cover bg-center opacity-60" style={{ backgroundImage: "url('https://api.maptiler.com/maps/streets-v2-light/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')", filter: "sepia(20%) hue-rotate(-10deg) saturate(150%)" }} />
                
                <div className="absolute top-6 left-4 bg-orange-100/90 backdrop-blur-md rounded-full px-4 py-2 flex items-center gap-2 z-20 shadow-sm border border-orange-200/50">
                  <Activity className="w-4 h-4 text-orange-600" />
                  <span className="text-xs font-semibold text-orange-900">14:20 น.</span>
                </div>

                <div className="absolute inset-0 flex items-center justify-center opacity-60 mix-blend-multiply z-0">
                   <div className="w-48 h-48 relative -mt-10 -ml-10 transition-transform duration-500" style={{ transform: `scale(${1 + frameIndex * 0.02})` }}>
                     <div className="absolute w-full h-full" style={{ backgroundImage: 'radial-gradient(circle, #ea580c 0%, #f59e0b 40%, transparent 80%)', filter: 'url(#pixelate) blur(4px)', clipPath: 'circle(40% at 30% 30%)' }}></div>
                   </div>
                </div>

                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10 transition-transform duration-500" style={{ transform: `scale(${1 + frameIndex * 0.05})` }}>
                  <div className="absolute inset-0 rounded-full border-2 border-orange-500/50 bg-orange-500/10"></div>
                </div>
                
                <div className="absolute top-1/4 right-1/4 flex flex-col items-center z-20">
                  <div className="w-10 h-10 rounded-[14px] bg-white flex items-center justify-center shadow-lg border border-orange-100 rotate-12">
                     <Droplets className="w-5 h-5 text-orange-500" />
                  </div>
                </div>
              </div>

              <div 
                className="bg-stone-50 rounded-t-[32px] relative z-30 shadow-[0_-20px_40px_rgba(0,0,0,0.1)] flex flex-col transition-all duration-300 ease-in-out"
                style={{ height: getBottomSheetHeight() }}
              >
                <div className="w-full pt-4 pb-2 flex justify-center cursor-pointer" onClick={toggleSnap}>
                  <div className="w-10 h-1.5 bg-stone-300 rounded-full"></div>
                </div>

                <div className="px-6 flex flex-col h-full overflow-hidden">
                  
                  <div className="flex flex-col items-center mb-8 shrink-0 text-center">
                    <h3 className="font-medium text-3xl text-stone-900 tracking-tight mb-2">ฝนตกหนัก</h3>
                    <div className="bg-orange-200 text-orange-900 px-4 py-1.5 rounded-full text-sm font-medium">จะถึงตำแหน่งคุณใน 20 นาที</div>
                  </div>

                  <div className="w-full mb-8 shrink-0 bg-white rounded-3xl p-5 shadow-sm border border-stone-100">
                    <div className="h-12 flex items-end gap-1 w-full pb-1 relative">
                      <div className="flex-1 bg-stone-200 rounded-md h-[20%]"></div>
                      <div className="flex-1 bg-stone-300 rounded-md h-[30%]"></div>
                      <div className="flex-1 bg-orange-300 rounded-md h-[50%]"></div>
                      <div className="flex-1 bg-orange-500 rounded-md h-[80%]"></div>
                      <div className="flex-1 bg-red-500 rounded-md h-[95%] shadow-sm"></div>
                      <div className="flex-1 bg-orange-400 rounded-md h-[60%]"></div>
                      <div className="flex-1 bg-stone-200 rounded-md h-[15%]"></div>
                    </div>
                  </div>

                  <div className="bg-orange-100/50 rounded-3xl p-5 flex flex-col gap-4 mt-auto shrink-0 mb-6">
                    <div className="flex items-center gap-5">
                      <button 
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 transition shadow-sm ${isPlaying ? 'bg-white text-orange-800' : 'bg-orange-800 text-white'}`}
                      >
                        {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                      </button>
                      <div className="flex-1 flex flex-col gap-2">
                        <div className="flex justify-between items-center px-1">
                          <span className="text-sm font-medium text-stone-600">ภาพย้อนหลัง</span>
                          <span className="text-sm font-bold text-stone-900">{times[frameIndex]}</span>
                        </div>
                        <div className="w-full h-3 bg-white/60 rounded-full relative shadow-inner">
                          <div 
                            className="absolute left-0 top-0 bottom-0 bg-orange-500 rounded-full transition-all duration-300 ease-linear"
                            style={{ width: `${progressPercent}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>

          {/* 2 - Style D: Meteorological Dark */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-slate-400">Style D: Meteorological Dark</h3>
            <div className="w-[375px] h-[812px] rounded-[40px] border-[8px] border-slate-800 overflow-hidden relative shadow-2xl flex flex-col bg-[#13171f]">
              
              {/* MAP AREA */}
              <div className="relative w-full overflow-hidden transition-all duration-300 ease-in-out" style={{ height: `calc(100% - ${getBottomSheetHeight()})` }}>
                <div className="absolute inset-0 bg-cover bg-center opacity-40"
                  style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />

                {/* RADAR LATEST BADGE */}
                <div className="absolute top-6 left-4 bg-slate-900/90 rounded-lg px-3 py-1.5 flex flex-col z-20 border border-slate-700/50 backdrop-blur-sm">
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider font-medium">TMD Radar Latest</span>
                  <span className="text-sm font-medium text-slate-100 flex items-center gap-1.5">
                    14:20 น.
                  </span>
                </div>

                <button className="absolute top-6 right-4 bg-slate-900/90 rounded-full p-2.5 z-20 border border-slate-700/50 backdrop-blur-sm hover:bg-slate-800 transition-colors">
                  <Layers className="w-4 h-4 text-slate-300" />
                </button>

                {/* RAW RADAR IMAGE layer */}
                <div className="absolute inset-0 flex items-center justify-center mix-blend-screen opacity-50 z-0">
                  <div className="w-48 h-48 relative -mt-10 -ml-10">
                    <div className="absolute w-full h-full transition-transform duration-500"
                      style={{ backgroundImage: 'radial-gradient(circle, #f00 0%, #ff0 30%, #0f0 60%, transparent 100%)', filter: 'blur(2px)', clipPath: 'circle(40% at 30% 30%)', transform: `scale(${1 + frameIndex * 0.02})` }}></div>
                  </div>
                </div>

                {/* VECTOR overlay */}
                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10 transition-transform duration-500" style={{ transform: `scale(${1 + frameIndex * 0.05})` }}>
                  <div className="absolute inset-0 rounded-full border border-blue-400/30 bg-blue-500/5"></div>
                  <div className="absolute top-1/4 left-1/4 w-16 h-16 rounded-full border border-rose-400/40 bg-rose-500/5"></div>
                  <svg className="absolute top-1/2 left-1/2 w-48 h-48 overflow-visible" style={{ transform: 'translate(-10px, -10px)' }}>
                    <path d="M 0 0 L 100 -50 L 150 -70" fill="none" stroke="#60a5fa" strokeWidth="2" strokeDasharray="6 4" strokeLinecap="round" opacity="0.6" />
                  </svg>
                </div>

                <div className="absolute top-1/4 right-1/4 flex flex-col items-center z-20">
                  <MapPin className="w-7 h-7 text-blue-400 drop-shadow-md" fill="#13171f" />
                </div>
              </div>

              {/* BOTTOM SHEET */}
              <div
                className="bg-[#1a1f2b] rounded-t-3xl relative z-30 flex flex-col transition-all duration-300 ease-in-out border-t border-slate-700 shadow-[0_-10px_30px_rgba(0,0,0,0.5)]"
                style={{ height: getBottomSheetHeight() }}
                onClick={toggleSnap}
              >
                <div className="w-full pt-3 pb-2 flex justify-center cursor-pointer">
                  <div className="w-12 h-1.5 rounded-full bg-slate-600"></div>
                </div>

                <div className="px-6 flex flex-col h-full overflow-hidden">

                  {/* Headline */}
                  <div className="flex items-center justify-between mb-6 shrink-0" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-3">
                      <div className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-[0_0_8px_#f43f5e]"></div>
                      <h3 className="font-medium text-xl text-white">ฝนหนักกำลังมา</h3>
                    </div>
                    <span className="font-medium text-sm px-3 py-1.5 rounded-lg text-rose-200 bg-rose-500/20 border border-rose-500/20">ETA: 20m</span>
                  </div>

                  {/* Timeline BarChart */}
                  <div className="w-full mb-6 shrink-0" onClick={e => e.stopPropagation()}>
                    <span className="text-[11px] font-medium uppercase tracking-widest text-slate-500 mb-3 block">Intensity (Next 2 hrs)</span>
                    <div className="h-16 flex items-end gap-1 w-full pb-2 relative border-b border-slate-800">
                      <div className="flex-1 rounded-sm h-[10%] bg-slate-700/50"></div>
                      <div className="flex-1 rounded-sm h-[30%] bg-slate-700/50"></div>
                      <div className="absolute bottom-0 left-[25%] top-[-10px] w-px bg-blue-500/50 z-10">
                        <span className="absolute -top-4 -translate-x-1/2 text-[10px] font-medium text-blue-400 bg-[#1a1f2b] px-1 rounded">NOW</span>
                      </div>
                      <div className="flex-1 rounded-sm h-[50%] bg-blue-500"></div>
                      <div className="flex-1 rounded-sm h-[80%] bg-amber-400"></div>
                      <div className="flex-1 rounded-sm h-[95%] bg-rose-500 shadow-[0_0_8px_#f43f5e88]"></div>
                      <div className="flex-1 rounded-sm h-[60%] bg-amber-400"></div>
                      <div className="flex-1 rounded-sm h-[20%] bg-slate-700/50"></div>
                      <div className="flex-1 rounded-sm h-[10%] bg-slate-700/50"></div>
                    </div>
                  </div>

                  {/* 6 Frames Playback */}
                  <div className="rounded-2xl p-5 flex flex-col gap-4 mt-auto shrink-0 mb-6 bg-slate-800/40 border border-slate-700/50"
                    onClick={e => e.stopPropagation()}>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-slate-400">ภาพย้อนหลัง (Past 6 Frames)</span>
                      <span className="text-sm font-medium text-blue-400">{times[frameIndex]}</span>
                    </div>
                    <div className="flex items-center gap-5">
                      <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all border ${isPlaying ? 'bg-blue-500/20 border-blue-500/50 text-blue-400' : 'bg-slate-700 border-slate-600 text-slate-300'}`}
                      >
                        {isPlaying
                          ? <Pause className="w-4 h-4" />
                          : <Play className="w-4 h-4 ml-0.5" />}
                      </button>
                      <div className="flex-1 h-2.5 rounded-full relative shadow-inner bg-slate-800 border border-slate-700/50">
                        <div
                          className="absolute left-0 top-0 bottom-0 rounded-full transition-all duration-300 ease-linear bg-blue-500 shadow-[0_0_6px_rgba(59,130,246,0.4)]"
                          style={{ width: `${progressPercent}%` }}
                        ></div>
                        <div
                          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full shadow-md border-2 transition-all duration-300 ease-linear bg-[#1a1f2b] border-blue-400"
                          style={{ left: `${progressPercent}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>

          {/* 2 - Style E: Dynamic Weather (Clear Sky) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-sky-500">Style E: Dynamic (Clear Sky)</h3>
            <div className="w-[375px] h-[812px] rounded-[40px] border-[8px] border-slate-200 overflow-hidden relative shadow-2xl flex flex-col bg-gradient-to-b from-sky-100 to-white">
              
              {/* MAP AREA */}
              <div className="relative w-full overflow-hidden transition-all duration-300 ease-in-out" style={{ height: `calc(100% - ${getBottomSheetHeight()})` }}>
                <div className="absolute inset-0 bg-cover bg-center opacity-60"
                  style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-light/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />

                {/* RADAR LATEST BADGE */}
                <div className="absolute top-6 left-4 bg-white/90 rounded-lg px-3 py-1.5 flex flex-col z-20 border border-slate-200 shadow-sm backdrop-blur-md">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">TMD Radar</span>
                  <span className="text-sm font-bold text-sky-900">
                    14:20 น.
                  </span>
                </div>

                <button className="absolute top-6 right-4 bg-white/90 rounded-full p-2.5 z-20 border border-slate-200 shadow-sm backdrop-blur-md hover:bg-slate-50 transition-colors">
                  <Layers className="w-4 h-4 text-slate-600" />
                </button>

                {/* VECTOR overlay */}
                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10 transition-transform duration-500" style={{ transform: `scale(${1 + frameIndex * 0.05})` }}>
                  <div className="absolute inset-0 rounded-full border border-sky-400/50 bg-sky-300/10"></div>
                  <svg className="absolute top-1/2 left-1/2 w-48 h-48 overflow-visible" style={{ transform: 'translate(-10px, -10px)' }}>
                    <path d="M 0 0 L 100 -50 L 150 -70" fill="none" stroke="#0ea5e9" strokeWidth="2" strokeDasharray="6 4" strokeLinecap="round" opacity="0.6" />
                  </svg>
                </div>

                <div className="absolute top-1/4 right-1/4 flex flex-col items-center z-20">
                  <MapPin className="w-7 h-7 text-sky-500 drop-shadow-md" fill="#ffffff" />
                </div>
              </div>

              {/* BOTTOM SHEET */}
              <div
                className="bg-white/90 backdrop-blur-xl rounded-t-3xl relative z-30 flex flex-col transition-all duration-300 ease-in-out border-t border-white shadow-[0_-10px_30px_rgba(0,0,0,0.05)]"
                style={{ height: getBottomSheetHeight() }}
                onClick={toggleSnap}
              >
                <div className="w-full pt-3 pb-2 flex justify-center cursor-pointer">
                  <div className="w-12 h-1.5 rounded-full bg-slate-200"></div>
                </div>

                <div className="px-6 flex flex-col h-full overflow-hidden">

                  {/* Headline */}
                  <div className="flex items-center justify-between mb-6 shrink-0" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-3">
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></div>
                      <h3 className="font-semibold text-xl text-slate-800">อากาศแจ่มใส</h3>
                    </div>
                    <span className="font-semibold text-sm px-3 py-1.5 rounded-lg text-emerald-700 bg-emerald-50 border border-emerald-100">0 mm/h</span>
                  </div>

                  {/* Timeline BarChart */}
                  <div className="w-full mb-6 shrink-0" onClick={e => e.stopPropagation()}>
                    <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-3 block">Intensity (Next 2 hrs)</span>
                    <div className="h-16 flex items-end gap-1 w-full pb-2 relative border-b border-slate-100">
                      <div className="flex-1 rounded-sm h-[10%] bg-slate-100"></div>
                      <div className="flex-1 rounded-sm h-[5%] bg-slate-100"></div>
                      <div className="absolute bottom-0 left-[25%] top-[-10px] w-px bg-sky-200 z-10">
                        <span className="absolute -top-4 -translate-x-1/2 text-[10px] font-bold text-sky-500 bg-white px-1 rounded">NOW</span>
                      </div>
                      <div className="flex-1 rounded-sm h-[5%] bg-slate-100"></div>
                      <div className="flex-1 rounded-sm h-[5%] bg-slate-100"></div>
                      <div className="flex-1 rounded-sm h-[5%] bg-slate-100"></div>
                      <div className="flex-1 rounded-sm h-[10%] bg-slate-100"></div>
                      <div className="flex-1 rounded-sm h-[10%] bg-slate-100"></div>
                      <div className="flex-1 rounded-sm h-[5%] bg-slate-100"></div>
                    </div>
                  </div>

                  {/* 6 Frames Playback */}
                  <div className="rounded-2xl p-5 flex flex-col gap-4 mt-auto shrink-0 mb-6 bg-slate-50 border border-slate-100"
                    onClick={e => e.stopPropagation()}>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-semibold text-slate-500">ภาพย้อนหลัง</span>
                      <span className="text-sm font-bold text-sky-600">{times[frameIndex]}</span>
                    </div>
                    <div className="flex items-center gap-5">
                      <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all border ${isPlaying ? 'bg-sky-100 border-sky-200 text-sky-600' : 'bg-white border-slate-200 text-slate-400 shadow-sm'}`}
                      >
                        {isPlaying
                          ? <Pause className="w-4 h-4" />
                          : <Play className="w-4 h-4 ml-0.5" />}
                      </button>
                      <div className="flex-1 h-2.5 rounded-full relative bg-slate-200">
                        <div
                          className="absolute left-0 top-0 bottom-0 rounded-full transition-all duration-300 ease-linear bg-sky-400"
                          style={{ width: `${progressPercent}%` }}
                        ></div>
                        <div
                          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full shadow-sm border-2 transition-all duration-300 ease-linear bg-white border-sky-500"
                          style={{ left: `${progressPercent}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>

          {/* 2 - Style F: Dynamic Weather (Storm Alert) */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-red-600">Style F: Dynamic (Storm Alert)</h3>
            <div className="w-[375px] h-[812px] rounded-[40px] border-[8px] border-slate-900 overflow-hidden relative shadow-2xl flex flex-col bg-[#140b0b]">
              
              {/* MAP AREA */}
              <div className="relative w-full overflow-hidden transition-all duration-300 ease-in-out" style={{ height: `calc(100% - ${getBottomSheetHeight()})` }}>
                <div className="absolute inset-0 bg-cover bg-center opacity-30 mix-blend-luminosity"
                  style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                
                <div className="absolute inset-0 bg-red-950/20 mix-blend-multiply"></div>

                {/* RADAR LATEST BADGE */}
                <div className="absolute top-6 left-4 bg-rose-950/80 rounded-lg px-3 py-1.5 flex flex-col z-20 border border-rose-900/50 backdrop-blur-sm">
                  <span className="text-[10px] text-rose-300/70 uppercase tracking-widest font-semibold">TMD Radar</span>
                  <span className="text-sm font-bold text-rose-100 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></span>
                    14:20 น.
                  </span>
                </div>

                <button className="absolute top-6 right-4 bg-rose-950/80 rounded-full p-2.5 z-20 border border-rose-900/50 backdrop-blur-sm hover:bg-rose-900 transition-colors">
                  <Layers className="w-4 h-4 text-rose-300" />
                </button>

                {/* RAW RADAR IMAGE layer */}
                <div className="absolute inset-0 flex items-center justify-center mix-blend-screen opacity-80 z-0">
                  <div className="w-64 h-64 relative -mt-10 -ml-10">
                    <div className="absolute w-full h-full transition-transform duration-500"
                      style={{ backgroundImage: 'radial-gradient(circle, #f00 0%, #ff0 30%, #0f0 60%, transparent 100%)', filter: 'blur(3px)', clipPath: 'circle(40% at 30% 30%)', transform: `scale(${1 + frameIndex * 0.03})` }}></div>
                  </div>
                </div>

                <div className="absolute top-1/4 right-1/4 flex flex-col items-center z-20">
                  <MapPin className="w-7 h-7 text-red-500 drop-shadow-md" fill="#140b0b" />
                </div>
              </div>

              {/* BOTTOM SHEET */}
              <div
                className="bg-[#241313] rounded-t-3xl relative z-30 flex flex-col transition-all duration-300 ease-in-out border-t border-rose-900/40 shadow-[0_-10px_40px_rgba(225,29,72,0.15)]"
                style={{ height: getBottomSheetHeight() }}
                onClick={toggleSnap}
              >
                <div className="w-full pt-3 pb-2 flex justify-center cursor-pointer">
                  <div className="w-12 h-1.5 rounded-full bg-rose-950"></div>
                </div>

                <div className="px-6 flex flex-col h-full overflow-hidden">

                  {/* Headline */}
                  <div className="flex items-center justify-between mb-6 shrink-0" onClick={e => e.stopPropagation()}>
                    <div className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse shadow-[0_0_12px_#ef4444]"></div>
                      <h3 className="font-semibold text-xl text-rose-50 tracking-wide">พายุฝนฟ้าคะนอง</h3>
                    </div>
                    <span className="font-bold text-sm px-3 py-1.5 rounded-lg text-red-100 bg-red-600 border border-red-500 shadow-sm">อันตราย</span>
                  </div>

                  {/* Timeline BarChart */}
                  <div className="w-full mb-6 shrink-0" onClick={e => e.stopPropagation()}>
                    <span className="text-[11px] font-bold uppercase tracking-widest text-rose-500/70 mb-3 block">Intensity (Next 2 hrs)</span>
                    <div className="h-16 flex items-end gap-1 w-full pb-2 relative border-b border-rose-950">
                      <div className="flex-1 rounded-sm h-[30%] bg-rose-900/40"></div>
                      <div className="flex-1 rounded-sm h-[60%] bg-amber-500/80"></div>
                      <div className="absolute bottom-0 left-[25%] top-[-10px] w-px bg-rose-500/50 z-10">
                        <span className="absolute -top-4 -translate-x-1/2 text-[10px] font-bold text-rose-400 bg-[#241313] px-1 rounded">NOW</span>
                      </div>
                      <div className="flex-1 rounded-sm h-[90%] bg-red-500 shadow-[0_0_8px_#ef444466]"></div>
                      <div className="flex-1 rounded-sm h-[100%] bg-rose-600 shadow-[0_0_12px_#e11d4888]"></div>
                      <div className="flex-1 rounded-sm h-[80%] bg-red-500"></div>
                      <div className="flex-1 rounded-sm h-[50%] bg-amber-500/80"></div>
                      <div className="flex-1 rounded-sm h-[20%] bg-rose-900/40"></div>
                      <div className="flex-1 rounded-sm h-[10%] bg-rose-900/40"></div>
                    </div>
                  </div>

                  {/* 6 Frames Playback */}
                  <div className="rounded-2xl p-5 flex flex-col gap-4 mt-auto shrink-0 mb-6 bg-rose-950/20 border border-rose-900/30"
                    onClick={e => e.stopPropagation()}>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-semibold text-rose-300/70">ภาพย้อนหลัง (Past 6 Frames)</span>
                      <span className="text-sm font-bold text-rose-400">{times[frameIndex]}</span>
                    </div>
                    <div className="flex items-center gap-5">
                      <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 transition-all border ${isPlaying ? 'bg-red-500/20 border-red-500/40 text-red-400' : 'bg-rose-900/50 border-rose-800 text-rose-300'}`}
                      >
                        {isPlaying
                          ? <Pause className="w-4 h-4" />
                          : <Play className="w-4 h-4 ml-0.5" />}
                      </button>
                      <div className="flex-1 h-2.5 rounded-full relative shadow-inner bg-rose-950/80">
                        <div
                          className="absolute left-0 top-0 bottom-0 rounded-full transition-all duration-300 ease-linear bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]"
                          style={{ width: `${progressPercent}%` }}
                        ></div>
                        <div
                          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full shadow-md border-2 transition-all duration-300 ease-linear bg-[#241313] border-red-400"
                          style={{ left: `${progressPercent}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* ======================= FLOW 3: ADMIN DEBUG VIEWER ======================= */}
      <div className="max-w-[1400px] w-full mb-10">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Step 3: Admin Debug Mode (Tester เลือกได้ 2 แบบ)</h2>
        <p className="text-slate-500 mb-8">Split Screen (สำหรับคนที่ชอบเทียบชัดๆ บน-ล่าง) และ PiP (สำหรับคนที่อยากดู Native เต็มตาแล้วชำเลืองมองบอท)</p>
        
        <div className="flex flex-wrap justify-center gap-10">
          
          {/* Debug 1: Split Screen */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-rose-500 flex items-center gap-2">
              <SplitSquareVertical className="w-5 h-5" /> Split Screen Debug
            </h3>
            
            <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-rose-900 overflow-hidden relative shadow-2xl flex flex-col">
              <div className="h-[45%] relative bg-slate-800 w-full overflow-hidden">
                <div className="absolute inset-0 bg-cover bg-center opacity-40" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                <div className="absolute top-2 left-2 bg-rose-500/20 text-rose-400 border border-rose-500/50 px-2 py-0.5 rounded text-[10px] font-bold">NATIVE VECTOR</div>
                
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 z-10">
                  <div className="absolute inset-0 rounded-full border-2 border-amber-400 bg-amber-500/10"></div>
                  <svg className="absolute top-1/2 left-1/2 w-48 h-48 overflow-visible" style={{ transform: 'translate(-10px, -10px)' }}>
                     <path d="M 0 0 L 80 -40" fill="none" stroke="#3b82f6" strokeWidth="2" strokeDasharray="4 2" />
                  </svg>
                </div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center z-20">
                  <MapPin className="w-6 h-6 text-white" fill="#3b82f6" />
                </div>
              </div>

              <div className="h-6 bg-slate-950 flex items-center justify-center border-y border-slate-800 cursor-row-resize z-30 shadow-[0_0_10px_rgba(0,0,0,0.5)]">
                 <div className="w-12 h-1 rounded-full bg-slate-700"></div>
              </div>

              <div className="flex-1 bg-black relative w-full overflow-hidden flex flex-col">
                <div className="absolute top-2 left-2 bg-slate-700 text-white px-2 py-0.5 rounded text-[10px] font-bold z-10">BOT STATIC IMAGE (JPG)</div>
                <div className="flex-1 flex items-center justify-center p-4">
                  <div className="w-full aspect-[4/5] bg-slate-800 rounded-lg overflow-hidden border border-slate-700 shadow-lg relative flex items-center justify-center">
                    <div className="absolute inset-0 bg-[url('https://api.maptiler.com/maps/streets-v2/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')] opacity-50 bg-cover"></div>
                    <div className="absolute inset-0 flex items-center justify-center mix-blend-multiply opacity-80">
                      <div className="w-48 h-48 bg-[radial-gradient(circle,#f00_0%,#ff0_30%,transparent_60%)] filter blur-[2px] opacity-80"></div>
                    </div>
                    <div className="absolute bottom-2 left-2 bg-black/60 text-[8px] text-white p-1 font-mono">Radar_Latest.jpg<br/>14:20:00</div>
                  </div>
                </div>
                <div className="h-14 bg-slate-900 border-t border-slate-800 flex items-center justify-between px-4">
                  <span className="text-xs text-slate-400">View:</span>
                  <div className="flex gap-2">
                    <button className="bg-blue-600 text-[10px] text-white px-3 py-1.5 rounded-md font-bold">Latest.jpg</button>
                    <button className="bg-slate-800 border border-slate-700 text-[10px] text-slate-300 px-3 py-1.5 rounded-md hover:bg-slate-700">6_frames.gif</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Debug 2: PiP */}
          <div className="flex flex-col items-center">
            <h3 className="text-md font-semibold mb-3 text-orange-500 flex items-center gap-2">
              <Bug className="w-5 h-5" /> PiP Overlay Debug
            </h3>
            
            <div className="w-[375px] h-[812px] bg-slate-100 rounded-[40px] border-[8px] border-orange-500/50 overflow-hidden relative shadow-2xl flex flex-col">
              <div className="h-[70%] relative bg-slate-200 w-full overflow-hidden">
                <div className="absolute inset-0 bg-cover bg-center opacity-70" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-light/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                
                <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10">
                  <div className="absolute inset-0 rounded-full border-2 border-orange-400 bg-transparent"></div>
                </div>
                
                {/* PIP WINDOW */}
                <div className="absolute bottom-6 right-4 w-32 h-44 bg-black rounded-xl shadow-2xl border-2 border-orange-500 overflow-hidden z-40 transform transition-transform hover:scale-110 origin-bottom-right">
                   <div className="bg-orange-500 text-black text-[8px] font-bold flex justify-between px-2 py-1 items-center">
                     <span>BOT.JPG</span>
                     <span className="opacity-50">✕</span>
                   </div>
                   <div className="w-full h-full bg-[url('https://api.maptiler.com/maps/streets-v2/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')] bg-cover relative">
                      <div className="absolute inset-0 bg-[radial-gradient(circle,#f00_0%,#ff0_30%,transparent_60%)] filter blur-[1px] opacity-70 mix-blend-multiply -translate-x-2 -translate-y-2"></div>
                   </div>
                </div>
              </div>
              <div className="flex-1 bg-white p-5 relative z-30 border-t border-slate-200 flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-bold text-lg text-slate-900">ฝนหนักกำลังมา</h3>
                </div>
                <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100 mt-auto">
                   <div className="flex items-center gap-4">
                    <button className="w-10 h-10 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center border border-orange-200">
                      <Bug className="w-5 h-5" />
                    </button>
                    <div className="text-sm font-semibold text-slate-700">Toggle Admin Image Viewer</div>
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
