import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Play, 
  Eye, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle,
  ArrowRight,
  History,
  FileText,
  Brain,
  Zap,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

export default function HistoricalTimeMachine() {
  const [targetYear, setTargetYear] = useState(2020);
  const [step, setStep] = useState(0); // 0: Start, 1: Forecast, 2: Reveal, 3: Compare, 4: Learn

  const handleNextStep = () => {
    if (step < 4) setStep(step + 1);
  };

  return (
    <div className="space-y-6">
      {/* Time Machine Header Control */}
      <div className="glass-card flex items-center justify-between p-4 bg-slate-900/80 border-blue-500/30">
        <div className="flex items-center gap-6">
          <History className="w-8 h-8 text-blue-400" />
          <div>
            <div className="text-xs text-blue-400 font-bold uppercase tracking-widest mb-1">Target Year</div>
            <div className="flex items-center gap-4">
              <button 
                onClick={() => { setTargetYear(targetYear - 1); setStep(0); }}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
                disabled={targetYear <= 2000}
              >
                <ChevronLeft className="w-5 h-5 text-gray-400" />
              </button>
              <h2 className="text-3xl font-black text-white">{targetYear}</h2>
              <button 
                onClick={() => { setTargetYear(targetYear + 1); setStep(0); }}
                className="p-1 hover:bg-slate-700 rounded transition-colors"
                disabled={targetYear >= 2025}
              >
                <ChevronRight className="w-5 h-5 text-gray-400" />
              </button>
            </div>
          </div>
        </div>

        <div className="flex gap-8">
          <div>
            <div className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-1">Training Data</div>
            <div className="text-lg text-gray-300 font-mono">1987 → {targetYear - 1}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-1">Model</div>
            <div className="text-lg text-gray-300 font-mono">xgb_recurrence_v1</div>
          </div>
        </div>
      </div>

      {/* Main Stage */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Left Column: Forecast */}
        <div className="glass-card relative overflow-hidden min-h-[400px]">
          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" /> Model Forecast
          </h3>
          
          {step === 0 ? (
            <div className="absolute inset-0 flex-center flex-col gap-4 bg-slate-900/50 backdrop-blur-sm z-10">
              <button onClick={handleNextStep} className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg flex items-center gap-2 transition-all transform hover:scale-105">
                <Play className="w-4 h-4" /> GENERATE FORECAST
              </button>
            </div>
          ) : (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
                <span className="font-medium text-gray-200">Operating Systems</span>
                <span className="text-blue-400 font-mono">8 marks</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
                <span className="font-medium text-gray-200">Database Management</span>
                <span className="text-blue-400 font-mono">7 marks</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-purple-500/30">
                <div>
                  <span className="font-medium text-purple-300 block">Three Address Code</span>
                  <span className="text-xs text-gray-500">Compiler Design</span>
                </div>
                <span className="text-blue-400 font-mono">92% Prob</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
                <span className="font-medium text-gray-200">Computer Networks</span>
                <span className="text-blue-400 font-mono">6 marks</span>
              </div>
            </motion.div>
          )}
        </div>

        {/* Right Column: Actual */}
        <div className="glass-card relative overflow-hidden min-h-[400px]">
          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
            <FileText className="w-5 h-5 text-green-400" /> Actual {targetYear} Paper
          </h3>

          {step < 2 ? (
            <div className="absolute inset-0 flex-center flex-col gap-4 bg-slate-900/50 backdrop-blur-sm z-10">
              {step === 1 && (
                <button onClick={handleNextStep} className="px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white font-bold rounded-lg flex items-center gap-2 transition-all">
                  <Eye className="w-4 h-4" /> REVEAL ACTUAL
                </button>
              )}
            </div>
          ) : (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
                <span className="font-medium text-gray-200">Operating Systems</span>
                <span className="text-green-400 font-mono">7 marks</span>
                {step >= 3 && <CheckCircle2 className="w-4 h-4 text-green-500 ml-2" />}
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
                <span className="font-medium text-gray-200">Database Management</span>
                <span className="text-green-400 font-mono">8 marks</span>
                {step >= 3 && <CheckCircle2 className="w-4 h-4 text-green-500 ml-2" />}
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg border border-red-500/30">
                <div>
                  <span className="font-medium text-red-300 block">Three Address Code</span>
                  <span className="text-xs text-gray-500">Compiler Design</span>
                </div>
                <span className="text-gray-500 font-mono">DID NOT APPEAR</span>
                {step >= 3 && <XCircle className="w-4 h-4 text-red-500 ml-2" />}
              </div>
              <div className="flex justify-between items-center p-3 bg-slate-800/50 rounded-lg">
                <span className="font-medium text-gray-200">Computer Networks</span>
                <span className="text-green-400 font-mono">6 marks</span>
                {step >= 3 && <CheckCircle2 className="w-4 h-4 text-green-500 ml-2" />}
              </div>
            </motion.div>
          )}
        </div>
      </div>

      {/* Analysis Section */}
      <AnimatePresence>
        {step >= 2 && (
          <motion.div key="analysis-actions" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="flex justify-center my-6">
            {step === 2 ? (
              <button onClick={handleNextStep} className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg flex items-center gap-2 transition-all">
                RUN DIAGNOSTIC COMPARISON <ArrowRight className="w-4 h-4" />
              </button>
            ) : step === 3 ? (
              <button onClick={handleNextStep} className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-lg flex items-center gap-2 transition-all">
                SEND TO MODEL BRAIN <Zap className="w-4 h-4" />
              </button>
            ) : null}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Deep Learning Trace */}
      <AnimatePresence>
        {step >= 4 && (
          <motion.div key="learning-trace" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="space-y-6">
            
            <div className="glass-card border-red-900/50 bg-red-900/10">
              <h4 className="font-bold text-red-400 flex items-center gap-2 mb-2">
                <AlertTriangle className="w-5 h-5" /> High-Confidence Failure Detected
              </h4>
              <p className="text-gray-300 text-sm">
                Model predicted <strong className="text-white">Three Address Code</strong> with 92% confidence, but it did not appear.
              </p>
              
              <div className="mt-4 p-4 bg-slate-900 rounded-lg">
                <div className="text-xs text-gray-500 uppercase font-bold mb-2">Evidence that led to this prediction:</div>
                <div className="flex flex-col gap-2 text-sm text-gray-300">
                  <div className="flex justify-between border-b border-slate-800 pb-1">
                    <span>Evidence Strength</span> <span className="text-green-400">Strong</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-1">
                    <span>Recent appearances</span> <span>4 / last 5 years</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-1">
                    <span>Current recurrence gap</span> <span>1 year</span>
                  </div>
                  <div className="mt-2 text-xs text-blue-400">
                    Supporting Questions: [2019 - Q12], [2018 - Q44], [2017 - Q31], [2015 - Q19]
                  </div>
                </div>
              </div>
            </div>

            <div className="glass-card border-purple-900/50 relative">
              <div className="absolute -top-4 left-6 bg-purple-900 px-3 py-1 rounded-full text-xs font-bold text-purple-200">
                MODEL BRAIN LEARNING LOOP
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
                <div className="space-y-2">
                  <div className="text-xs text-purple-400 font-bold uppercase">1. Hypothesis</div>
                  <div className="text-sm text-gray-300 bg-slate-800/50 p-3 rounded">
                    Concept has high recurrence but is often skipped in years with major syllabus changes (like {targetYear}).
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="text-xs text-blue-400 font-bold uppercase">2. Candidate Strategy</div>
                  <div className="text-sm text-gray-300 bg-slate-800/50 p-3 rounded">
                    Penalize probability by 20% if `is_major_syllabus_change_year` is true.
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="text-xs text-green-400 font-bold uppercase">3. Temporal Backtest</div>
                  <div className="text-sm text-gray-300 bg-slate-800/50 p-3 rounded">
                    <span className="text-green-400 font-bold">PASSED</span><br/>
                    Improves historical Brier Score by 0.012. Strategy <strong>ACCEPTED</strong> and frozen into `xgb_recurrence_v2`.
                  </div>
                </div>
              </div>
            </div>
            
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
