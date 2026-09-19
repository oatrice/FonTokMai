import os

with open('frontend/src/app/radar-mockups/page.tsx', 'r') as f:
    content = f.read()

# Extract bottom static part
idx = content.find('export default function RadarMockupsPage')
bottom_part = content[idx:]

top_part = """\
"use client";

import React, { useState, useEffect } from 'react';
import { Menu, ChevronLeft, Activity, AlertCircle, AlertTriangle, BarChart2, Bell, BellOff, Bug, Check, CheckCircle2, ChevronRight, Clock, CloudLightning, CloudRain, Crosshair, Database, Droplets, Gauge, Layers, Map, MapPin, Navigation, Pause, Play, Power, Search, Settings, Shield, ShieldAlert, Sliders, SplitSquareVertical, Star, Sun, Target, Wind, Zap } from 'lucide-react';

type AppScreen = 'map' | 'places' | 'admin';
type NotificationPolicy = 'always' | 'ask' | 'schedule' | 'silent';
type SnoozeDuration = 'active' | '1h' | '4h' | '24h';
type AdminToolMode = 'none' | 'calibrate' | 'lock';

"""

proto_base = """
function RadarMockupsPrototype() {
  const [currentScreen, setCurrentScreen] = useState<AppScreen>('map');
  const [isAdmin, setIsAdmin] = useState(true);

  // --- 1.2 Timeline Scrubbing State ---
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(5);
  const times = ['-25m', '-20m', '-15m', '-10m', '-5m', 'NOW'];

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(() => {
        setFrameIndex((prev) => (prev + 1) % 6);
      }, 1500);
    }
    return () => clearInterval(interval);
  }, [isPlaying]);

  // --- 1.3 Map Control State ---
  const [layerMode, setLayerMode] = useState<'minimal' | 'pro'>('pro');
  const [dataSource, setDataSource] = useState<'TMD' | 'BMA' | 'WINDY'>('TMD');

  // --- 1.1 My Places & Map Interaction State ---
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

  // --- 2. Admin State ---
  const [adminMode, setAdminMode] = useState<AdminToolMode>('none');
  const [mockWeather, setMockWeather] = useState<'clear' | 'rain' | 'storm' | 'offline'>('rain');
  const [overdrive, setOverdrive] = useState(false);
  const [publicAccess, setPublicAccess] = useState(true);

  const goToLocation = (index: number) => {
    setActivePlaceIndex(index);
    setIsOverview(false);
    setShowDropdown(false);
  };

  const nextLocation = () => {
    setActivePlaceIndex((prev) => (prev + 1) % places.length);
    setIsOverview(false);
  };

  const prevLocation = () => {
    setActivePlaceIndex((prev) => (prev - 1 + places.length) % places.length);
    setIsOverview(false);
  };

  // === RENDERERS ===

  const renderMainMap = () => (
    <div className="relative h-full w-full bg-slate-900 overflow-hidden flex flex-col">
      <div 
        className="absolute inset-0 bg-cover transition-all duration-1000 ease-in-out origin-center" 
        style={{ 
          backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/600x800.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')",
          backgroundPosition: isOverview ? 'center' : activePlace.bgPos,
          transform: isOverview ? 'scale(1)' : 'scale(1.5)',
          filter: mockWeather === 'offline' ? 'grayscale(100%) blur(4px)' : 'none'
        }} 
      />
      
      {isOverview ? (
         <div className="absolute inset-0 z-10">
           <div className="absolute top-[45%] left-[45%]"><MapPin className="text-blue-500 w-6 h-6 fill-blue-500/20 animate-bounce" /></div>
           <div className="absolute top-[60%] left-[65%]"><MapPin className="text-emerald-500 w-6 h-6 fill-emerald-500/20" /></div>
           <div className="absolute top-[30%] left-[40%]"><MapPin className="text-purple-500 w-6 h-6 fill-purple-500/20" /></div>
         </div>
      ) : (
         <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 transition-all duration-500">
            <div className="relative">
              <MapPin className="text-blue-500 w-10 h-10 -mt-10 fill-blue-500/20 drop-shadow-lg" />
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-4 h-4 bg-blue-500 rounded-full animate-ping opacity-50" />
            </div>
         </div>
      )}

      {mockWeather !== 'offline' && mockWeather !== 'clear' && (
        <div className="absolute inset-0 flex items-center justify-center opacity-60 transition-opacity duration-500">
           <div className={`w-64 h-64 rounded-full blur-3xl ${mockWeather === 'storm' ? 'bg-red-500' : 'bg-blue-500'} mix-blend-screen opacity-50 animate-pulse`} />
        </div>
      )}

      <div className="absolute top-12 left-4 right-4 flex justify-between items-start z-30">
        
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
                  onClick={() => goToLocation(idx)}
                  className={`w-full text-left px-4 py-3 text-sm font-medium flex items-center justify-between ${activePlaceIndex === idx && !isOverview ? 'bg-blue-500/20 text-blue-400' : 'text-slate-200 hover:bg-slate-700'}`}
                >
                  {place.name}
                  {activePlaceIndex === idx && !isOverview && <CheckCircle2 className="w-4 h-4" />}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <button 
            onClick={() => setIsOverview(!isOverview)}
            className={`w-11 h-11 backdrop-blur-md rounded-2xl flex items-center justify-center border shadow-lg transition-colors ${isOverview ? 'bg-blue-500 text-white border-blue-400' : 'bg-slate-900/90 text-slate-400 border-slate-700'}`}
            title="Overview (Zoom to Bounds)"
          >
            <Crosshair className="w-5 h-5" />
          </button>
          <button 
            onClick={() => setLayerMode(prev => prev === 'minimal' ? 'pro' : 'minimal')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border border-slate-700 shadow-lg text-slate-400"
          >
            <Layers className={`w-5 h-5 ${layerMode === 'pro' ? 'text-emerald-400' : 'text-slate-400'}`} />
          </button>
        </div>
      </div>

      {mockWeather === 'offline' && (
        <div className="absolute top-28 left-4 right-4 z-30 bg-red-500/90 backdrop-blur-md text-white px-4 py-3 rounded-2xl flex items-center gap-3 shadow-xl">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <p className="text-sm font-medium">TMD API Offline. Switching to fallback data.</p>
        </div>
      )}

      <div className="absolute bottom-24 left-4 right-4 z-30">
        <div className="bg-slate-900/85 backdrop-blur-xl border border-slate-700/50 rounded-3xl p-5 shadow-2xl relative overflow-hidden">
          
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-2 text-white font-semibold">
              {!isOverview && (
                <div className="flex gap-1 mr-1">
                  <button onClick={prevLocation} className="p-1 bg-slate-800 rounded-full hover:bg-slate-700"><ChevronRight className="w-4 h-4 rotate-180" /></button>
                  <button onClick={nextLocation} className="p-1 bg-slate-800 rounded-full hover:bg-slate-700"><ChevronRight className="w-4 h-4" /></button>
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
                 <span className="text-blue-400">{times[frameIndex]}</span>
              </div>
              <div className="absolute bottom-1 left-0 right-0 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 transition-all duration-300 ease-linear"
                  style={{ width: `${(frameIndex / 5) * 100}%` }}
                />
              </div>
              <div className="absolute bottom-1 inset-x-0 flex justify-between items-center pointer-events-none px-1">
                {[0, 1, 2, 3, 4, 5].map(i => (
                  <div key={i} className={`w-2.5 h-2.5 rounded-full transition-colors ${i <= frameIndex ? 'bg-white' : 'bg-slate-500'}`} />
                ))}
              </div>
              <input 
                type="range" min="0" max="5" 
                value={frameIndex} 
                onChange={(e) => { setFrameIndex(parseInt(e.target.value)); setIsPlaying(false); }}
                className="absolute bottom-0 inset-x-0 w-full opacity-0 cursor-pointer h-6"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const renderPlaces = () => (
    <div className="h-full w-full bg-[#13171f] overflow-y-auto px-5 pt-16 pb-32">
      <h1 className="text-3xl font-semibold mb-8 text-white tracking-tight">My Places</h1>
      
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
                  <button 
                    onClick={() => {
                      setCurrentScreen('map');
                      goToLocation(idx);
                    }}
                    className="w-full mb-6 py-3 bg-blue-500/20 text-blue-400 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 border border-blue-500/30 hover:bg-blue-500/30 transition-colors"
                  >
                    <Map className="w-4 h-4" />
                    View on Map (Fly-to)
                  </button>

                  <div className="mb-6">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 block">Notification Policy</label>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { id: 'always', label: 'Always Notify', icon: Bell },
                        { id: 'ask', label: 'Always Ask', icon: ShieldAlert },
                        { id: 'schedule', label: 'Schedule', icon: Clock },
                        { id: 'silent', label: 'Silent', icon: BellOff },
                      ].map(pol => (
                        <button key={pol.id} className={`flex items-center gap-2 p-3 rounded-xl border text-sm font-medium transition-colors ${place.policy === pol.id ? 'bg-blue-500/20 border-blue-500/50 text-blue-400' : 'bg-slate-800/50 border-slate-700 text-slate-300'}`}>
                          <pol.icon className="w-4 h-4" />
                          {pol.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 block">Snooze / Mute</label>
                    <div className="flex bg-slate-800/50 rounded-xl p-1 border border-slate-700">
                      {[
                        { id: 'active', label: 'Active' },
                        { id: '1h', label: '1h' },
                        { id: '4h', label: '4h' },
                        { id: '24h', label: '24h' },
                      ].map(snz => (
                        <button key={snz.id} className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-colors ${place.snooze === snz.id ? (snz.id === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400') : 'text-slate-400 hover:text-slate-200'}`}>
                          {snz.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderAdmin = () => (
    <div className="h-full w-full bg-black overflow-y-auto px-5 pt-16 pb-32 text-slate-300 font-mono">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-emerald-400 tracking-tight flex items-center gap-3">
          <Database className="w-6 h-6" />
          Admin Console
        </h1>
        <div className="flex items-center gap-2 text-xs bg-emerald-950/50 text-emerald-500 px-3 py-1 rounded-full border border-emerald-900">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          LIVE
        </div>
      </div>

      <section className="mb-10">
        <h2 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-800 pb-2">DevMock Sandbox</h2>
        <div className="grid grid-cols-2 gap-3 mb-4">
          {[
            { id: 'clear', label: 'Clear Sky', icon: Zap },
            { id: 'rain', label: 'Heavy Rain', icon: CloudLightning },
            { id: 'storm', label: 'Storm', icon: AlertTriangle },
            { id: 'offline', label: 'API Offline', icon: Power },
          ].map(mock => (
            <button 
              key={mock.id}
              onClick={() => { setMockWeather(mock.id as "clear" | "rain" | "storm" | "offline"); setCurrentScreen('map'); }}
              className={`flex flex-col items-center justify-center gap-2 p-4 rounded-2xl border transition-all ${mockWeather === mock.id ? 'bg-emerald-900/30 border-emerald-500/50 text-emerald-400' : 'bg-slate-900 border-slate-800 hover:border-slate-700'}`}
            >
              <mock.icon className="w-6 h-6" />
              <span className="text-xs font-bold">{mock.label}</span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-800 pb-2">System Controls</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between p-5 bg-slate-900 rounded-2xl border border-slate-800">
            <div>
              <div className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Activity className="w-4 h-4 text-orange-500" />
                Emergency Overdrive
              </div>
              <div className="text-xs text-slate-500 mt-1">Bypass GCP budget limits</div>
            </div>
            <button 
              onClick={() => setOverdrive(!overdrive)}
              className={`w-14 h-8 rounded-full transition-colors relative ${overdrive ? 'bg-orange-500' : 'bg-slate-700'}`}
            >
              <div className={`absolute top-1 w-6 h-6 rounded-full bg-white transition-all ${overdrive ? 'left-7' : 'left-1'}`} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
      <div className="w-[400px] h-[850px] bg-black rounded-[50px] border-[12px] border-slate-800 shadow-2xl relative overflow-hidden flex flex-col">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-7 bg-slate-800 rounded-b-3xl z-50" />
        
        <div className="flex-1 relative">
          {currentScreen === 'map' && renderMainMap()}
          {currentScreen === 'places' && renderPlaces()}
          {currentScreen === 'admin' && renderAdmin()}
        </div>

        <div className="h-20 bg-slate-900 border-t border-slate-800 flex items-center justify-around px-4 z-40 relative">
          <button 
            onClick={() => { setCurrentScreen('map'); setAdminMode('none'); }}
            className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'map' ? 'text-blue-400' : 'text-slate-500 hover:text-slate-400'}`}
          >
            <Map className="w-6 h-6" />
            <span className="text-[10px] font-bold">Radar</span>
          </button>
          
          <button 
            onClick={() => { setCurrentScreen('places'); setAdminMode('none'); }}
            className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'places' ? 'text-blue-400' : 'text-slate-500 hover:text-slate-400'}`}
          >
            <MapPin className="w-6 h-6" />
            <span className="text-[10px] font-bold">Places</span>
          </button>

          {isAdmin && (
            <button 
              onClick={() => setCurrentScreen('admin')}
              className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'admin' ? 'text-emerald-400' : 'text-slate-500 hover:text-slate-400'}`}
            >
              <Database className="w-6 h-6" />
              <span className="text-[10px] font-bold">Admin</span>
            </button>
          )}
        </div>
        
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1.5 bg-white/20 rounded-full z-50 pointer-events-none" />
      </div>
    </div>
  );
}
"""

