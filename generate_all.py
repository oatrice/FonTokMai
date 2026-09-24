import os

def load_template(is_overlay=False):
    bottom_class = 'bottom-6' if is_overlay else 'bottom-24'
    name = 'RadarMockupsOverlayPrototype' if is_overlay else 'RadarMockupsPrototype'
    
    code = """
function PROTOTYPE_NAME() {
  const [currentScreen, setCurrentScreen] = useState<AppScreen>('map');
  const [isAdmin, setIsAdmin] = useState(true);

  // --- UI Visibility States ---
  const [isUIHidden, setIsUIHidden] = useState(false); 
  const [isCardMinimized, setIsCardMinimized] = useState(false);

  // --- Timeline State (Future Prediction Included) ---
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(6);
  const times = ['-30m', '-25m', '-20m', '-15m', '-10m', '-5m', 'NOW', '+5m', '+10m', '+15m', '+20m', '+25m', '+30m'];

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(() => {
        setFrameIndex((prev) => (prev + 1) % times.length);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isPlaying, times.length]);

  const [layerMode, setLayerMode] = useState<'minimal' | 'pro'>('pro');
  const [mockWeather, setMockWeather] = useState<'clear' | 'rain' | 'storm' | 'offline'>('rain');
  
  const [activePlaceIndex, setActivePlaceIndex] = useState(0);
  const [isOverview, setIsOverview] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [expandedPlace, setExpandedPlace] = useState<string | null>('home');
  
  const places = [
    { id: 'home', name: 'บ้าน', address: 'บางนา, กรุงเทพฯ', policy: 'always', snooze: 'active', bgPos: 'center' },
    { id: 'work', name: 'ที่ทำงาน', address: 'สาทร, กรุงเทพฯ', policy: 'schedule', snooze: '1h', bgPos: 'bottom right' },
    { id: 'school', name: 'โรงเรียน', address: 'ปทุมวัน, กรุงเทพฯ', policy: 'ask', snooze: 'active', bgPos: 'top left' },
  ];
  
  const activePlace = places[activePlaceIndex];

  const renderMainMap = () => (
    <div className="relative h-full w-full bg-slate-900 overflow-hidden flex flex-col">
      <div 
        className="absolute inset-0 bg-cover transition-all duration-1000 ease-in-out origin-center cursor-pointer" 
        onClick={() => setIsUIHidden(!isUIHidden)}
        style={{ 
          backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/600x800.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')",
          backgroundPosition: isOverview ? 'center' : activePlace.bgPos,
          transform: isOverview ? 'scale(1)' : 'scale(1.5)',
          filter: mockWeather === 'offline' ? 'grayscale(100%) blur(4px)' : 'none'
        }} 
      />
      
      {isOverview ? (
         <div className="absolute inset-0 z-10 pointer-events-none">
           <div className="absolute top-[45%] left-[45%]"><MapPin className="text-blue-500 w-6 h-6 fill-blue-500/20 animate-bounce" /></div>
           <div className="absolute top-[60%] left-[65%]"><MapPin className="text-emerald-500 w-6 h-6 fill-emerald-500/20" /></div>
           <div className="absolute top-[30%] left-[40%]"><MapPin className="text-purple-500 w-6 h-6 fill-purple-500/20" /></div>
         </div>
      ) : (
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 transition-all duration-500 pointer-events-none">
            <div className="relative">
              <MapPin className="text-blue-500 w-10 h-10 -mt-10 fill-blue-500/20 drop-shadow-lg" />
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-4 h-4 bg-blue-500 rounded-full animate-ping opacity-50" />
            </div>
         </div>
      )}

      <div className={`absolute top-12 left-4 right-4 flex justify-between items-start z-30 transition-all duration-500 ${isUIHidden ? '-translate-y-24 opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'}`}>
        <div className="flex items-center gap-2">
          MENU_BUTTON
          <div className="relative">
            <button 
              onClick={() => setShowDropdown(!showDropdown)}
              className="bg-slate-900/90 backdrop-blur-md rounded-2xl px-4 py-2.5 flex items-center gap-2 shadow-lg border border-slate-700 text-white"
            >
              <MapPin className="w-4 h-4 text-blue-400" />
              <span className="font-semibold text-sm">{isOverview ? 'All Locations' : activePlace.name}</span>
              <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform ${showDropdown ? 'rotate-90' : ''}`} />
            </button>
            
            {showDropdown && (
              <div className="absolute top-full left-0 mt-2 w-48 bg-slate-800 border border-slate-700 rounded-2xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-top-2">
                <button 
                  onClick={() => { setIsOverview(true); setShowDropdown(false); }}
                  className="w-full text-left px-4 py-3 text-sm font-medium text-slate-200 hover:bg-slate-700 flex items-center gap-2 border-b border-slate-700/50"
                >
                  <Crosshair className="w-4 h-4 text-slate-400" />
                  View All (Overview)
                </button>
                {places.map((place, idx) => (
                  <button 
                    key={place.id}
                    onClick={() => { setActivePlaceIndex(idx); setIsOverview(false); setShowDropdown(false); }}
                    className={`w-full text-left px-4 py-3 text-sm font-medium flex items-center justify-between ${activePlaceIndex === idx && !isOverview ? 'bg-blue-500/20 text-blue-400' : 'text-slate-200 hover:bg-slate-700'}`}
                  >
                    {place.name}
                    {activePlaceIndex === idx && !isOverview && <CheckCircle2 className="w-4 h-4" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <button onClick={() => setIsOverview(!isOverview)} className={`w-11 h-11 backdrop-blur-md rounded-2xl flex items-center justify-center border shadow-lg transition-colors ${isOverview ? 'bg-blue-500 text-white border-blue-400' : 'bg-slate-900/90 text-slate-400 border-slate-700'}`}><Crosshair className="w-5 h-5" /></button>
          <button onClick={() => setLayerMode(prev => prev === 'minimal' ? 'pro' : 'minimal')} className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border border-slate-700 shadow-lg text-slate-400"><Layers className={`w-5 h-5 ${layerMode === 'pro' ? 'text-emerald-400' : 'text-slate-400'}`} /></button>
          ADMIN_BUTTON
        </div>
      </div>

      <div className={`absolute BOTTOM_CLASS left-4 right-4 z-30 transition-all duration-500 ${isUIHidden ? 'translate-y-32 opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'}`}>
        <div className={`bg-slate-900/85 backdrop-blur-xl border border-slate-700/50 rounded-3xl shadow-2xl relative overflow-hidden transition-all duration-500 ${isCardMinimized ? 'h-10' : 'h-[148px]'}`}>
          
          <div 
            className="w-full flex justify-center py-3 cursor-pointer relative hover:bg-slate-800/50 transition-colors"
            onClick={() => setIsCardMinimized(!isCardMinimized)}
          >
             <div className="w-12 h-1.5 bg-slate-600 rounded-full pointer-events-none" />
             <button 
               className="absolute right-4 top-2 text-slate-400 hover:text-white transition-colors"
               onClick={(e) => { e.stopPropagation(); setIsCardMinimized(!isCardMinimized); }}
             >
                {isCardMinimized ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
             </button>
          </div>

          <div className={`px-5 pb-5 transition-opacity duration-300 ${isCardMinimized ? 'opacity-0 pointer-events-none' : 'opacity-100 delay-100'}`}>
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-2 text-white font-semibold">
                {!isOverview && (
                  <div className="flex gap-1 mr-1">
                    <button onClick={() => { setActivePlaceIndex((prev) => (prev - 1 + places.length) % places.length); setIsOverview(false); }} className="p-1 bg-slate-800 rounded-full hover:bg-slate-700"><ChevronRight className="w-4 h-4 rotate-180" /></button>
                    <button onClick={() => { setActivePlaceIndex((prev) => (prev + 1) % places.length); setIsOverview(false); }} className="p-1 bg-slate-800 rounded-full hover:bg-slate-700"><ChevronRight className="w-4 h-4" /></button>
                  </div>
                )}
                {isOverview ? 'Overview' : activePlace.name}
              </div>
              
              {!isOverview && (
                <div className="flex gap-1.5">
                  {places.map((_, i) => (
                    <div key={i} className={`w-1.5 h-1.5 rounded-full ${i === activePlaceIndex ? 'bg-blue-400 w-3' : 'bg-slate-600'} transition-all`} />
                  ))}
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-4">
              <button 
                onClick={() => setIsPlaying(!isPlaying)}
                className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-lg transition-colors ${isPlaying ? 'bg-amber-500/20 text-amber-500' : 'bg-blue-600 text-white'}`}
              >
                {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
              </button>

              <div className="flex-1 relative flex flex-col justify-center h-10">
                <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-2 px-1">
                   <span>-30m</span>
                   <span className={frameIndex > 6 ? "text-purple-400" : "text-blue-400"}>
                     {frameIndex > 6 ? 'พยากรณ์ ' : ''}{times[frameIndex]}
                   </span>
                   <span>+30m</span>
                </div>
                <div className="absolute bottom-1 left-0 right-0 h-1.5 bg-slate-800 rounded-full overflow-hidden flex">
                  <div 
                    className={`h-full transition-all duration-300 ease-linear ${frameIndex > 6 ? 'bg-purple-500' : 'bg-blue-500'}`}
                    style={{ width: `${(frameIndex / (times.length - 1)) * 100}%` }}
                  />
                </div>
                <div className="absolute bottom-1 inset-x-0 flex justify-between items-center pointer-events-none px-1">
                  {times.map((_, i) => (
                    <div 
                      key={i} 
                      className={`rounded-full transition-colors ${
                        i === 6 ? 'bg-white w-2.5 h-2.5 shadow-[0_0_8px_rgba(255,255,255,0.8)]' : 
                        i <= frameIndex 
                          ? (i > 6 ? 'bg-purple-300 w-1.5 h-1.5' : 'bg-white w-1.5 h-1.5') 
                          : 'bg-slate-600 w-1 h-1'
                      }`} 
                    />
                  ))}
                </div>
                <input 
                  type="range" min="0" max={times.length - 1} 
                  value={frameIndex} 
                  onChange={(e) => { setFrameIndex(parseInt(e.target.value)); setIsPlaying(false); }}
                  className="absolute bottom-0 inset-x-0 w-full opacity-0 cursor-pointer h-6"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderPlaces = () => (
    <div className="h-full w-full bg-[#13171f] overflow-y-auto px-5 pt-16 pb-32">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          PLACES_BACK_BUTTON
          <h1 className="text-3xl font-semibold text-white tracking-tight m-0">My Places</h1>
        </div>
        <button 
          onClick={() => setCurrentScreen('add_place')}
          className="w-10 h-10 bg-blue-600 hover:bg-blue-500 text-white rounded-full flex items-center justify-center transition-colors shadow-lg shadow-blue-500/20"
        >
          <Plus className="w-6 h-6" />
        </button>
      </div>
      
      <div className="space-y-4">
        {places.map((place, idx) => {
          const isExpanded = expandedPlace === place.id;
          return (
            <div key={place.id} className="bg-slate-800/40 border border-slate-700/50 rounded-3xl overflow-hidden transition-all duration-300">
              <button 
                onClick={() => setExpandedPlace(isExpanded ? null : place.id)}
                className="w-full flex items-center gap-4 p-5 text-left"
              >
                <div className="w-12 h-12 rounded-full bg-slate-800 flex items-center justify-center shrink-0 border border-slate-700">
                  <MapPin className="w-6 h-6 text-blue-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-white text-lg">{place.name}</h3>
                  <p className="text-slate-400 text-sm mt-0.5">{place.address}</p>
                </div>
                <ChevronRight className={`w-5 h-5 text-slate-500 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
              </button>

              {isExpanded && (
                <div className="px-5 pb-6 pt-2 border-t border-slate-700/50">
                  <div className="flex items-center gap-3 mb-4 bg-slate-900/50 p-3 rounded-xl border border-slate-800">
                     <BellRing className="w-5 h-5 text-blue-400" />
                     <div className="text-xs">
                       <span className="text-slate-300 block font-medium">เตือน: {place.policy === 'always' ? 'ทุกครั้งที่มีฝน' : place.policy === 'ask' ? 'ฝนตกหนัก' : 'ตามเวลา (08:00)'}</span>
                       <span className="text-slate-500">ความครอบคลุมรัศมี 5 กม.</span>
                     </div>
                  </div>
                  <button 
                    onClick={() => { setCurrentScreen('map'); setActivePlaceIndex(idx); setIsOverview(false); setShowDropdown(false); }}
                    className="w-full py-3 bg-blue-500/20 text-blue-400 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 border border-blue-500/30 hover:bg-blue-500/30 transition-colors"
                  >
                    <Map className="w-4 h-4" />
                    ดูเรดาร์พื้นที่นี้
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderAddPlace = () => (
    <div className="h-full w-full bg-slate-50 overflow-y-auto flex flex-col">
       {/* Map Header */}
       <div className="h-48 bg-slate-200 relative shrink-0">
          <div 
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: "url('https://api.maptiler.com/maps/streets-v2/static/100.50,13.75,13/400x300.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }}
          />
          <div className="absolute inset-0 bg-gradient-to-b from-black/40 to-transparent" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
             <MapPin className="w-10 h-10 text-red-500 -mt-10 fill-red-500/20 drop-shadow-lg" />
             <div className="w-3 h-3 bg-red-500 rounded-full absolute bottom-0 left-1/2 -translate-x-1/2 shadow-lg" />
          </div>
          
          <button 
            onClick={() => setCurrentScreen('places')}
            className="absolute top-12 left-4 w-10 h-10 bg-white/90 backdrop-blur rounded-full flex items-center justify-center shadow-md text-slate-700"
          >
             <ChevronLeft className="w-6 h-6" />
          </button>
       </div>

       {/* Form Body */}
       <div className="flex-1 bg-white -mt-6 rounded-t-3xl p-6 shadow-[0_-10px_20px_rgba(0,0,0,0.05)] relative z-10">
          <h2 className="text-2xl font-bold text-slate-800 mb-6">บันทึกพิกัดใหม่</h2>

          <div className="space-y-5">
             <div>
               <label className="block text-sm font-semibold text-slate-700 mb-1.5">ชื่อสถานที่</label>
               <input type="text" placeholder="เช่น บ้าน, ที่ทำงาน" defaultValue="ร้านกาแฟประจำ" className="w-full bg-slate-100 border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:ring-2 focus:ring-blue-500 outline-none" />
             </div>
             
             <div>
               <label className="block text-sm font-semibold text-slate-700 mb-1.5">การแจ้งเตือนฝนตก</label>
               <div className="bg-slate-100 rounded-xl p-1 flex flex-col gap-1">
                 <button className="flex items-center justify-between p-3 rounded-lg bg-white shadow-sm border border-slate-200 text-left text-sm">
                   <div className="flex flex-col">
                     <span className="font-semibold text-slate-800">แจ้งเตือนเสมอ</span>
                     <span className="text-slate-500 text-xs mt-0.5">เตือนทุกครั้งที่ฝนกำลังจะตก</span>
                   </div>
                   <div className="w-5 h-5 rounded-full border-4 border-blue-500 bg-white" />
                 </button>
                 <button className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-200/50 text-left text-sm transition-colors border border-transparent">
                   <div className="flex flex-col">
                     <span className="font-semibold text-slate-700">แจ้งตามช่วงเวลา (Routine)</span>
                     <span className="text-slate-500 text-xs mt-0.5">เฉพาะ 07:00 - 09:00</span>
                   </div>
                   <div className="w-5 h-5 rounded-full border-2 border-slate-300" />
                 </button>
                 <button className="flex items-center justify-between p-3 rounded-lg hover:bg-slate-200/50 text-left text-sm transition-colors border border-transparent">
                   <div className="flex flex-col">
                     <span className="font-semibold text-slate-700">แจ้งเฉพาะพายุหนัก</span>
                     <span className="text-slate-500 text-xs mt-0.5">เตือนเฉพาะเมื่อมีพายุระดับรุนแรง</span>
                   </div>
                   <div className="w-5 h-5 rounded-full border-2 border-slate-300" />
                 </button>
               </div>
             </div>

             <div className="pt-4">
               <button onClick={() => setCurrentScreen('places')} className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl py-4 flex items-center justify-center gap-2 shadow-lg shadow-blue-600/30 transition-all">
                 <Save className="w-5 h-5" />
                 บันทึกข้อมูลพิกัด
               </button>
             </div>
          </div>
       </div>
    </div>
  );

  const renderAdmin = () => (
    <div className="h-full w-full bg-black overflow-y-auto px-5 pt-16 pb-32 text-slate-300 font-mono">
      <div className="flex items-center justify-between mb-8">
        ADMIN_HEADER
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
      <div className="w-[400px] h-[850px] bg-black rounded-[50px] border-[12px] border-slate-800 shadow-2xl relative overflow-hidden flex flex-col">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-7 bg-slate-800 rounded-b-3xl z-50" />
        
        <div className="flex-1 relative bg-black">
          {currentScreen === 'map' && renderMainMap()}
          {currentScreen === 'places' && renderPlaces()}
          {currentScreen === 'add_place' && renderAddPlace()}
          {currentScreen === 'admin' && renderAdmin()}
        </div>

        BOTTOM_NAV
        
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1.5 bg-slate-300/30 rounded-full z-50 pointer-events-none" />
      </div>
    </div>
  );
}
"""
    
    code = code.replace("PROTOTYPE_NAME", name)
    code = code.replace("BOTTOM_CLASS", bottom_class)
    
    if is_overlay:
        code = code.replace("MENU_BUTTON", """
          <button 
            onClick={() => setCurrentScreen('places')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border shadow-lg border-slate-700 text-white"
          >
            <Menu className="w-5 h-5" />
          </button>
        """)
        code = code.replace("ADMIN_BUTTON", """
          {isAdmin && (
            <button onClick={() => setCurrentScreen('admin')} className="mt-2 w-11 h-11 bg-emerald-900/80 backdrop-blur-md rounded-2xl flex items-center justify-center border border-emerald-700/50 shadow-lg text-emerald-400"><Bug className="w-5 h-5" /></button>
          )}
        """)
        code = code.replace("PLACES_BACK_BUTTON", """
          <button onClick={() => setCurrentScreen('map')} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors">
             <ChevronLeft className="w-6 h-6 text-slate-300" />
          </button>
        """)
        code = code.replace("ADMIN_HEADER", """
        <div className="flex items-center gap-4">
          <button onClick={() => setCurrentScreen('map')} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors">
             <ChevronLeft className="w-6 h-6 text-slate-300" />
          </button>
          <h1 className="text-xl font-bold text-emerald-400 tracking-tight flex items-center gap-2 m-0">
            <Database className="w-5 h-5" /> Admin Console
          </h1>
        </div>
        """)
        code = code.replace("BOTTOM_NAV", "")
    else:
        code = code.replace("MENU_BUTTON", "")
        code = code.replace("ADMIN_BUTTON", "")
        code = code.replace("PLACES_BACK_BUTTON", "")
        code = code.replace("ADMIN_HEADER", """
        <h1 className="text-2xl font-bold text-emerald-400 tracking-tight flex items-center gap-3">
          <Database className="w-6 h-6" /> Admin Console
        </h1>
        """)
        code = code.replace("BOTTOM_NAV", """
        <div className={`h-20 bg-slate-900 border-t border-slate-800 flex items-center justify-around px-4 z-40 relative transition-all duration-500 ${isUIHidden && currentScreen === 'map' ? 'translate-y-24 opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'}`}>
          <button onClick={() => setCurrentScreen('map')} className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'map' ? 'text-blue-400' : 'text-slate-500 hover:text-slate-400'}`}><Map className="w-6 h-6" /><span className="text-[10px] font-bold">Radar</span></button>
          <button onClick={() => setCurrentScreen('places') || setCurrentScreen('add_place')} className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'places' || currentScreen === 'add_place' ? 'text-blue-400' : 'text-slate-500 hover:text-slate-400'}`}><MapPin className="w-6 h-6" /><span className="text-[10px] font-bold">Places</span></button>
          <button onClick={() => setCurrentScreen('admin')} className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'admin' ? 'text-emerald-400' : 'text-slate-500 hover:text-slate-400'}`}><Database className="w-6 h-6" /><span className="text-[10px] font-bold">Admin</span></button>
        </div>
        """)

    return code

