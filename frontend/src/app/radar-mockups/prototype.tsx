'use client';

import React, { useState, useEffect } from 'react';
import { 
  Map, MapPin, Layers, Play, Pause, Bell, BellOff, Settings, AlertTriangle, 
  Crosshair, Activity, ShieldAlert, Sliders, Database, Search, ChevronRight,
  Clock, CheckCircle2, Zap, CloudLightning, Shield, Power, Gauge, Target
} from 'lucide-react';

type AppScreen = 'map' | 'places' | 'admin';
type NotificationPolicy = 'always' | 'ask' | 'schedule' | 'silent';
type SnoozeDuration = 'active' | '1h' | '4h' | '24h';
type AdminToolMode = 'none' | 'calibrate' | 'lock';

export default function RadarMockupsPrototype() {
  const [currentScreen, setCurrentScreen] = useState<AppScreen>('map');
  const [isAdmin, setIsAdmin] = useState(true); // Default true for testing

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

  // --- 1.1 My Places State ---
  const [expandedPlace, setExpandedPlace] = useState<string | null>('home');
  const places = [
    { id: 'home', name: 'บ้าน', address: 'บางนา, กรุงเทพฯ', policy: 'always', snooze: 'active' },
    { id: 'work', name: 'ที่ทำงาน', address: 'สาทร, กรุงเทพฯ', policy: 'schedule', snooze: '1h' },
  ];

  // --- 2. Admin State ---
  const [adminMode, setAdminMode] = useState<AdminToolMode>('none');
  const [mockWeather, setMockWeather] = useState<'clear' | 'rain' | 'storm' | 'offline'>('rain');
  const [overdrive, setOverdrive] = useState(false);
  const [publicAccess, setPublicAccess] = useState(true);

  // === RENDERERS ===

  const renderMainMap = () => (
    <div className="relative h-full w-full bg-slate-900 overflow-hidden flex flex-col">
      {/* Background Map Simulation */}
      <div 
        className="absolute inset-0 bg-cover bg-center opacity-40 transition-all duration-700" 
        style={{ 
          backgroundImage: "url('https://api.maptiler.com/maps/dataviz-dark/static/100.50,13.75,11/600x800.png?key=get_your_own_OpIi9ZULNHzrESv6T2vL')",
          filter: mockWeather === 'offline' ? 'grayscale(100%) blur(4px)' : 'none'
        }} 
      />
      
      {/* Radar Overlay Simulation */}
      {mockWeather !== 'offline' && mockWeather !== 'clear' && (
        <div className={`absolute inset-0 flex items-center justify-center opacity-60 transition-opacity duration-500`}>
           <div className={`w-64 h-64 rounded-full blur-3xl ${mockWeather === 'storm' ? 'bg-red-500' : 'bg-blue-500'} mix-blend-screen opacity-50 animate-pulse`} />
        </div>
      )}

      {/* Admin Visual Tools Overlay */}
      {currentScreen === 'map' && adminMode === 'calibrate' && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-black/40 pointer-events-none">
          <div className="w-48 h-48 rounded-full border-4 border-dashed border-yellow-400 flex items-center justify-center pointer-events-auto cursor-move">
            <div className="w-4 h-4 bg-yellow-400 rounded-full" />
          </div>
          <p className="text-yellow-400 font-mono text-xs mt-4 bg-black/60 px-3 py-1 rounded-full">Drag to set center & scale</p>
        </div>
      )}

      {currentScreen === 'map' && adminMode === 'lock' && (
        <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-auto cursor-crosshair">
          <Crosshair className="w-12 h-12 text-red-500 opacity-50 animate-pulse" />
          <p className="absolute top-1/4 text-red-400 font-mono text-sm bg-black/60 px-4 py-2 rounded-full">Tap anywhere to Force Lock target</p>
        </div>
      )}

      {/* Top Floating Controls */}
      <div className="absolute top-12 left-4 right-4 flex justify-between items-start z-30">
        <div className="bg-slate-800/80 backdrop-blur-md rounded-2xl p-1 flex shadow-lg border border-slate-700/50">
          {(['TMD', 'BMA', 'WINDY'] as const).map(src => (
            <button 
              key={src}
              onClick={() => setDataSource(src)}
              className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-colors ${dataSource === src ? 'bg-blue-500 text-white shadow-sm' : 'text-slate-400 hover:text-white'}`}
            >
              {src}
            </button>
          ))}
        </div>
        
        <button 
          onClick={() => setLayerMode(prev => prev === 'minimal' ? 'pro' : 'minimal')}
          className="bg-slate-800/80 backdrop-blur-md w-10 h-10 rounded-2xl flex items-center justify-center border border-slate-700/50 shadow-lg"
        >
          <Layers className={`w-5 h-5 ${layerMode === 'pro' ? 'text-blue-400' : 'text-slate-400'}`} />
        </button>
      </div>

      {/* Warning Toast */}
      {mockWeather === 'offline' && (
        <div className="absolute top-28 left-4 right-4 z-30 bg-red-500/90 backdrop-blur-md text-white px-4 py-3 rounded-2xl flex items-center gap-3 shadow-xl">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <p className="text-sm font-medium">TMD API Offline. Switching to fallback data.</p>
        </div>
      )}

      {/* Bottom Timeline Scrubber */}
      <div className="absolute bottom-24 left-4 right-4 z-30">
        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-3xl p-5 shadow-2xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              Radar Timeline
            </h3>
            <span className="text-blue-400 font-mono font-bold">{times[frameIndex]}</span>
          </div>
          
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setIsPlaying(!isPlaying)}
              className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 shadow-lg transition-colors ${isPlaying ? 'bg-amber-500/20 text-amber-500' : 'bg-blue-600 text-white'}`}
            >
              {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-1" />}
            </button>

            <div className="flex-1 relative flex items-center h-8">
              <div className="absolute left-0 right-0 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 transition-all duration-300 ease-linear"
                  style={{ width: `${(frameIndex / 5) * 100}%` }}
                />
              </div>
              <div className="absolute inset-0 flex justify-between items-center pointer-events-none px-1">
                {[0, 1, 2, 3, 4, 5].map(i => (
                  <div key={i} className={`w-2.5 h-2.5 rounded-full transition-colors ${i <= frameIndex ? 'bg-white' : 'bg-slate-500'}`} />
                ))}
              </div>
              <input 
                type="range" min="0" max="5" 
                value={frameIndex} 
                onChange={(e) => { setFrameIndex(parseInt(e.target.value)); setIsPlaying(false); }}
                className="absolute inset-0 w-full opacity-0 cursor-pointer"
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
        {places.map(place => {
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
                  {/* Notification Policy */}
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

                  {/* Snooze Options */}
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
      
      <button className="mt-6 w-full py-4 rounded-2xl border-2 border-dashed border-slate-700 text-slate-400 font-semibold hover:border-slate-500 hover:text-slate-300 transition-colors">
        + Add New Location
      </button>
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

      {/* DevMock Sandbox */}
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

      {/* Visual Tools */}
      <section className="mb-10">
        <h2 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4 border-b border-slate-800 pb-2">Map Tools</h2>
        <div className="space-y-3">
          <button 
            onClick={() => { setAdminMode('calibrate'); setCurrentScreen('map'); }}
            className="w-full flex items-center justify-between p-4 bg-slate-900 rounded-2xl border border-slate-800 hover:border-blue-500/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Crosshair className="w-5 h-5 text-blue-400" />
              <div className="text-left">
                <div className="font-bold text-sm text-slate-200">Visual Calibration</div>
                <div className="text-xs text-slate-500">Drag to tune radar bounds</div>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-600" />
          </button>
          
          <button 
            onClick={() => { setAdminMode('lock'); setCurrentScreen('map'); }}
            className="w-full flex items-center justify-between p-4 bg-slate-900 rounded-2xl border border-slate-800 hover:border-red-500/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Target className="w-5 h-5 text-red-400" />
              <div className="text-left">
                <div className="font-bold text-sm text-slate-200">Force Target Lock</div>
                <div className="text-xs text-slate-500">Tap map to lock tracking</div>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-slate-600" />
          </button>
        </div>
      </section>

      {/* Kill Switches */}
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

          <div className="flex items-center justify-between p-5 bg-slate-900 rounded-2xl border border-slate-800">
            <div>
              <div className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue-500" />
                Public Access
              </div>
              <div className="text-xs text-slate-500 mt-1">Allow incoming requests</div>
            </div>
            <button 
              onClick={() => setPublicAccess(!publicAccess)}
              className={`w-14 h-8 rounded-full transition-colors relative ${publicAccess ? 'bg-blue-500' : 'bg-red-500'}`}
            >
              <div className={`absolute top-1 w-6 h-6 rounded-full bg-white transition-all ${publicAccess ? 'left-7' : 'left-1'}`} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8">
      {/* Mobile Device Frame */}
      <div className="w-[400px] h-[850px] bg-black rounded-[50px] border-[12px] border-slate-800 shadow-2xl relative overflow-hidden flex flex-col">
        
        {/* Hardware Notch */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-40 h-7 bg-slate-800 rounded-b-3xl z-50" />

        {/* Dynamic Screen Content */}
        <div className="flex-1 relative">
          {currentScreen === 'map' && renderMainMap()}
          {currentScreen === 'places' && renderPlaces()}
          {currentScreen === 'admin' && renderAdmin()}
        </div>

        {/* Bottom Navigation */}
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
        
        {/* iOS Home Indicator */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1.5 bg-white/20 rounded-full z-50 pointer-events-none" />
      </div>
    </div>
  );
}