proto_overlay = proto_base.replace('RadarMockupsPrototype', 'RadarMockupsOverlayPrototype')
proto_overlay = proto_overlay.replace('className="absolute bottom-24 left-4 right-4 z-30"', 'className="absolute bottom-10 left-4 right-4 z-30"')

# Remove bottom nav from overlay proto
proto_overlay = proto_overlay.replace("""
        <div className="h-20 bg-slate-900 border-t border-slate-800 flex items-center justify-around px-4 z-40 relative">
          <button 
            onClick={() => { setCurrentScreen('map'); setAdminMode('none'); }}
            className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'map' ? 'text-blue-400' : 'text-slate-500 hover:text-slate-400'}`}
          >
            <Map className="w-6 h-6" />
            <span className="text-[10px] font-bold">Radar</span>
          </button>
          
          <button 
            onClick={() => { setCurrentScreen('places'); setAdminMode('none'); }}
            className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'places' ? 'text-blue-400' : 'text-slate-500 hover:text-slate-400'}`}
          >
            <MapPin className="w-6 h-6" />
            <span className="text-[10px] font-bold">Places</span>
          </button>

          {isAdmin && (
            <button 
              onClick={() => setCurrentScreen('admin')}
              className={`flex flex-col items-center gap-1.5 p-2 transition-colors ${currentScreen === 'admin' ? 'text-emerald-400' : 'text-slate-500 hover:text-slate-400'}`}
            >
              <Database className="w-6 h-6" />
              <span className="text-[10px] font-bold">Admin</span>
            </button>
          )}
        </div>""", "")

