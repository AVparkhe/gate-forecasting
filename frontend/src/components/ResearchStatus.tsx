import { CheckCircle2, AlertTriangle } from 'lucide-react';

export default function ResearchStatus() {
  return (
    <div className="glass-card mb-6" style={{ padding: '1rem', border: '1px solid rgba(59, 130, 246, 0.3)', background: 'rgba(15, 23, 42, 0.8)' }}>
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
        <h3 className="text-sm font-bold text-gray-200 tracking-wider">RESEARCH ENGINE STATUS</h3>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-gray-500 block text-xs">Data</span>
          <span className="flex items-center text-green-400 gap-1"><CheckCircle2 className="w-3 h-3" /> Verified through 2025</span>
        </div>
        <div>
          <span className="text-gray-500 block text-xs">2026 Data</span>
          <span className="flex items-center text-yellow-500 gap-1"><AlertTriangle className="w-3 h-3" /> EXCLUDED / UNVERIFIED</span>
        </div>
        <div>
          <span className="text-gray-500 block text-xs">Model Version</span>
          <span className="text-gray-300">xgb_recurrence_v1</span>
        </div>
        <div>
          <span className="text-gray-500 block text-xs">Research Run Hash</span>
          <span className="text-blue-400 font-mono text-xs">RRH_7a82f91b</span>
        </div>
        <div>
          <span className="text-gray-500 block text-xs">Release Gate (Gate A)</span>
          <span className="flex items-center text-green-400 gap-1"><CheckCircle2 className="w-3 h-3" /> PASS</span>
        </div>
        <div>
          <span className="text-gray-500 block text-xs">Forecast Status</span>
          <span className="flex items-center text-green-400 gap-1"><CheckCircle2 className="w-3 h-3" /> FROZEN</span>
        </div>
        <div>
          <span className="text-gray-500 block text-xs">Evidence Coverage</span>
          <span className="text-gray-300">100% Pre-Target</span>
        </div>
        <div>
          <span className="text-gray-500 block text-xs">Forecast Type</span>
          <span className="text-gray-300">Concept Pattern (NOT Exact Question)</span>
        </div>
      </div>
    </div>
  );
}
