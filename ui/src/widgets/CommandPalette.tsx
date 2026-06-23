import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Command, AppWindow, FileText, CheckSquare, Folder, Brain, Users, Calendar, Laptop } from 'lucide-react';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const categories = [
    { icon: <AppWindow size={16} />, label: 'Apps' },
    { icon: <FileText size={16} />, label: 'Files' },
    { icon: <CheckSquare size={16} />, label: 'Tasks' },
    { icon: <Folder size={16} />, label: 'Projects' },
    { icon: <Brain size={16} />, label: 'Memories' },
    { icon: <Users size={16} />, label: 'People' },
    { icon: <Calendar size={16} />, label: 'Calendar' },
    { icon: <Command size={16} />, label: 'Commands' },
    { icon: <Laptop size={16} />, label: 'Devices' },
  ];

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] pointer-events-none"
          >
            <div 
              className="w-full max-w-2xl bg-zinc-950/90 backdrop-blur-md border border-zinc-800/60 rounded-2xl shadow-2xl overflow-hidden pointer-events-auto flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Search Header */}
              <div className="flex items-center px-4 py-4 border-b border-zinc-800/60">
                <Search className="text-zinc-400 mr-3" size={20} />
                <input
                  ref={inputRef}
                  type="text"
                  placeholder="What do you need, Boss?"
                  className="flex-1 bg-transparent text-zinc-100 placeholder:text-zinc-500 outline-none text-lg"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <div className="text-xs text-zinc-500 font-mono bg-zinc-900 px-2 py-1 rounded border border-zinc-800">
                  ESC
                </div>
              </div>

              {/* Results / Categories Area */}
              <div className="p-2 h-[400px] overflow-y-auto custom-scrollbar">
                {!query ? (
                  <div className="grid grid-cols-3 gap-2 p-2">
                    {categories.map((cat, idx) => (
                      <div 
                        key={idx} 
                        className="flex flex-col items-center justify-center p-4 rounded-xl border border-transparent hover:border-zinc-800 hover:bg-zinc-900/50 cursor-pointer transition-all duration-200 group"
                      >
                        <div className="p-3 rounded-full bg-zinc-900 text-zinc-400 group-hover:text-emerald-400 group-hover:bg-emerald-400/10 transition-colors">
                          {cat.icon}
                        </div>
                        <span className="mt-2 text-sm text-zinc-400 group-hover:text-zinc-200">
                          {cat.label}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                    <Search size={32} className="mb-3 opacity-20" />
                    <p>Searching JARVIS core for "{query}"...</p>
                  </div>
                )}
              </div>
              
              {/* Footer */}
              <div className="px-4 py-3 bg-zinc-900/30 border-t border-zinc-800/60 flex justify-between items-center text-xs text-zinc-500">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1"><kbd className="font-sans">↑↓</kbd> to navigate</span>
                  <span className="flex items-center gap-1"><kbd className="font-sans">↵</kbd> to select</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                  JARVIS Connected
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
