import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { Cpu, HardDrive, Target, FolderGit2, Activity, Search, Settings, Camera, CameraOff, Wifi, WifiOff } from 'lucide-react';
import { useJarvisStore } from '../store/jarvisStore';
import { cn } from '../lib/utils';

interface ContextBarProps {
  onOpenSettings: () => void;
}

export const ContextBar: React.FC<ContextBarProps> = ({ onOpenSettings }) => {
  const {
    currentFocus,
    activeProject,
    cpuUsage,
    memoryUsage,
    systemStatus,
    isCameraActive,
    activityPanelOpen,
    searchResults,
    searchResultsVisible,
    setCameraActive,
    setActivityPanelOpen,
    setSearchResultsVisible,
    setDashboardData,
    setSystemStatus,
  } = useJarvisStore();

  // Poll dashboard data
  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await fetch('/dashboard');
        if (res.ok) {
          const data = await res.json();
          setDashboardData(data);
        } else {
          setSystemStatus('offline');
        }
      } catch (err) {
        setSystemStatus('offline');
      }
    };

    fetchDashboard();
    const interval = setInterval(fetchDashboard, 5000);
    return () => clearInterval(interval);
  }, [setDashboardData, setSystemStatus]);

  return (
    <motion.div
      initial={{ y: -30, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 200, damping: 25 }}
      className="fixed top-4 left-1/2 -translate-x-1/2 z-40 w-[95%] max-w-5xl flex items-center justify-between px-6 py-2.5 bg-zinc-950/75 backdrop-blur-xl border border-zinc-800/40 rounded-full shadow-lg"
    >
      {/* Left: System Status & Resources */}
      <div className="flex items-center gap-4 text-xs font-mono text-zinc-400">
        <div className="flex items-center gap-1.5">
          <div className={cn(
            "w-2 h-2 rounded-full",
            systemStatus === 'online' ? "bg-emerald-500 animate-pulse" : "bg-rose-500"
          )} />
          <span className="text-zinc-300 font-medium capitalize flex items-center gap-1">
            {systemStatus === 'online' ? <Wifi size={12} className="text-emerald-400" /> : <WifiOff size={12} className="text-rose-400" />}
            {systemStatus}
          </span>
        </div>

        <div className="w-[1px] h-3.5 bg-zinc-800" />

        <div className="flex items-center gap-1.5" title="CPU Usage">
          <Cpu size={13} className="text-zinc-500" />
          <span>CPU {cpuUsage}</span>
        </div>

        <div className="flex items-center gap-1.5" title="Memory Usage">
          <HardDrive size={13} className="text-zinc-500" />
          <span>RAM {memoryUsage}</span>
        </div>
      </div>

      {/* Middle: Active Focus / Project */}
      <div className="hidden md:flex items-center gap-4 text-xs">
        <div className="flex items-center gap-2 px-3 py-1 bg-zinc-900/60 rounded-full border border-zinc-800/30">
          <Target size={12} className="text-emerald-400" />
          <span className="text-zinc-500 font-mono">Focus:</span>
          <span className="text-zinc-200 font-medium truncate max-w-[150px]">{currentFocus}</span>
        </div>

        <div className="flex items-center gap-2 px-3 py-1 bg-zinc-900/60 rounded-full border border-zinc-800/30">
          <FolderGit2 size={12} className="text-purple-400" />
          <span className="text-zinc-500 font-mono">Project:</span>
          <span className="text-zinc-200 font-medium truncate max-w-[150px]">{activeProject}</span>
        </div>
      </div>

      {/* Right: Quick Action Controls */}
      <div className="flex items-center gap-2">
        {/* Camera Toggle */}
        <button
          onClick={() => setCameraActive(!isCameraActive)}
          className={cn(
            "p-2 rounded-full transition-all duration-300 border",
            isCameraActive 
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" 
              : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 border-transparent"
          )}
          title={isCameraActive ? "Close Camera Viewport" : "Open Camera Viewport"}
        >
          {isCameraActive ? <Camera size={14} /> : <CameraOff size={14} />}
        </button>

        {/* Search Results Toggle */}
        {searchResults && (
          <button
            onClick={() => setSearchResultsVisible(!searchResultsVisible)}
            className={cn(
              "p-2 rounded-full transition-all duration-300 border",
              searchResultsVisible 
                ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/30" 
                : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 border-transparent"
            )}
            title="Toggle Search Results Panel"
          >
            <Search size={14} />
          </button>
        )}

        {/* Activity Toggle */}
        <button
          onClick={() => setActivityPanelOpen(!activityPanelOpen)}
          className={cn(
            "p-2 rounded-full transition-all duration-300 border",
            activityPanelOpen 
              ? "bg-purple-500/10 text-purple-400 border-purple-500/30" 
              : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 border-transparent"
          )}
          title="Toggle Activity Flow Sidebar"
        >
          <Activity size={14} />
        </button>

        <div className="w-[1px] h-3.5 bg-zinc-800 mx-1" />

        {/* Settings Toggle */}
        <button
          onClick={onOpenSettings}
          className="p-2 rounded-full text-zinc-400 hover:text-zinc-100 hover:bg-zinc-900 transition-colors"
          title="Settings Configuration"
        >
          <Settings size={14} />
        </button>
      </div>
    </motion.div>
  );
};
