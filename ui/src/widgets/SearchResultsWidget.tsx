import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, Globe, ChevronRight } from 'lucide-react';
import { useJarvisStore } from '../store/jarvisStore';

export const SearchResultsWidget: React.FC = () => {
  const {
    searchResults,
    searchResultsVisible,
    setSearchResultsVisible,
  } = useJarvisStore();

  const getDomainLabel = (urlStr: string): string => {
    if (!urlStr) return '';
    try {
      const url = new URL(urlStr);
      return url.hostname.replace('www.', '');
    } catch (_) {
      return urlStr;
    }
  };

  const results = searchResults?.list || [];

  return (
    <AnimatePresence>
      {searchResultsVisible && searchResults && (
        <>
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSearchResultsVisible(false)}
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          />

          {/* Left Sliding Sidebar */}
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed left-0 top-0 bottom-0 z-50 w-full max-w-lg bg-zinc-950/90 backdrop-blur-md border-r border-zinc-800/60 shadow-2xl flex flex-col font-sans text-white"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/60 bg-zinc-900/30">
              <div className="flex items-center gap-2 text-zinc-300 font-semibold text-sm tracking-wide uppercase">
                <Globe size={15} className="text-cyan-400 animate-pulse" />
                <span>Web Research Results</span>
              </div>
              <button
                onClick={() => setSearchResultsVisible(false)}
                className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900/60 transition-all"
                title="Close Results"
              >
                <X size={15} />
              </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
              {/* Search Query info */}
              <div className="space-y-1">
                <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono">Research Query</span>
                <h3 className="text-base font-semibold text-zinc-150 flex items-center gap-2">
                  <Search size={14} className="text-zinc-400" />
                  "{searchResults.query}"
                </h3>
              </div>

              {/* Direct LLM Answer / Synthesis */}
              {searchResults.answer && (
                <div className="p-4 rounded-xl bg-cyan-500/5 border border-cyan-500/10 space-y-2">
                  <span className="text-[10px] uppercase tracking-wider text-cyan-400 font-mono font-semibold">Direct Answer</span>
                  <p className="text-xs text-zinc-200 leading-relaxed whitespace-pre-wrap select-text font-sans">
                    {searchResults.answer}
                  </p>
                </div>
              )}

              {/* Search Results List */}
              <div className="space-y-3">
                <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono">Verified References ({results.length})</span>
                
                {results.length === 0 ? (
                  <p className="text-xs text-zinc-500 italic">No references found for this search.</p>
                ) : (
                  <div className="space-y-3">
                    {results.map((r, idx) => {
                      const domain = getDomainLabel(r.url);
                      return (
                        <div
                          key={idx}
                          className="p-4 rounded-xl bg-zinc-900/30 border border-zinc-800/40 hover:border-zinc-700/60 transition-all flex flex-col gap-2"
                        >
                          <h4 className="text-xs font-semibold text-zinc-100 select-text leading-snug">
                            {r.title || 'Source Reference'}
                          </h4>
                          {r.snippet && (
                            <p className="text-[11px] text-zinc-400 leading-relaxed select-text font-sans">
                              {r.snippet}
                            </p>
                          )}
                          <div className="flex items-center justify-between mt-1 pt-2 border-t border-zinc-900">
                            {r.url ? (
                              <a
                                href={r.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[10px] text-cyan-400 hover:underline flex items-center gap-0.5 group font-mono"
                              >
                                <span>{domain}</span>
                                <ChevronRight size={10} className="group-hover:translate-x-0.5 transition-transform" />
                              </a>
                            ) : (
                              <span className="text-[10px] text-zinc-500 font-mono">No URL available</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
};
