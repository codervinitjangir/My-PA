import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Sun, Play, Eye, FolderCode, Link2, RotateCw, Plus, CheckSquare, Square, 
  Trash2, Monitor, Percent, Sparkles, ChevronRight, X
} from 'lucide-react';
import { useJarvisStore } from '../store/jarvisStore';
import { api } from '../services/api';

export const DashboardWidgets: React.FC<{ onSendMessage: (msg: string) => void }> = ({ onSendMessage }) => {
  const { dashboardRawData, setDashboardData, addActivity } = useJarvisStore();
  const [frictions, setFrictions] = useState<any[]>([]);
  const [newFriction, setNewFriction] = useState('');
  const [usage, setUsage] = useState<any>(null);
  const [briefing, setBriefing] = useState<any>(null);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const [screenAnalysis, setScreenAnalysis] = useState<any>(null);
  const [isAnalyzingScreen, setIsAnalyzingScreen] = useState(false);

  // Reload all dashboard related data
  const loadAllData = async () => {
    try {
      const [dash, fList, useData] = await Promise.all([
        api.getDashboard(),
        api.getFrictions(),
        api.getUsage()
      ]);
      setDashboardData(dash);
      setFrictions(fList || []);
      setUsage(useData);
      
      // If the dashboard already contains screen state, load it
      if (dash?.current_screen) {
        setScreenAnalysis(dash.current_screen);
      }
    } catch (err) {
      console.error('Failed to load dashboard widgets data', err);
    }
  };

  useEffect(() => {
    loadAllData();
    const interval = setInterval(loadAllData, 20000);
    return () => clearInterval(interval);
  }, []);

  // Actions
  const handleMorningBrief = async () => {
    try {
      const data = await api.getBriefing();
      setBriefing(data);
      setIsBriefingOpen(true);
      addActivity('Retrieved daily briefing report', 'status');
    } catch (e) {
      console.error(e);
    }
  };

  const handleAnalyzeScreen = async () => {
    if (isAnalyzingScreen) return;
    setIsAnalyzingScreen(true);
    addActivity('Capturing screen context for observation...', 'status');
    try {
      const data = await api.performOperatorAction('analyze_screen');
      if (data && !data.error) {
        setScreenAnalysis(data);
        addActivity('Screen observation completed successfully', 'status');
      } else if (data?.error) {
        addActivity(data.error, 'error');
      }
    } catch (e) {
      console.error(e);
      addActivity('Screen observation pipeline failed', 'error');
    } finally {
      setIsAnalyzingScreen(false);
    }
  };

  const handleToggleWakeWord = async () => {
    try {
      const res = await api.performOperatorAction('toggle_wake_word');
      if (res.success) {
        addActivity(`Wake word daemon status changed`, 'status');
        loadAllData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleOpenSite = async (siteAlias: string) => {
    try {
      addActivity(`Opening site ${siteAlias}...`, 'status');
      const res = await api.performOperatorAction('open_site', { site: siteAlias });
      if (res.success) {
        loadAllData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Friction Handlers
  const handleAddFriction = async () => {
    const text = newFriction.trim();
    if (!text) return;
    setNewFriction('');
    try {
      await api.addFriction(text);
      const fList = await api.getFrictions();
      setFrictions(fList || []);
      addActivity(`Logged friction point: "${text}"`, 'status');
    } catch (e) {
      console.error(e);
    }
  };

  const handleResolveFriction = async (id: string) => {
    try {
      await api.resolveFriction(id);
      const fList = await api.getFrictions();
      setFrictions(fList || []);
      addActivity('Friction resolved', 'status');
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteFriction = async (id: string) => {
    try {
      await api.deleteFriction(id);
      const fList = await api.getFrictions();
      setFrictions(fList || []);
      addActivity('Friction entry deleted', 'status');
    } catch (e) {
      console.error(e);
    }
  };

  if (!dashboardRawData) {
    return (
      <div className="flex items-center justify-center p-8 text-zinc-500 font-mono text-xs gap-2">
        <RotateCw size={14} className="animate-spin text-emerald-500" />
        <span>Syncing Dashboard Engine...</span>
      </div>
    );
  }

  const briefActionLabel = dashboardRawData.time_of_day === "morning" ? "Morning Brief" : 
                           dashboardRawData.time_of_day === "afternoon" ? "Afternoon Review" : "Evening Summary";

  return (
    <div className="w-full space-y-6 text-left select-none pb-8">
      {/* 1. Header Greeting Card */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-6 bg-zinc-900/25 border border-zinc-800/40 backdrop-blur-md rounded-2xl"
      >
        <div className="space-y-1">
          <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
            <span>{dashboardRawData.greeting}</span>
            <Sparkles size={16} className="text-amber-400 animate-pulse" />
          </h2>
          <p className="text-xs text-zinc-400">Welcome to your programmatic control deck.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="text-[10px] font-mono bg-zinc-900/60 border border-zinc-800/80 px-3 py-1.5 rounded-lg flex items-center gap-2 text-zinc-300">
            <span className={`w-2 h-2 rounded-full ${dashboardRawData.telegram_enabled ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-600'}`} />
            <span>Telegram Link: {dashboardRawData.telegram_enabled ? 'Active' : 'Offline'}</span>
          </div>

          {dashboardRawData.wake_word && (
            <div className="text-[10px] font-mono bg-zinc-900/60 border border-zinc-800/80 px-3 py-1 rounded-lg flex items-center gap-2.5 text-zinc-300">
              <span className={`w-2 h-2 rounded-full ${dashboardRawData.wake_word.enabled ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
              <span>Wake Word</span>
              <button 
                onClick={handleToggleWakeWord}
                className="bg-zinc-800 hover:bg-zinc-700/80 text-[9px] text-zinc-200 border border-zinc-750 px-2 py-0.5 rounded transition-all focus:outline-none"
              >
                Toggle
              </button>
            </div>
          )}
        </div>
      </motion.div>

      {/* 2. Command Center (Actions Hub) */}
      <div className="space-y-3">
        <h3 className="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-500">Jarvis Command Center</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2">
          <button 
            onClick={handleMorningBrief}
            className="flex flex-col items-center justify-center p-3.5 bg-zinc-900/30 hover:bg-emerald-500/10 border border-zinc-900 hover:border-emerald-500/20 rounded-xl text-center transition-all group focus:outline-none"
          >
            <Sun className="text-amber-400 mb-1.5 transition-transform group-hover:scale-110" size={18} />
            <span className="text-[10px] font-medium text-zinc-300">{briefActionLabel}</span>
          </button>

          <button 
            onClick={() => onSendMessage('Continue Previous Session')}
            className="flex flex-col items-center justify-center p-3.5 bg-zinc-900/30 hover:bg-emerald-500/10 border border-zinc-900 hover:border-emerald-500/20 rounded-xl text-center transition-all group focus:outline-none"
          >
            <Play className="text-emerald-400 mb-1.5 transition-transform group-hover:scale-110" size={18} />
            <span className="text-[10px] font-medium text-zinc-300">Resume Session</span>
          </button>

          <button 
            onClick={handleAnalyzeScreen}
            disabled={isAnalyzingScreen}
            className="flex flex-col items-center justify-center p-3.5 bg-zinc-900/30 hover:bg-emerald-500/10 border border-zinc-900 hover:border-emerald-500/20 rounded-xl text-center transition-all group focus:outline-none disabled:opacity-50"
          >
            <Eye className="text-cyan-400 mb-1.5 transition-transform group-hover:scale-110" size={18} />
            <span className="text-[10px] font-medium text-zinc-300">
              {isAnalyzingScreen ? 'Analyzing...' : 'Analyze Screen'}
            </span>
          </button>

          <button 
            onClick={() => onSendMessage('Open VS Code')}
            className="flex flex-col items-center justify-center p-3.5 bg-zinc-900/30 hover:bg-emerald-500/10 border border-zinc-900 hover:border-emerald-500/20 rounded-xl text-center transition-all group focus:outline-none"
          >
            <FolderCode className="text-purple-400 mb-1.5 transition-transform group-hover:scale-110" size={18} />
            <span className="text-[10px] font-medium text-zinc-300">Open Workspace</span>
          </button>

          <button 
            onClick={() => {
              const el = document.getElementById('quick-links-section');
              el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }}
            className="flex flex-col items-center justify-center p-3.5 bg-zinc-900/30 hover:bg-emerald-500/10 border border-zinc-900 hover:border-emerald-500/20 rounded-xl text-center transition-all group focus:outline-none"
          >
            <Link2 className="text-blue-400 mb-1.5 transition-transform group-hover:scale-110" size={18} />
            <span className="text-[10px] font-medium text-zinc-300">Quick Links</span>
          </button>

          <button 
            onClick={loadAllData}
            className="flex flex-col items-center justify-center p-3.5 bg-zinc-900/30 hover:bg-emerald-500/10 border border-zinc-900 hover:border-emerald-500/20 rounded-xl text-center transition-all group focus:outline-none"
          >
            <RotateCw className="text-zinc-400 mb-1.5 group-hover:rotate-180 transition-transform duration-500" size={18} />
            <span className="text-[10px] font-medium text-zinc-300">Refresh deck</span>
          </button>
        </div>
      </div>

      {/* 3. Main Data Cards Grid (Frictions Log & Status Summary) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Column A: Today's Status, Metrics, & Sites */}
        <div className="space-y-4">
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-500">System Metrics & Quick Sites</h3>
          
          <div className="p-5 bg-zinc-900/25 border border-zinc-800/40 backdrop-blur-md rounded-2xl space-y-4">
            
            {/* Streak & Completion Metric */}
            {dashboardRawData.timeline && (
              <div className="space-y-2 border-b border-zinc-800/60 pb-3">
                <div className="flex justify-between items-center text-xs">
                  <span className="font-semibold text-zinc-200">Progress Timeline</span>
                  <span className="text-emerald-400 font-bold font-mono">🔥 {dashboardRawData.timeline.metrics.current_streak} Day Streak</span>
                </div>

                <div className="w-full bg-zinc-800/50 rounded-full h-2 overflow-hidden border border-zinc-750">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${dashboardRawData.timeline.metrics.progress_percentage}%` }}
                    transition={{ duration: 0.8 }}
                    className="bg-emerald-500 h-full rounded-full"
                  />
                </div>

                <div className="flex justify-between text-[10px] text-zinc-400 font-mono">
                  <span>Completed: {dashboardRawData.timeline.metrics.completed_count}</span>
                  <span>Pending: {dashboardRawData.timeline.metrics.pending_count}</span>
                </div>

                {dashboardRawData.timeline.metrics.milestones?.length > 0 && (
                  <div className="text-[10px] text-amber-400 pt-1 flex items-center gap-1">
                    <span>🏆</span>
                    <span className="truncate">{dashboardRawData.timeline.metrics.milestones.join(', ')}</span>
                  </div>
                )}
              </div>
            )}

            {/* Programmatic status grid */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-2.5 bg-zinc-950/40 border border-zinc-850 rounded-lg space-y-1">
                <span className="text-[10px] text-zinc-500 block uppercase font-mono">Focus Mode</span>
                <span className="font-semibold text-zinc-200 truncate block">{dashboardRawData.current_focus}</span>
              </div>
              
              <div className="p-2.5 bg-zinc-950/40 border border-zinc-850 rounded-lg space-y-1">
                <span className="text-[10px] text-zinc-500 block uppercase font-mono">Active Project</span>
                <span className="font-semibold text-zinc-200 truncate block">{dashboardRawData.active_project}</span>
              </div>

              <div className="p-2.5 bg-zinc-950/40 border border-zinc-850 rounded-lg space-y-1">
                <span className="text-[10px] text-zinc-500 block uppercase font-mono">CPU Utilization</span>
                <span className="font-semibold text-zinc-200 font-mono">{dashboardRawData.computer_summary?.cpu_usage}</span>
              </div>

              <div className="p-2.5 bg-zinc-950/40 border border-zinc-850 rounded-lg space-y-1">
                <span className="text-[10px] text-zinc-500 block uppercase font-mono">Memory Load</span>
                <span className="font-semibold text-zinc-200 font-mono">{dashboardRawData.computer_summary?.memory_usage}</span>
              </div>
            </div>

            {/* Quick Links Site Grid */}
            {dashboardRawData.quick_links && (
              <div className="pt-2" id="quick-links-section">
                <span className="text-[10px] text-zinc-500 block uppercase font-mono mb-2">Workspace Quick Links</span>
                <div className="flex flex-wrap gap-1.5">
                  {dashboardRawData.quick_links.map((link: any, idx: number) => (
                    <button
                      key={idx}
                      onClick={() => handleOpenSite(link.site)}
                      className="px-3 py-1.5 bg-zinc-950/50 hover:bg-zinc-800/80 border border-zinc-850 hover:border-zinc-700 text-[10px] text-zinc-300 rounded-lg transition-all focus:outline-none flex items-center gap-1"
                    >
                      <Link2 size={10} className="text-zinc-500" />
                      <span>{link.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Column B: Frictions Log */}
        <div className="space-y-4">
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-500">Today's Frictions</h3>
          
          <div className="p-5 bg-zinc-900/25 border border-zinc-800/40 backdrop-blur-md rounded-2xl flex flex-col h-[324px] justify-between">
            <div className="overflow-y-auto space-y-2 flex-1 custom-scrollbar pr-1">
              {frictions.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-4">
                  <Sparkles size={20} className="text-emerald-500 mb-2 animate-bounce" />
                  <p className="text-[11px] text-zinc-400">No frictions logged today.</p>
                  <p className="text-[9px] text-zinc-600">Your workflows are running completely smooth! ✓</p>
                </div>
              ) : (
                frictions.map((item) => {
                  const isOpen = item.status === 'open';
                  return (
                    <div 
                      key={item.id} 
                      className={`flex items-center justify-between p-2.5 bg-zinc-950/40 border rounded-xl text-xs gap-3 ${
                        isOpen ? 'border-zinc-850' : 'border-zinc-850/40 opacity-50'
                      }`}
                    >
                      <button 
                        onClick={() => handleResolveFriction(item.id)}
                        className="text-zinc-500 hover:text-emerald-400 transition-colors focus:outline-none"
                      >
                        {isOpen ? (
                          <Square size={15} className="text-zinc-600" />
                        ) : (
                          <CheckSquare size={15} className="text-emerald-500" />
                        )}
                      </button>

                      <span className={`flex-1 break-all ${!isOpen && 'line-through text-zinc-500'}`}>
                        {item.text}
                      </span>

                      <button 
                        onClick={() => handleDeleteFriction(item.id)}
                        className="text-zinc-600 hover:text-rose-500 transition-colors focus:outline-none"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  );
                })
              )}
            </div>

            {/* Add Friction controls */}
            <div className="flex gap-2 pt-4 border-t border-zinc-800/60 mt-3">
              <input
                type="text"
                value={newFriction}
                onChange={(e) => setNewFriction(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddFriction()}
                placeholder="Log workflow friction point..."
                className="flex-1 px-3 py-2 bg-zinc-950/60 border border-zinc-800 rounded-xl text-xs text-white focus:outline-none focus:border-zinc-700 placeholder:text-zinc-650"
              />
              <button 
                onClick={handleAddFriction}
                className="px-3 bg-zinc-800 hover:bg-zinc-700/80 border border-zinc-750 text-xs font-semibold rounded-xl transition-all focus:outline-none flex items-center gap-1.5"
              >
                <Plus size={14} />
                <span>Add</span>
              </button>
            </div>
          </div>
        </div>

      </div>

      {/* 4. Screen Analysis Card (Display only if data exists) */}
      {screenAnalysis && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="space-y-3"
        >
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-500">Live Visual Observer</h3>
          <div className="p-5 bg-zinc-900/25 border border-zinc-800/40 backdrop-blur-md rounded-2xl space-y-4">
            
            <div className="flex items-center justify-between border-b border-zinc-800/60 pb-3">
              <div className="flex items-center gap-2 text-xs">
                <Monitor size={15} className="text-emerald-400" />
                <span className="font-semibold text-zinc-200">Current Captured Frame</span>
              </div>
              {screenAnalysis.confidence !== undefined && (
                <div className="flex items-center gap-1.5 text-[10px] font-mono">
                  <Percent size={11} className="text-zinc-500" />
                  <span className="text-zinc-400">Confidence:</span>
                  <span className={`font-bold ${
                    screenAnalysis.confidence >= 80 ? 'text-emerald-400' : screenAnalysis.confidence >= 55 ? 'text-amber-400' : 'text-rose-400'
                  }`}>
                    {Math.round(screenAnalysis.confidence)}%
                  </span>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="space-y-1">
                <span className="text-[10px] text-zinc-500 block uppercase font-mono">Open Application</span>
                <span className="font-semibold text-zinc-200">{screenAnalysis.application || 'Unknown'}</span>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] text-zinc-500 block uppercase font-mono">Detected Activity</span>
                <span className="font-semibold text-zinc-200">{screenAnalysis.activity || 'Unknown'}</span>
              </div>

              <div className="sm:col-span-2 space-y-1 bg-zinc-950/30 border border-zinc-850 p-3 rounded-xl">
                <span className="text-[10px] text-zinc-500 block uppercase font-mono mb-1">State Analysis</span>
                <p className="text-zinc-300 leading-relaxed font-sans text-[11px]">{screenAnalysis.summary}</p>
              </div>

              {screenAnalysis.next_best_action && (
                <div className="sm:col-span-2 flex items-center gap-2 p-2.5 bg-emerald-500/5 border border-emerald-500/10 rounded-xl">
                  <ChevronRight size={14} className="text-emerald-400 animate-pulse" />
                  <span className="text-[10px] font-mono uppercase tracking-wide text-emerald-400 font-bold">Recommended:</span>
                  <span className="text-[11px] text-zinc-250 truncate">{screenAnalysis.next_best_action}</span>
                </div>
              )}
            </div>

          </div>
        </motion.div>
      )}

      {/* 5. Daily Usage Card (Display if usage details available) */}
      {usage && (
        <div className="space-y-3">
          <h3 className="text-[10px] font-mono font-semibold uppercase tracking-wider text-zinc-500">Event Engagement Counters</h3>
          <div className="p-5 bg-zinc-900/25 border border-zinc-800/40 backdrop-blur-md rounded-2xl">
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5 text-center">
              {[
                { label: 'Dashboard', val: usage.features?.dashboard_open || 0 },
                { label: 'Morning Brief', val: usage.features?.morning_brief || 0 },
                { label: 'Screen Analysis', val: usage.features?.screen_analysis || 0 },
                { label: 'Resume Session', val: usage.features?.session_resume || 0 },
                { label: 'Browser Opens', val: usage.features?.browser_open || 0 },
              ].map((row, idx) => (
                <div key={idx} className="p-3 bg-zinc-950/40 border border-zinc-850 rounded-xl space-y-1">
                  <span className="text-[9px] text-zinc-500 block uppercase tracking-wider font-mono">{row.label}</span>
                  <span className="text-base font-bold text-zinc-200 font-mono">{row.val}</span>
                </div>
              ))}
            </div>
            
            {usage.most_used && (
              <div className="mt-4 pt-3 border-t border-zinc-800/40 flex flex-wrap gap-4 text-[10px] text-zinc-400 font-mono">
                <span>Most Active: <strong className="text-emerald-400">{usage.most_used}</strong></span>
                {usage.least_used && <span>Least Active: <strong className="text-zinc-500">{usage.least_used}</strong></span>}
                <span className="ml-auto text-emerald-500 font-semibold">{usage.score_label}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 6. Daily Briefing Modal */}
      <AnimatePresence>
        {isBriefingOpen && briefing && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsBriefingOpen(false)}
              className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm pointer-events-auto"
            />
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 10 }}
                className="w-full max-w-lg bg-zinc-950/90 border border-zinc-850 rounded-2xl shadow-2xl overflow-hidden pointer-events-auto flex flex-col font-sans text-zinc-200"
              >
                <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-850 bg-zinc-900/10">
                  <div className="flex items-center gap-2 text-zinc-300 font-semibold text-xs tracking-wider uppercase">
                    <Sun size={14} className="text-amber-400 animate-pulse" />
                    <span>Daily Briefing Summary</span>
                  </div>
                  <button 
                    onClick={() => setIsBriefingOpen(false)}
                    className="p-1 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900 transition-all focus:outline-none"
                  >
                    <X size={16} />
                  </button>
                </div>

                <div className="p-6 space-y-5 overflow-y-auto max-h-[70vh] custom-scrollbar text-xs leading-relaxed">
                  <div className="text-sm font-semibold text-zinc-150 border-b border-zinc-900 pb-2">{briefing.greeting}</div>

                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div className="p-3 bg-zinc-900/30 border border-zinc-900 rounded-xl space-y-1">
                      <span className="text-[10px] text-zinc-500 block uppercase font-mono">Focus Category</span>
                      <p className="font-semibold text-zinc-200">{briefing.today_mode}</p>
                    </div>

                    <div className="p-3 bg-zinc-900/30 border border-zinc-900 rounded-xl space-y-1">
                      <span className="text-[10px] text-zinc-500 block uppercase font-mono">Energy Allocation</span>
                      <p className="font-semibold text-zinc-200">{briefing.energy_score}</p>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <span className="text-[10px] text-zinc-500 block uppercase font-mono">Primary Objective</span>
                    <p className="font-semibold text-zinc-200 bg-zinc-900/30 border border-zinc-900 p-3 rounded-xl leading-normal">{briefing.today_focus}</p>
                  </div>

                  {briefing.active_projects && briefing.active_projects.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-[10px] text-zinc-500 block uppercase font-mono">Target Projects</span>
                      <ul className="list-disc pl-5 space-y-1 text-zinc-350">
                        {briefing.active_projects.map((p: string, idx: number) => (
                          <li key={idx}>{p}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="space-y-1 border-t border-zinc-900 pt-3 flex justify-between items-center text-zinc-450 font-mono text-[10px]">
                    <span>Pending Work Items:</span>
                    <span className="font-bold text-zinc-300">{briefing.pending_tasks} items</span>
                  </div>

                  <div className="space-y-1.5">
                    <span className="text-[10px] text-zinc-500 block uppercase font-mono">Hardware/Agent Health</span>
                    <p className="text-zinc-300 font-semibold">{briefing.computer_status}</p>
                  </div>

                  {briefing.suggested_action && (
                    <div className="bg-emerald-500/5 border border-emerald-500/10 p-4 rounded-xl space-y-3.5">
                      <div className="space-y-1">
                        <span className="text-[9px] text-emerald-400 block uppercase tracking-wider font-mono font-bold">Suggested Immediate Action</span>
                        <p className="text-zinc-300 text-[11px] font-sans font-medium leading-normal">{briefing.suggested_action}</p>
                      </div>
                      <button
                        onClick={() => {
                          setIsBriefingOpen(false);
                          onSendMessage(briefing.suggested_action);
                        }}
                        className="w-full py-2 bg-emerald-500/10 hover:bg-emerald-500 text-emerald-400 hover:text-white border border-emerald-500/20 rounded-xl text-xs font-semibold tracking-wide transition-all focus:outline-none"
                      >
                        Execute Recommendation
                      </button>
                    </div>
                  )}
                </div>
              </motion.div>
            </div>
          </>
        )}
      </AnimatePresence>

    </div>
  );
};