# Replace main map top UI for overlay
overlay_top_ui = """
      <div className="absolute top-12 left-4 right-4 flex justify-between items-start z-30">
        
        <div className="flex items-center gap-2">
          <button 
            onClick={() => setCurrentScreen('places')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border shadow-lg border-slate-700 text-white"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="relative">
"""
proto_overlay = proto_overlay.replace("""
      <div className="absolute top-12 left-4 right-4 flex justify-between items-start z-30">
        
        <div className="relative">
""", overlay_top_ui.strip('\n'))

# Fix the end of the top-left section
overlay_top_ui_end = """
            </div>
          )}
        </div>
        </div>

        <div className="flex flex-col gap-2">
"""
proto_overlay = proto_overlay.replace("""
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2">
""", overlay_top_ui_end.strip('\n'))

# Add secret admin button to the right
overlay_right_buttons = """
          <button 
            onClick={() => setLayerMode(prev => prev === 'minimal' ? 'pro' : 'minimal')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border border-slate-700 shadow-lg text-slate-400"
          >
            <Layers className={`w-5 h-5 ${layerMode === 'pro' ? 'text-emerald-400' : 'text-slate-400'}`} />
          </button>
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
proto_overlay = proto_overlay.replace("""
          <button 
            onClick={() => setLayerMode(prev => prev === 'minimal' ? 'pro' : 'minimal')}
            className="w-11 h-11 bg-slate-900/90 backdrop-blur-md rounded-2xl flex items-center justify-center border border-slate-700 shadow-lg text-slate-400"
          >
            <Layers className={`w-5 h-5 ${layerMode === 'pro' ? 'text-emerald-400' : 'text-slate-400'}`} />
          </button>
        </div>
