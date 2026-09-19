import re

with open('frontend/src/app/radar-mockups/page.tsx', 'r') as f:
    content = f.read()

# 1. Update state and times array
old_state = "const [frameIndex, setFrameIndex] = useState(5);\n  const times = ['-25m', '-20m', '-15m', '-10m', '-5m', 'NOW'];"
new_state = "const [frameIndex, setFrameIndex] = useState(6);\n  const times = ['-30m', '-25m', '-20m', '-15m', '-10m', '-5m', 'NOW', '+5m', '+10m', '+15m', '+20m', '+25m', '+30m'];"
content = content.replace(old_state, new_state)

# 2. Update setInterval modulus
old_interval = "setFrameIndex((prev) => (prev + 1) % 6);"
new_interval = "setFrameIndex((prev) => (prev + 1) % times.length);"
content = content.replace(old_interval, new_interval)

# 3. Update the timeline UI markup
old_timeline_1 = """<div className="flex-1 relative flex flex-col justify-center h-10">
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
              </div>"""

old_timeline_2 = """<div className="flex-1 relative flex flex-col justify-center h-10">
                <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-2 px-1">
                   <span>-30m</span><span className="text-blue-400">{times[frameIndex]}</span>
                </div>
                <div className="absolute bottom-1 left-0 right-0 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 transition-all duration-300 ease-linear" style={{ width: `${(frameIndex / 5) * 100}%` }} />
                </div>
                <input type="range" min="0" max="5" value={frameIndex} onChange={(e) => { setFrameIndex(parseInt(e.target.value)); setIsPlaying(false); }} className="absolute bottom-0 inset-x-0 w-full opacity-0 cursor-pointer h-6" />
              </div>"""


new_timeline = """<div className="flex-1 relative flex flex-col justify-center h-10">
                <div className="flex justify-between text-[10px] font-bold text-slate-500 mb-2 px-1">
                   <span>-30m</span>
                   <span className={frameIndex > 6 ? "text-purple-400" : "text-blue-400"}>
                     {frameIndex > 6 ? 'พยากรณ์ ' : ''}{times[frameIndex]}
                   </span>
                   <span>+30m</span>
                </div>
                <div className="absolute bottom-1 left-0 right-0 h-1.5 bg-slate-800 rounded-full overflow-hidden">
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
                        i === 6 ? 'bg-white w-2 h-2 shadow-[0_0_8px_rgba(255,255,255,0.8)]' : // NOW indicator
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
              </div>"""

content = content.replace(old_timeline_1, new_timeline)
content = content.replace(old_timeline_2, new_timeline)

with open('frontend/src/app/radar-mockups/page.tsx', 'w') as f:
    f.write(content)
