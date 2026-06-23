import { useState, useCallback, useEffect } from 'react';
import { useJarvisStore } from './store/jarvisStore';
import { CommandPalette } from './widgets/CommandPalette';
import { GlobalDock } from './widgets/GlobalDock';
import { ContextBar } from './widgets/ContextBar';
import { ActivityPanel } from './widgets/ActivityPanel';
import { SearchResultsWidget } from './widgets/SearchResultsWidget';
import { SettingsPanel } from './widgets/SettingsPanel';
import { VisionWidget } from './widgets/VisionWidget';
import { ChatPage } from './pages/ChatPage';
import { VoiceOrb } from './animations/VoiceOrb';

function App() {
  const { activeTab, isOrbActive, setIsOrbActive, currentFocus, activeProject } = useJarvisStore();
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const toggleCommandPalette = useCallback(() => {
    setIsCommandPaletteOpen((prev) => !prev);
  }, []);

  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.code === 'Space') {
        e.preventDefault();
        toggleCommandPalette();
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [toggleCommandPalette]);

  return (
    <div className="min-h-screen bg-zinc-950 text-white overflow-hidden selection:bg-emerald-500/30 flex flex-col relative font-sans">
      {/* Decorative Premium Ambient Glow Backdrops */}
      <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] rounded-full bg-emerald-500/5 blur-[120px] pointer-events-none animate-pulse duration-[8000ms]" />
      <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] rounded-full bg-purple-500/5 blur-[150px] pointer-events-none animate-pulse duration-[12000ms]" />
      
      {/* OS Shell Layer Header / Widgets */}
      <ContextBar onOpenSettings={() => setIsSettingsOpen(true)} />
      <CommandPalette 
        isOpen={isCommandPaletteOpen} 
        onClose={() => setIsCommandPaletteOpen(false)} 
      />
      <GlobalDock />

      {/* Floating Side Panels & Dialogs */}
      <ActivityPanel />
      <SearchResultsWidget />
      <VisionWidget />
      <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {/* Main Workspace Frame */}
      <main className="flex-1 w-full h-full relative flex items-center justify-center pt-24 pb-32 px-4 z-10">
        
        {/* TAB 1: Home Ambient Orb Screen */}
        {activeTab === 'home' && (
          <div className="flex flex-col items-center justify-center text-center space-y-8 select-none">
            <div 
              className="cursor-pointer transition-transform duration-500 hover:scale-105"
              onClick={() => setIsOrbActive(!isOrbActive)}
            >
              <VoiceOrb isActive={isOrbActive} size={320} />
            </div>
            
            <div className="space-y-1 bg-zinc-900/30 border border-zinc-800/40 backdrop-blur-md px-6 py-3 rounded-2xl shadow-lg">
              <h1 className="text-sm font-semibold tracking-wider text-zinc-300 uppercase">J.A.R.V.I.S Ambient Terminal</h1>
              <p className="text-[11px] text-zinc-500">
                Click the core voice orb to toggle activation manually, or start speaking.
              </p>
            </div>
          </div>
        )}

        {/* TAB 2: Detailed Stream Chat Workspace */}
        {activeTab === 'chat' && <ChatPage />}

        {/* TABS 3+: Secondary Placeholder views for future workspace panels */}
        {!['home', 'chat'].includes(activeTab) && (
          <div className="p-8 rounded-3xl bg-zinc-900/40 border border-zinc-800/50 backdrop-blur-md flex flex-col items-center justify-center text-center max-w-md shadow-2xl">
            <div className="w-12 h-12 rounded-full bg-zinc-800/50 flex items-center justify-center text-zinc-500 mb-4 animate-bounce">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" />
                <path d="M9 3v18M15 3v18" />
              </svg>
            </div>
            <h3 className="text-sm font-bold text-zinc-200 capitalize mb-1">{activeTab} Workspace Active</h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              This panel is linked to active context. General instructions, speech streams, and observer pipelines remain fully operational via the global dock.
            </p>
            <div className="mt-4 px-4 py-2 bg-zinc-950/60 rounded-xl border border-zinc-800/60 text-[10px] text-zinc-400 font-mono">
              Focus: {currentFocus} | Project: {activeProject}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