""", overlay_right_buttons.strip('\n'))

# Add back buttons
places_overlay = """
    <div className="h-full w-full bg-[#13171f] overflow-y-auto px-5 pt-16 pb-32">
      <div className="flex items-center gap-4 mb-8">
        <button onClick={() => setCurrentScreen('map')} className="p-2 bg-slate-800 rounded-full hover:bg-slate-700 transition-colors">
           <ChevronLeft className="w-6 h-6 text-slate-300" />
        </button>
        <h1 className="text-3xl font-semibold text-white tracking-tight m-0">My Places</h1>
      </div>
"""
proto_overlay = proto_overlay.replace("""
    <div className="h-full w-full bg-[#13171f] overflow-y-auto px-5 pt-16 pb-32">
      <h1 className="text-3xl font-semibold mb-8 text-white tracking-tight">My Places</h1>
""", places_overlay.strip('\n'))

admin_overlay = """
    <div className="h-full w-full bg-black overflow-y-auto px-5 pt-16 pb-32 text-slate-300 font-mono">
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
"""
proto_overlay = proto_overlay.replace("""
    <div className="h-full w-full bg-black overflow-y-auto px-5 pt-16 pb-32 text-slate-300 font-mono">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-emerald-400 tracking-tight flex items-center gap-3">
          <Database className="w-6 h-6" />
          Admin Console
        </h1>
