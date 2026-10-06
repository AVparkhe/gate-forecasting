import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  BrainCircuit, 
  Target, 
  TrendingUp, 
  AlertTriangle, 
  BookOpen, 
  History,
  BarChart2,
  Search,
  FileText
} from 'lucide-react';

// Data
import forecastData from './data/forecast_2027.json';
import mockBlueprints from './data/mock_blueprints.json';
import calibrationData from './data/calibration_report.json';
import paperSpec from './data/forecast_2027_paper_spec.json';

// Components
import ResearchStatus from './components/ResearchStatus';
import HistoricalTimeMachine from './components/HistoricalTimeMachine';

export default function App() {
  const [activeTab, setActiveTab] = useState('history');

  const navItems = [
    { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
    { id: 'history', label: 'Historical Forecast Lab', icon: <History className="w-4 h-4" /> },
    { id: 'pattern', label: 'Pattern Explorer', icon: <BarChart2 className="w-4 h-4" /> },
    { id: 'brain', label: 'Model Brain', icon: <BrainCircuit className="w-4 h-4" /> },
    { id: 'surprise', label: 'Surprise Question Bank', icon: <AlertTriangle className="w-4 h-4" /> },
    { id: 'analytics', label: 'Accuracy & Analytics', icon: <TrendingUp className="w-4 h-4" /> },
    { id: 'forecast2027', label: 'GATE 2027 Forecast', icon: <Target className="w-4 h-4" /> },
    { id: 'mock', label: 'Mock Tests', icon: <BookOpen className="w-4 h-4" /> },
    { id: 'evidence', label: 'Evidence Explorer', icon: <Search className="w-4 h-4" /> },
    { id: 'reports', label: 'Reports', icon: <FileText className="w-4 h-4" /> }
  ];

  return (
    <div className="flex h-screen bg-[#0b0f19] text-gray-200 overflow-hidden font-sans">
      {/* Sidebar Navigation */}
      <aside className="w-64 flex-shrink-0 bg-slate-900/80 border-r border-slate-800 flex flex-col z-20">
        <div className="p-4 border-b border-slate-800 flex items-center gap-3">
          <Activity className="w-6 h-6 text-blue-500" />
          <h1 className="font-bold text-lg text-white">GATE Research Lab</h1>
        </div>
        
        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === item.id 
                  ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' 
                  : 'text-gray-400 hover:bg-slate-800 hover:text-gray-200'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-6 relative">
        <div className="max-w-6xl mx-auto pb-12">
          {/* Global Research Status */}
          <ResearchStatus />

          {/* Routed Views */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {activeTab === 'history' && <HistoricalTimeMachine />}
              {activeTab === 'forecast2027' && <Forecast2027 />}
              {activeTab === 'mock' && <MockTests />}
              {activeTab === 'brain' && <ModelBrain />}
              {/* Fallbacks for unbuilt tabs */}
              {['overview', 'pattern', 'surprise', 'analytics', 'evidence', 'reports'].includes(activeTab) && (
                <div className="flex-center flex-col h-64 text-gray-500">
                  <Activity className="w-12 h-12 mb-4 opacity-50" />
                  <p>Module currently in development</p>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

// ----------------------------------------------------
// Sub-Views (Ideally in separate files)
// ----------------------------------------------------

function Forecast2027() {
  const topCandidates = forecastData.forecast_candidate_set.slice(0, 5);
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <Target className="w-6 h-6 text-blue-500" /> GATE 2027 Forecast
      </h2>
      
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="glass-card">
          <div className="text-xs text-gray-500 font-bold uppercase mb-1">Data Verified Through</div>
          <div className="text-xl font-bold">{forecastData.metadata.latest_verified_year}</div>
        </div>
        <div className="glass-card">
          <div className="text-xs text-gray-500 font-bold uppercase mb-1">2026 Data Status</div>
          <div className="text-xl font-bold text-yellow-500">EXCLUDED</div>
        </div>
        <div className="glass-card">
          <div className="text-xs text-gray-500 font-bold uppercase mb-1">Forecast Type</div>
          <div className="text-xl font-bold text-blue-400">Pattern-Level</div>
        </div>
      </div>

      <div className="glass-card mt-6 border-blue-900/30">
        <h3 className="font-bold text-lg mb-4 text-gray-200">Top 5 Concept Candidates</h3>
        <table className="data-table w-full">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Topic</th>
              <th>Concept</th>
              <th>Probability</th>
              <th>Confidence</th>
            </tr>
          </thead>
          <tbody>
            {topCandidates.map((c, i) => (
              <tr key={i}>
                <td><span className="badge badge-info">#{c.rank}</span></td>
                <td className="text-gray-400">{c.topic}</td>
                <td className="font-bold">{c.concept}</td>
                <td>{(c.probability * 100).toFixed(1)}%</td>
                <td><span className="badge badge-high">{c.confidence}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MockTests() {
  const [selectedBp, setSelectedBp] = useState<any>(null);

  if (selectedBp) {
    return (
      <div className="space-y-6">
        <button onClick={() => setSelectedBp(null)} className="text-blue-400 hover:text-blue-300 flex items-center gap-2 mb-4 font-medium transition-colors">
          &larr; Back to Blueprints
        </button>
        <h2 className="text-2xl font-bold flex items-center gap-2 mb-6 text-white">
          <BookOpen className="w-6 h-6 text-green-500" /> {selectedBp.name}
        </h2>
        
        <div className="glass-card bg-slate-900/50">
          <h3 className="font-bold mb-6 text-xl border-b border-slate-700 pb-3 flex justify-between items-center">
            Test Preview
            <span className="text-sm font-normal text-gray-400 bg-slate-800 px-3 py-1 rounded-full">{selectedBp.composition}</span>
          </h3>
          <div className="space-y-4">
            {paperSpec.predicted_paper.slice(0, 5).map((q: any, i: number) => (
              <div key={i} className="p-5 bg-slate-800/60 rounded-lg border border-slate-700 hover:border-slate-600 transition-colors">
                <div className="flex justify-between mb-3 border-b border-slate-700/50 pb-2">
                  <span className="font-bold text-gray-200">{q.q_num} | {q.subject}</span>
                  <span className="text-blue-400 font-mono bg-blue-900/20 px-2 py-0.5 rounded">{q.marks} Marks | {q.question_type}</span>
                </div>
                <p className="text-md text-gray-100 mb-4 leading-relaxed font-serif">{q.evidence.crafted_mock_question}</p>
                <div className="flex justify-between items-center">
                  <div className="text-xs font-medium text-green-400 bg-green-900/20 px-2 py-1 rounded">Target Concept: {q.concept}</div>
                  <div className="text-xs text-gray-500 font-mono">Difficulty: {q.difficulty}</div>
                </div>
              </div>
            ))}
            <div className="text-center text-gray-400 font-medium text-sm mt-6 pt-4 border-t border-slate-800/50 italic">
              + 60 more questions generated in this blueprint suite
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2 mb-6 text-white">
        <BookOpen className="w-6 h-6 text-green-500" /> AI-Generated Practice Suite
      </h2>

      <div className="p-4 border border-yellow-900/50 bg-yellow-900/10 rounded-lg flex gap-3 text-yellow-200 mb-8 shadow-lg">
        <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <strong className="block mb-1">STRICT ISOLATION PROTOCOL:</strong> 
          All questions generated here reside in the <code className="bg-slate-800 px-1.5 py-0.5 rounded text-yellow-300 font-mono mx-1">AI_GENERATED_PRACTICE</code> namespace. 
          They are strictly prohibited from entering the Golden Dataset or influencing future historical simulations.
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {mockBlueprints.blueprints.map((bp, i) => (
          <div key={i} onClick={() => setSelectedBp(bp)} className="glass-card hover:border-green-500/50 hover:bg-slate-800/80 transition-all cursor-pointer group shadow-md hover:shadow-green-900/20 hover:-translate-y-1 duration-300">
            <h3 className="font-bold text-lg mb-2 group-hover:text-green-400 transition-colors">{bp.name}</h3>
            <p className="text-sm text-gray-400 mb-4 h-10 line-clamp-2">{bp.description}</p>
            <div className="pt-4 border-t border-slate-700/50 text-xs text-gray-500 uppercase tracking-widest font-bold group-hover:text-gray-400 transition-colors flex justify-between items-center">
              <span>{bp.composition}</span>
              <span className="text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity">View Test &rarr;</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModelBrain() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2 mb-6">
        <BrainCircuit className="w-6 h-6 text-purple-500" /> Model Brain & Learning Ledger
      </h2>
      
      <div className="glass-card">
        <h3 className="font-bold text-gray-300 mb-4">Probability Calibration (Brier Score)</h3>
        <div className="flex items-center gap-8 mb-6">
          <div>
            <div className="text-xs text-gray-500 uppercase font-bold">Brier Score</div>
            <div className="text-2xl font-mono text-purple-400">{calibrationData.brier_score.toFixed(4)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 uppercase font-bold">Reliability</div>
            <div className="text-2xl font-mono text-purple-400">{calibrationData.reliability.toFixed(4)}</div>
          </div>
        </div>
        <p className="text-sm text-gray-400">Calibration ensures that when the model says "80% probability", the concept actually appears historically 80% of the time.</p>
      </div>

      <div className="glass-card border-red-900/30">
        <h3 className="font-bold text-red-400 mb-4">High-Confidence Failures Ledger</h3>
        <table className="data-table w-full text-sm">
          <thead>
            <tr>
              <th>Target Year</th>
              <th>Failed Concept</th>
              <th>Predicted Prob</th>
              <th>Actual</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>2020</td>
              <td>Three Address Code</td>
              <td className="font-mono">92%</td>
              <td className="text-red-400">Did Not Appear</td>
              <td><span className="badge badge-high">STRATEGY ADOPTED</span></td>
            </tr>
            <tr>
              <td>2022</td>
              <td>LR Parsers</td>
              <td className="font-mono">88%</td>
              <td className="text-red-400">Did Not Appear</td>
              <td><span className="badge badge-medium">BACKTESTING</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
