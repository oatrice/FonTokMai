import re

with open('frontend/src/app/radar-mockups/page.tsx', 'r') as f:
    content = f.read()

# Add states
content = content.replace(
    "const [isAdmin, setIsAdmin] = useState(true);",
    "const [isAdmin, setIsAdmin] = useState(true);\n  const [isUIHidden, setIsUIHidden] = useState(false);\n  const [isCardMinimized, setIsCardMinimized] = useState(false);"
)

# Tap to hide UI on map
content = content.replace(
    'className="absolute inset-0 bg-cover transition-all duration-1000 ease-in-out origin-center"',
    'className="absolute inset-0 bg-cover transition-all duration-1000 ease-in-out origin-center cursor-pointer" onClick={() => setIsUIHidden(!isUIHidden)}'
)

# Hide top bar (applies to both prototypes)
content = content.replace(
    '<div className="absolute top-12 left-4 right-4 flex justify-between items-start z-30">',
    '<div className={`absolute top-12 left-4 right-4 flex justify-between items-start z-30 transition-all duration-500 ${isUIHidden ? \'-translate-y-24 opacity-0 pointer-events-none\' : \'translate-y-0 opacity-100\'}`}>'
)

# Hide bottom bar/card - Flow 0
content = content.replace(
    '<div className="absolute bottom-24 left-4 right-4 z-30">',
    '<div className={`absolute bottom-24 left-4 right-4 z-30 transition-all duration-500 ${isUIHidden ? \'translate-y-32 opacity-0 pointer-events-none\' : \'translate-y-0 opacity-100\'}`}>'
)

# Hide bottom bar/card - Flow 0.5
content = content.replace(
    '<div className="absolute bottom-6 left-4 right-4 z-30">',
    '<div className={`absolute bottom-6 left-4 right-4 z-30 transition-all duration-500 ${isUIHidden ? \'translate-y-32 opacity-0 pointer-events-none\' : \'translate-y-0 opacity-100\'}`}>'
)

# Hide main bottom navigation - Flow 0
content = content.replace(
    '<div className="h-20 bg-slate-900 border-t border-slate-800 flex items-center justify-around px-4 z-40 relative">',
    '<div className={`h-20 bg-slate-900 border-t border-slate-800 flex items-center justify-around px-4 z-40 relative transition-all duration-500 ${isUIHidden && currentScreen === \'map\' ? \'translate-y-24 opacity-0 pointer-events-none\' : \'translate-y-0 opacity-100\'}`}>'
)

# Add Drag handle & minimize button to cards
card_original = '<div className="bg-slate-900/85 backdrop-blur-xl border border-slate-700/50 rounded-3xl p-5 shadow-2xl relative overflow-hidden">'
card_new = """<div className={`bg-slate-900/85 backdrop-blur-xl border border-slate-700/50 rounded-3xl shadow-2xl relative overflow-hidden transition-all duration-500 ${isCardMinimized ? 'h-10' : 'h-[148px]'}`}>
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
          <div className={`px-5 pb-5 transition-opacity duration-300 ${isCardMinimized ? 'opacity-0 pointer-events-none' : 'opacity-100 delay-100'}`}>"""

content = content.replace(card_original, card_new)

# Add closing div for the new card structure (before the end of the card wrapper)
content = content.replace(
    '</div>\n      </div>\n    </div>\n  );',
    '</div>\n        </div>\n      </div>\n    </div>\n  );'
)

with open('frontend/src/app/radar-mockups/page.tsx', 'w') as f:
    f.write(content)