""", admin_overlay.strip('\n'))


new_flows_injection = """
      {/* ======================= FLOW 0.5: MAP-CENTRIC PROTOTYPE ======================= */}
      <div className="max-w-[1400px] w-full mb-24">
        <h2 className="text-2xl font-bold text-slate-800 mb-2 border-b-2 border-slate-200 pb-2">Flow 0.5: Map-Centric (Full-screen Overlay, No Bottom Nav)</h2>
        <p className="text-slate-500 mb-8">เวอร์ชันนี้ซ่อนแท็บด้านล่างทิ้งเพื่อให้แผนที่เต็มจอ และใช้ปุ่ม Menu ซ้ายบนในการเปิดหน้าต่าง Places แบบเต็มจอ รวมถึงซ่อนโหมด Admin ไว้หลังไอคอน Bug ขวาบน (เป็นเพียงแนวคิดทดสอบ)</p>
        <RadarMockupsOverlayPrototype />
      </div>
"""

bottom_part = bottom_part.replace('{/* ======================= FLOW 1: LOCATION SETUP ======================= */}', new_flows_injection + '\n      {/* ======================= FLOW 1: LOCATION SETUP ======================= */}')

full_content = top_part + proto_base + "\n" + proto_overlay + "\n" + bottom_part

with open('frontend/src/app/radar-mockups/page.tsx', 'w') as f:
    f.write(full_content)
