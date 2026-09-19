'use client';

import React, { useState, useEffect } from 'react';
import { Menu, ChevronDown, ChevronUp, ChevronLeft, Activity, AlertCircle, AlertTriangle, BarChart2, Bell, BellOff, Bug, Check, CheckCircle2, ChevronRight, Clock, CloudLightning, CloudRain, Crosshair, Database, Droplets, Gauge, Layers, Map, MapPin, Navigation, Pause, Play, Power, Search, Settings, Shield, ShieldAlert, Sliders, SplitSquareVertical, Star, Sun, Target, Wind, Zap, Plus, Save, BellRing } from 'lucide-react';

type AppScreen = 'map' | 'places' | 'admin' | 'add_place';
type NotificationPolicy = 'always' | 'ask' | 'schedule' | 'silent';
type AdminToolMode = 'none' | 'calibrate' | 'lock';


function RadarMockupsPrototype() {
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
          
        </div>
      </div>

      <div className={`absolute bottom-24 left-4 right-4 z-30 transition-all duration-500 ${isUIHidden ? 'translate-y-32 opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'}`}>
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
        
        <h1 className="text-2xl font-bold text-emerald-400 tracking-tight flex items-center gap-3">
          <Database className="w-6 h-6" /> Admin Console
        </h1>
        
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

        
        <div className={`h-20 bg-slate-900 border-t border-slate-800 flex items-center justify-around px-4 z-40 relative transition-all duration-500 ${isUIHidden && currentScreen === 'map' ? 'translate-y-24 opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'}`}>
          <button onClick={() => setCurrentScreen('map')} className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'map' ? 'text-blue-400' : 'text-slate-500 hover:text-slate-400'}`}><Map className="w-6 h-6" /><span className="text-[10px] font-bold">Radar</span></button>
          <button onClick={() => setCurrentScreen('places') || setCurrentScreen('add_place')} className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'places' || currentScreen === 'add_place' ? 'text-blue-400' : 'text-slate-500 hover:text-slate-400'}`}><MapPin className="w-6 h-6" /><span className="text-[10px] font-bold">Places</span></button>
          <button onClick={() => setCurrentScreen('admin')} className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'admin' ? 'text-emerald-400' : 'text-slate-500 hover:text-slate-400'}`}><Database className="w-6 h-6" /><span className="text-[10px] font-bold">Admin</span></button>
        </div>
        
        
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1.5 bg-slate-300/30 rounded-full z-50 pointer-events-none" />
      </div>
    </div>
  );
}

function RadarMockupsOverlayPrototype() {
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
          
          <button 
            onClick={() => setCurrentScreen('places')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border shadow-lg border-slate-700 text-white"
          >
            <Menu className="w-5 h-5" />
          </button>
        
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
          
          {isAdmin && (
            <button onClick={() => setCurrentScreen('admin')} className="mt-2 w-11 h-11 bg-emerald-900/80 backdrop-blur-md rounded-2xl flex items-center justify-center border border-emerald-700/50 shadow-lg text-emerald-400"><Bug className="w-5 h-5" /></button>
          )}
        
        </div>
      </div>

      <div className={`absolute bottom-6 left-4 right-4 z-30 transition-all duration-500 ${isUIHidden ? 'translate-y-32 opacity-0 pointer-events-none' : 'translate-y-0 opacity-100'}`}>
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
          
          <button onClick={() => setCurrentScreen('map')} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors">
             <ChevronLeft className="w-6 h-6 text-slate-300" />
          </button>
        
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
        
        <div className="flex items-center gap-4">
          <button onClick={() => setCurrentScreen('map')} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors">
             <ChevronLeft className="w-6 h-6 text-slate-300" />
          </button>
          <h1 className="text-xl font-bold text-emerald-400 tracking-tight flex items-center gap-2 m-0">
            <Database className="w-5 h-5" /> Admin Console
          </h1>
        </div>
        
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

        
        
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1.5 bg-slate-300/30 rounded-full z-50 pointer-events-none" />
      </div>
    </div>
  );
}


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

  // Admin Debug Viewer State
  const [debugMode, setDebugMode] = useState<'split' | 'pip'>('split');
  const [adminViewMode, setAdminViewMode] = useState<'latest' | '6frames'>('latest');
  const [selectedFrame, setSelectedFrame] = useState<number | null>(null);
  const [expandStyle, setExpandStyle] = useState<'half' | 'full'>('full');

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
      <div className="max-w-[1400px] w-full mb-10 flex flex-col items-center">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Step 3: Admin Debug Mode (Interactive)</h2>
        <p className="text-slate-500 mb-6">คลิกปุ่มด้านล่างเพื่อสลับโหมดการทำงานและดูภาพ 6 Frames ย้อนหลัง</p>
        
        <div className="flex flex-wrap justify-center gap-6 mb-10 bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
          <div className="flex flex-col gap-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest pl-2">Layout Mode</span>
            <div className="flex bg-slate-100 p-1 rounded-xl">
              <button 
                onClick={() => setDebugMode('split')}
                className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center gap-2 ${debugMode === 'split' ? 'bg-white text-rose-600 shadow-sm border border-slate-200/50' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'}`}
              >
                <SplitSquareVertical className="w-4 h-4" /> Split Screen
              </button>
              <button 
                onClick={() => setDebugMode('pip')}
                className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center gap-2 ${debugMode === 'pip' ? 'bg-white text-orange-600 shadow-sm border border-slate-200/50' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'}`}
              >
                <Bug className="w-4 h-4" /> PiP Overlay
              </button>
            </div>
          </div>
          
          <div className="w-px bg-slate-200 mx-2 hidden sm:block"></div>

          <div className="flex flex-col gap-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest pl-2">Data View</span>
            <div className="flex bg-slate-100 p-1 rounded-xl">
              <button 
                onClick={() => setAdminViewMode('latest')}
                className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center gap-2 ${adminViewMode === 'latest' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'}`}
              >
                Radar Latest
              </button>
              <button 
                onClick={() => setAdminViewMode('6frames')}
                className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all flex items-center gap-2 ${adminViewMode === '6frames' ? 'bg-indigo-600 text-white shadow-md' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'}`}
              >
                6 Frames Analysis
              </button>
            </div>
          </div>
        </div>
        
        <div className="flex justify-center transition-all duration-500 min-h-[850px]">
          
          {debugMode === 'split' && (
            <div className="flex flex-col items-center animate-in fade-in zoom-in-95 duration-300">
              <h3 className="text-md font-semibold mb-3 text-rose-500 flex items-center gap-2">
                <SplitSquareVertical className="w-5 h-5" /> Split Screen Debug
              </h3>
              
              <div className="w-[375px] h-[812px] bg-slate-900 rounded-[40px] border-[8px] border-rose-900 overflow-hidden relative shadow-2xl flex flex-col">
                
                {/* IN-APP ADMIN TOGGLE */}
                <div className="absolute top-12 left-1/2 -translate-x-1/2 z-50 bg-black/60 backdrop-blur-md p-1 rounded-full flex border border-slate-700/50 shadow-xl">
                  <button onClick={() => setDebugMode('split')} className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${debugMode === 'split' ? 'bg-rose-500 text-white shadow-md' : 'text-slate-300 hover:text-white'}`}>SPLIT</button>
                  <button onClick={() => setDebugMode('pip')} className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${debugMode === 'pip' ? 'bg-orange-500 text-white shadow-md' : 'text-slate-300 hover:text-white'}`}>PIP</button>
                </div>

                {/* NATIVE VECTOR HALF */}
                <div className="h-[45%] relative bg-slate-800 w-full overflow-hidden">
                  <div className="absolute inset-0 bg-cover bg-center opacity-40" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                  <div className="absolute top-2 left-2 bg-blue-500/20 text-blue-400 border border-blue-500/50 px-2 py-0.5 rounded text-[10px] font-bold z-10">NATIVE VECTOR RENDER</div>
                  
                  {/* Dynamic render based on adminViewMode */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 z-10">
                    <div className="absolute inset-0 rounded-full border-2 border-amber-400 bg-amber-500/10 transition-transform duration-500" style={{ transform: adminViewMode === '6frames' ? `scale(${1 + frameIndex * 0.05})` : 'scale(1)' }}></div>
                    {adminViewMode === '6frames' && (
                      <>
                        <div className="absolute top-1/4 left-1/4 w-16 h-16 rounded-full border border-blue-400/40 bg-blue-500/10"></div>
                        <div className="absolute bottom-1/4 right-1/4 w-20 h-20 rounded-full border border-rose-400/40 bg-rose-500/10"></div>
                      </>
                    )}
                    <svg className="absolute top-1/2 left-1/2 w-48 h-48 overflow-visible" style={{ transform: 'translate(-10px, -10px)' }}>
                       <path d="M 0 0 L 80 -40" fill="none" stroke="#3b82f6" strokeWidth="2" strokeDasharray="4 2" />
                       {adminViewMode === '6frames' && <path d="M 0 0 L -60 30" fill="none" stroke="#f43f5e" strokeWidth="2" strokeDasharray="4 2" />}
                    </svg>
                  </div>
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center z-20">
                    <MapPin className="w-6 h-6 text-white drop-shadow-md" fill="#3b82f6" />
                  </div>
                  
                  {adminViewMode === '6frames' && (
                    <div className="absolute bottom-3 left-3 bg-slate-900/80 px-3 py-2 rounded-xl border border-slate-700 flex items-center gap-3 backdrop-blur-sm z-20">
                       <span className="text-[10px] font-bold text-slate-300">NATIVE SYNC:</span>
                       <div className="h-2 w-24 bg-slate-800 rounded-full overflow-hidden border border-slate-600">
                          <div className="h-full bg-blue-500 transition-all duration-300 ease-linear" style={{ width: `${progressPercent}%` }}></div>
                       </div>
                       <span className="text-xs font-mono text-blue-400">{times[frameIndex]}</span>
                    </div>
                  )}
                </div>

                {/* DRAG HANDLE */}
                <div className="h-6 bg-slate-950 flex items-center justify-center border-y border-slate-800 cursor-row-resize z-30 shadow-[0_0_10px_rgba(0,0,0,0.5)] relative">
                   <div className="w-12 h-1 rounded-full bg-slate-700"></div>
                   <div className="absolute right-2 text-[8px] font-bold text-slate-600">DRAG</div>
                </div>

                {/* BOT STATIC HALF */}
                <div className="flex-1 bg-black relative w-full overflow-hidden flex flex-col">
                  <div className="absolute top-2 left-2 bg-slate-700 text-white px-2 py-0.5 rounded text-[10px] font-bold z-10 shadow-md">
                    {adminViewMode === 'latest' ? 'BOT STATIC IMAGE (JPG)' : 'BOT 6-FRAMES GRID (TAP TO EXPAND)'}
                  </div>
                  <div className="flex-1 flex items-center justify-center p-4 pt-10">
                    {adminViewMode === 'latest' ? (
                      // Latest Image View
                      <div className="w-full aspect-[4/5] bg-slate-800 rounded-xl overflow-hidden border border-slate-700 shadow-xl relative flex items-center justify-center group">
                        <div className="absolute inset-0 bg-[url('https://api.maptiler.com/maps/streets-v2/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')] opacity-50 bg-cover"></div>
                        <div className="absolute inset-0 flex items-center justify-center mix-blend-screen opacity-80">
                          <div className="w-48 h-48 bg-[radial-gradient(circle,#f00_0%,#ff0_30%,transparent_60%)] filter blur-[2px] opacity-80"></div>
                        </div>
                        <div className="absolute bottom-3 left-3 bg-black/80 text-[10px] text-white px-2 py-1.5 rounded-lg font-mono border border-slate-700 backdrop-blur-sm">
                          radar_latest.jpg<br/><span className="text-slate-400">14:20:00</span>
                        </div>
                        <div className="absolute inset-0 border-2 border-indigo-500/0 group-hover:border-indigo-500/50 rounded-xl transition-colors pointer-events-none"></div>
                      </div>
                    ) : (
                      // 6 Frames View (Grid layout representing analysis)
                      <div className="w-full h-full grid grid-cols-2 grid-rows-3 gap-3 p-1">
                         {[1, 2, 3, 4, 5, 6].map((num) => (
                           <div 
                             key={num} 
                             onClick={() => setSelectedFrame(num)}
                             className={`cursor-pointer hover:scale-[1.02] bg-slate-800 rounded-lg overflow-hidden relative border flex items-center justify-center transition-all ${frameIndex === num - 1 ? 'border-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.3)]' : 'border-slate-700 hover:border-slate-500'}`}
                           >
                             <div className="absolute inset-0 bg-[url('https://api.maptiler.com/maps/streets-v2/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')] opacity-40 bg-cover"></div>
                             <div className="absolute inset-0 flex items-center justify-center mix-blend-screen opacity-80 pointer-events-none">
                               <div className="w-24 h-24 bg-[radial-gradient(circle,#f00_0%,#ff0_30%,transparent_60%)] filter blur-[2px]" style={{ transform: `scale(${0.4 + num * 0.1})` }}></div>
                             </div>
                             <div className={`absolute top-2 left-2 text-[10px] px-1.5 py-0.5 font-mono rounded pointer-events-none ${frameIndex === num - 1 ? 'bg-indigo-600 text-white' : 'bg-black/70 text-slate-300'}`}>
                               {times[num - 1]}
                             </div>
                           </div>
                         ))}
                      </div>
                    )}
                  </div>
                  <div className="h-16 bg-slate-900 border-t border-slate-800 flex items-center justify-between px-6 z-20">
                    <span className="text-xs font-semibold text-slate-400">Render Source:</span>
                    <span className="text-sm font-mono text-emerald-400 font-bold bg-emerald-950/50 px-3 py-1 rounded border border-emerald-900/50">
                      {adminViewMode === 'latest' ? 'S3: radar_latest.jpg' : 'S3: radar_analysis_6frames'}
                    </span>
                  </div>
                </div>

                {/* EXPANDED FRAME VIEW OVERLAY */}
                {selectedFrame !== null && adminViewMode === '6frames' && (
                  <div className={`absolute left-0 right-0 top-0 z-50 bg-slate-950 flex flex-col transition-all duration-300 ${expandStyle === 'full' ? 'bottom-0 h-full' : 'h-[45%] border-b-2 border-indigo-500 shadow-xl'}`}>
                     <div className="flex items-center justify-between p-4 bg-gradient-to-b from-black/80 to-transparent z-10 absolute top-0 left-0 right-0 pt-12">
                       <div className="bg-indigo-600 text-white text-[10px] px-2 py-1 rounded font-mono shadow-md border border-indigo-500/50">FRAME: {times[selectedFrame - 1]}</div>
                       <div className="flex gap-2">
                         <button 
                           onClick={(e) => { e.stopPropagation(); setExpandStyle(expandStyle === 'full' ? 'half' : 'full'); }} 
                           className="bg-black/60 backdrop-blur border border-slate-600 text-white text-[10px] px-3 py-1.5 rounded-full hover:bg-slate-800 transition-colors"
                         >
                           {expandStyle === 'full' ? 'ย่อครึ่งจอ (Half)' : 'เต็มจอ (Full)'}
                         </button>
                         <button 
                           onClick={(e) => { e.stopPropagation(); setSelectedFrame(null); }} 
                           className="bg-rose-500 text-white w-7 h-7 rounded-full flex items-center justify-center hover:bg-rose-600 transition-colors shadow-md"
                         >✕</button>
                       </div>
                     </div>
                     <div className="flex-1 w-full bg-[url('https://api.maptiler.com/maps/streets-v2/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')] bg-cover bg-center relative flex items-center justify-center">
                        <div className="absolute inset-0 bg-black/20"></div>
                        <div className="absolute inset-0 flex items-center justify-center mix-blend-screen opacity-90">
                          <div className="w-64 h-64 bg-[radial-gradient(circle,#f00_0%,#ff0_30%,transparent_60%)] filter blur-[2px]" style={{ transform: `scale(${0.4 + selectedFrame * 0.1})` }}></div>
                        </div>
                     </div>
                     {expandStyle === 'full' && (
                       <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-black/80 px-4 py-2 rounded-full text-xs text-white backdrop-blur border border-slate-700/50 pointer-events-none">
                         Bot Static Image Review
                       </div>
                     )}
                  </div>
                )}
              </div>
            </div>
          )}

          {debugMode === 'pip' && (
            <div className="flex flex-col items-center animate-in fade-in zoom-in-95 duration-300">
              <h3 className="text-md font-semibold mb-3 text-orange-500 flex items-center gap-2">
                <Bug className="w-5 h-5" /> PiP Overlay Debug
              </h3>
              
              <div className="w-[375px] h-[812px] bg-slate-100 rounded-[40px] border-[8px] border-orange-500/50 overflow-hidden relative shadow-2xl flex flex-col">
                
                {/* IN-APP ADMIN TOGGLE */}
                <div className="absolute top-12 left-1/2 -translate-x-1/2 z-50 bg-black/60 backdrop-blur-md p-1 rounded-full flex border border-slate-700/50 shadow-xl">
                  <button onClick={() => setDebugMode('split')} className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${debugMode === 'split' ? 'bg-rose-500 text-white shadow-md' : 'text-slate-300 hover:text-white'}`}>SPLIT</button>
                  <button onClick={() => setDebugMode('pip')} className={`px-4 py-1.5 rounded-full text-[10px] font-bold transition-all ${debugMode === 'pip' ? 'bg-orange-500 text-white shadow-md' : 'text-slate-300 hover:text-white'}`}>PIP</button>
                </div>

                <div className="flex-1 relative bg-slate-200 w-full overflow-hidden">
                  <div className="absolute inset-0 bg-cover bg-center opacity-70" style={{ backgroundImage: "url('https://api.maptiler.com/maps/dataviz-light/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')" }} />
                  
                  <div className="absolute top-1/3 left-1/3 w-32 h-32 z-10">
                    <div className="absolute inset-0 rounded-full border-2 border-orange-400 bg-transparent transition-transform duration-500" style={{ transform: adminViewMode === '6frames' ? `scale(${1 + frameIndex * 0.05})` : 'scale(1)' }}></div>
                    <svg className="absolute top-1/2 left-1/2 w-48 h-48 overflow-visible" style={{ transform: 'translate(-10px, -10px)' }}>
                       <path d="M 0 0 L 80 -40" fill="none" stroke="#f97316" strokeWidth="2" strokeDasharray="4 2" />
                    </svg>
                  </div>
                  <div className="absolute top-1/3 left-1/3 flex flex-col items-center z-20" style={{ transform: 'translate(-12px, -12px)' }}>
                    <MapPin className="w-6 h-6 text-orange-500 drop-shadow-md" fill="#ffffff" />
                  </div>
                  
                  {/* PIP WINDOW (STATIC BOT IMAGE OVERLAY) */}
                  <div className="absolute bottom-32 right-4 w-[160px] shadow-2xl rounded-xl border-2 border-orange-500 overflow-hidden z-40 transform transition-transform hover:scale-105 origin-bottom-right bg-black flex flex-col">
                     <div className="bg-orange-500 text-black text-[10px] font-bold flex justify-between px-3 py-2 items-center">
                       <span>{adminViewMode === 'latest' ? 'BOT STATIC' : '6-FRAMES'}</span>
                       <button className="opacity-60 hover:opacity-100 transition-opacity">✕</button>
                     </div>
                     <div className="w-full aspect-[4/5] bg-[url('https://api.maptiler.com/maps/streets-v2/static/100.50,13.75,11/400x500.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')] bg-cover relative flex items-center justify-center p-1.5 bg-slate-900">
                        {adminViewMode === 'latest' ? (
                          <div className="absolute inset-0 flex items-center justify-center mix-blend-screen opacity-90">
                            <div className="w-24 h-24 bg-[radial-gradient(circle,#f00_0%,#ff0_30%,transparent_60%)] filter blur-[1px]"></div>
                          </div>
                        ) : (
                          <div className="w-full h-full grid grid-cols-2 grid-rows-3 gap-1">
                            {[1, 2, 3, 4, 5, 6].map((num) => (
                              <div key={num} className={`bg-slate-800 rounded overflow-hidden relative flex items-center justify-center transition-colors ${frameIndex === num - 1 ? 'border border-indigo-400' : ''}`}>
                                <div className="absolute inset-0 bg-[radial-gradient(circle,#f00_0%,#ff0_30%,transparent_60%)] filter blur-[0.5px] mix-blend-screen opacity-90" style={{ transform: `scale(${0.4 + num * 0.1})` }}></div>
                              </div>
                            ))}
                          </div>
                        )}
                     </div>
                  </div>
                </div>
                
                {/* BOTTOM SHEET */}
                <div className="bg-white rounded-t-3xl border-t border-slate-200 relative z-30 shadow-[0_-10px_30px_rgba(0,0,0,0.08)] flex flex-col pb-6">
                  <div className="w-full pt-3 pb-2 flex justify-center cursor-pointer">
                    <div className="w-12 h-1.5 rounded-full bg-slate-200"></div>
                  </div>
                  <div className="px-6 flex items-center justify-between mt-2">
                     <div>
                       <h3 className="font-bold text-xl text-slate-900">Admin Mode</h3>
                       <p className="text-xs text-slate-500 mt-1 font-mono">{adminViewMode === 'latest' ? 'Sync: radar_latest.jpg' : 'Sync: 6 frames animation'}</p>
                     </div>
                     <button onClick={() => setDebugMode('split')} className="w-12 h-12 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center border border-orange-200 hover:bg-orange-200 transition-colors shadow-sm">
                        <Bug className="w-6 h-6" />
                     </button>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>


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
    </div>
  );
}