top = """\
"use client";

import React, { useState, useEffect } from 'react';
import { Menu, ChevronDown, ChevronUp, ChevronLeft, Activity, AlertCircle, AlertTriangle, BarChart2, Bell, BellOff, Bug, Check, CheckCircle2, ChevronRight, Clock, CloudLightning, CloudRain, Crosshair, Database, Droplets, Gauge, Layers, Map, MapPin, Navigation, Pause, Play, Power, Search, Settings, Shield, ShieldAlert, Sliders, SplitSquareVertical, Star, Sun, Target, Wind, Zap, Plus, Save, BellRing } from 'lucide-react';

type AppScreen = 'map' | 'places' | 'admin' | 'add_place';
type NotificationPolicy = 'always' | 'ask' | 'schedule' | 'silent';
type AdminToolMode = 'none' | 'calibrate' | 'lock';
"""

bottom = """
export default function RadarMockupsPage() {
  return (
    <div className="min-h-screen bg-slate-100 flex flex-col items-center py-12 gap-16">
      <div className="max-w-[1400px] w-full">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Flow 0: Interactive Prototype (Bottom Navigation)</h2>
        <p className="text-slate-500 mb-8">เวอร์ชันดั้งเดิมที่ใช้แถบนำทางด้านล่าง สามารถสลับหน้าและแสดง Timeline แบบมี Forecast (+30m)</p>
        <RadarMockupsPrototype />
      </div>
      <div className="max-w-[1400px] w-full mb-24">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Flow 0.5: Map-Centric (Full-screen Overlay, No Bottom Nav)</h2>
        <p className="text-slate-500 mb-8">เวอร์ชันนี้สามารถซ่อน UI ได้ด้วยการกดพื้นที่ว่างบนแผนที่ (Method 1) หรือปัด/กดที่ปุ่มมุมการ์ดด้านล่างเพื่อพับเก็บ (Method 2 & 3)</p>
        <RadarMockupsOverlayPrototype />
      </div>
    </div>
  );
}
"""

with open('frontend/src/app/radar-mockups/page.tsx', 'w') as f:
    f.write(top + load_template(False) + load_template(True) + bottom)
