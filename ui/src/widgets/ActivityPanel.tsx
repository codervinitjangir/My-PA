import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Trash2, ShieldAlert, Cpu, Hammer, Search, CheckCircle } from 'lucide-react';
import { useJarvisStore, type ActivityItem } from '../store/jarvisStore';
import { cn } from '../lib/utils';

export const ActivityPanel: React.FC = () => {
  const {
    activities,
    activityPanelOpen,
    setActivityPanelOpen,
    clearActivities,
  } = useJarvisStore();

  const getIcon = (type: ActivityItem['type']) => {
    switch (type) {
      case 'error':
        return <ShieldAlert size={14} className="text-rose-400" />;
      case 'thinking':
        return <Cpu size={14} className="text-amber-400 animate-spin" />;
      case 'tool':
        return <Hammer size={14} className="text-indigo-400" />;
      case 'execution':
        return <CheckCircle size={14} className="text-emerald-400" />;
      default:
        return <Search size={14} className="text-cyan-400" />;
    }
  };

  const getTypeStyles = (type: ActivityItem['type']) => {
    switch (type) {
      case 'error':
        return 'bg-rose-500/10 border-rose-500/20 text-rose-200';
      case 'thinking':
        return 'bg-amber-500/10 border-amber-500/20 text-amber-200';
      case 'tool':
        return 'bg-indigo-500/10 border-indigo-500/20 text-indigo-200';
      case 'execution':
        return 'bg-emerald-500/10 border-emerald-500/20 text-emerald-200';
      default:
        return 'bg-cyan-500/10 border-cyan-500/20 text-cyan-200';
    }
  };

  return (
    <AnimatePresence>
      {activityPanelOpen && (
        <>
          {/* Overlay background */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setActivityPanelOpen(false)}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />

          {/* Sidebar */}
          <motion.aside
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-zinc-950/90 backdrop-blur-md border-l border-zinc-800/60 shadow-2xl flex flex-col font-sans text-white"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/60 bg-zinc-900/30">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm tracking-wide uppercase text-zinc-300">Activity Flow</span>
                <span className="text-xs px-2 py-0.5 bg-zinc-800 rounded-full text-zinc-400 font-mono">
                  {activities.length}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {activities.length > 0 && (
                  <button
                    onClick={clearActivities}
                    className="p-1.5 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-zinc-900/60 transition-all"
                    title="Clear Activities"
                  >
                    <Trash2 size={15} />
                  </button>
                )}
                <button
                  onClick={() => setActivityPanelOpen(false)}
                  className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900/60 transition-all"
                  title="Close Panel"
                >
                  <X size={15} />
                </button>
              </div>
            </div>

            {/* List Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
              {activities.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center text-zinc-500 space-y-2">
                  <X size={36} className="opacity-15" />
                  <p className="text-sm font-medium">No activity logged yet.</p>
                  <p className="text-xs max-w-[240px]">Ask Jarvis a question or run a task to see background execution updates.</p>
                </div>
              ) : (
                activities.slice().reverse().map((item) => (
                  <div
                    key={item.id}
                    className={cn(
                      "p-3.5 rounded-xl border flex flex-col gap-1.5 transition-all hover:bg-zinc-900/20",
                      getTypeStyles(item.type)
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-semibold text-xs tracking-wider uppercase">
                        {getIcon(item.type)}
                        <span>{item.type}</span>
                      </div>
                      <span className="text-[10px] text-zinc-500 font-mono">{item.timestamp}</span>
                    </div>
                    <p className="text-xs text-zinc-300 leading-relaxed font-mono select-text">
                      {item.text}
                    </p>
                  </div>
                ))
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};
