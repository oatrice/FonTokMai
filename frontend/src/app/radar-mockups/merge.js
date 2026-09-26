const fs = require('fs');

const pageContent = fs.readFileSync('page.tsx', 'utf-8');
const protoContent = fs.readFileSync('prototype.tsx', 'utf-8');

// Extract PrototypeMockup component
let protoComp = protoContent.replace(/export default function RadarMockupsPrototype\(\) {/g, 'function RadarMockupsPrototype() {');

// Combine
const importLines = `import React, { useState, useEffect } from 'react';
import { 
  Map, MapPin, Layers, Play, Pause, Bell, BellOff, Settings, AlertTriangle, 
  Crosshair, Activity, ShieldAlert, Sliders, Database, Search, ChevronRight,
  Clock, CheckCircle2, Zap, CloudLightning, Shield, Power, Gauge, Target,
  CloudRain, Wind, AlertCircle, Droplets, Sun, Navigation, BarChart2, Star, Check, Bug, SplitSquareVertical
} from 'lucide-react';
`;

let newPage = pageContent.replace(/import React.*?;/s, '');
newPage = newPage.replace(/import \{.*?;/s, '');

// Insert PrototypeMockup before export default function RadarMockupsPage
newPage = newPage.replace('export default function RadarMockupsPage', protoComp.split("function RadarMockupsPrototype")[1].split("export default function RadarMockupsPrototype")[0] + "\n\nexport default function RadarMockupsPage");

// Oh wait, doing regex replacement for function bodies is risky. 
// Let's just create a new file properly.
