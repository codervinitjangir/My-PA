import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { useJarvisStore } from '../store/jarvisStore';

interface SettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const ToggleSwitch = ({ checked, onChange }: { checked: boolean; onChange: () => void }) => {
  return (
    <button
      type="button"
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
        checked ? 'bg-emerald-500' : 'bg-zinc-700/50'
      }`}
    >
      <span className="sr-only">Toggle setting</span>
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          checked ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  );
};

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ isOpen, onClose }) => {
  const { settings, updateSetting } = useJarvisStore();

  const toggleSetting = (key: keyof typeof settings) => {
    updateSetting(key, !settings[key]);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Overlay matching the old style updatePanelOverlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[2px]"
          />

          {/* Centered Modal mimicking the old .settings-panel */}
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="w-full max-w-[360px] bg-zinc-900/60 backdrop-blur-xl border border-zinc-700/50 rounded-2xl shadow-2xl overflow-hidden pointer-events-auto flex flex-col font-sans text-zinc-100"
              style={{
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1)'
              }}
            >
              {/* Header matching .settings-header */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-700/50">
                <h3 className="text-base font-semibold text-zinc-100">Settings</h3>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-full text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/80 transition-all focus:outline-none"
                  title="Close settings"
                  aria-label="Close settings"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Body matching .settings-body */}
              <div className="flex flex-col gap-5 px-5 pt-6 pb-7">
                
                {/* Auto Open Activity */}
                <div className="flex items-center justify-between gap-3">
                  <label 
                    className="text-[0.88rem] text-zinc-200 cursor-pointer select-none flex-1"
                    onClick={() => toggleSetting('autoOpenActivity')}
                  >
                    Auto-open activity panel
                  </label>
                  <ToggleSwitch 
                    checked={settings.autoOpenActivity} 
                    onChange={() => toggleSetting('autoOpenActivity')} 
                  />
                </div>

                {/* Auto Open Search Results */}
                <div className="flex items-center justify-between gap-3">
                  <label 
                    className="text-[0.88rem] text-zinc-200 cursor-pointer select-none flex-1"
                    onClick={() => toggleSetting('autoOpenSearchResults')}
                  >
                    Auto-open search results
                  </label>
                  <ToggleSwitch 
                    checked={settings.autoOpenSearchResults} 
                    onChange={() => toggleSetting('autoOpenSearchResults')} 
                  />
                </div>

                {/* Thinking Sound Effects */}
                <div className="flex items-center justify-between gap-3">
                  <label 
                    className="text-[0.88rem] text-zinc-200 cursor-pointer select-none flex-1"
                    onClick={() => toggleSetting('thinkingSounds')}
                  >
                    Thinking sound effects
                  </label>
                  <ToggleSwitch 
                    checked={settings.thinkingSounds} 
                    onChange={() => toggleSetting('thinkingSounds')} 
                  />
                </div>

                {/* Voice Interruption */}
                <div className="flex items-center justify-between gap-3">
                  <label 
                    className="text-[0.88rem] text-zinc-200 cursor-pointer select-none flex-1"
                    onClick={() => toggleSetting('voiceInterrupt')}
                  >
                    Voice interruption
                  </label>
                  <ToggleSwitch 
                    checked={settings.voiceInterrupt} 
                    onChange={() => toggleSetting('voiceInterrupt')} 
                  />
                </div>

                {/* Settings Hint matching .settings-hint */}
                <p className="text-[0.75rem] text-zinc-400 leading-relaxed mt-1">
                  Activity and search panels open automatically when data is available. Thinking sounds play a short cue while the AI processes. Voice interruption lets you interrupt the AI by speaking — it will stop talking and listen to you.
                </p>
              </div>
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
};
