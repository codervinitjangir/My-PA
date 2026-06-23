
import { Home, MessageSquare, Brain, CheckSquare, Laptop, Cpu, Bell } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../lib/utils';
import { useJarvisStore } from '../store/jarvisStore';

export const GlobalDock = () => {
  const { activeTab, setActiveTab } = useJarvisStore();

  const navItems = [
    { id: 'home', icon: <Home size={20} />, label: 'Home' },
    { id: 'chat', icon: <MessageSquare size={20} />, label: 'Chat' },
    { id: 'memory', icon: <Brain size={20} />, label: 'Memory' },
    { id: 'tasks', icon: <CheckSquare size={20} />, label: 'Tasks' },
    { id: 'devices', icon: <Laptop size={20} />, label: 'Devices' },
    { id: 'automations', icon: <Cpu size={20} />, label: 'Automations' },
  ];

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40">
      <motion.div 
        initial={{ y: 50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="flex items-center gap-2 px-3 py-2 bg-zinc-900/80 backdrop-blur-xl border border-zinc-800/60 rounded-full shadow-2xl"
      >
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={cn(
                "relative group flex items-center justify-center p-3 rounded-full transition-all duration-300",
                isActive ? "text-emerald-400 bg-emerald-400/10" : "text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50"
              )}
              title={item.label}
            >
              {item.icon}
              {isActive && (
                <motion.div
                  layoutId="dock-indicator"
                  className="absolute bottom-1 w-1.5 h-1.5 rounded-full bg-emerald-400"
                />
              )}
            </button>
          );
        })}
        
        <div className="w-[1px] h-8 bg-zinc-800 mx-2" />
        
        <button 
          onClick={() => useJarvisStore.getState().setActivityPanelOpen(true)}
          className="relative group flex items-center justify-center p-3 rounded-full text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/50 transition-all"
          title="Activity Log Notifications"
        >
          <Bell size={20} />
          <div className="absolute top-2 right-2 w-2 h-2 rounded-full bg-emerald-500 border border-zinc-900"></div>
        </button>
      </motion.div>
    </div>
  );
};
