import { create } from 'zustand';

export interface JarvisSettings {
  autoOpenActivity: boolean;
  autoOpenSearchResults: boolean;
  thinkingSounds: boolean;
  voiceInterrupt: boolean;
}

export interface SearchResultData {
  query?: string;
  answer?: string;
  list?: Array<{ title: string; url: string; snippet?: string }>;
}

export interface ActivityItem {
  id: string;
  timestamp: string;
  type: 'status' | 'tool' | 'thinking' | 'execution' | 'error';
  text: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  isStreaming?: boolean;
  images?: string[];
  backgroundTasks?: Array<{
    task_id: string;
    type: string;
    label?: string;
    status: 'pending' | 'completed' | 'failed';
    error?: string;
  }>;
  actions?: any;
}

interface JarvisState {
  // Session / Chat Mode
  sessionId: string | null;
  currentMode: 'jarvis' | 'general' | 'realtime';
  isStreaming: boolean;
  
  // Voice / Audio States
  isListening: boolean;
  isSpeaking: boolean; // User voice activity detection (VAD)
  ttsSpeaking: boolean; // Assistant TTS playback status
  isOrbActive: boolean;
  autoListenMode: boolean;
  speechWidgetVisible: boolean;
  speechWidgetText: string;
  
  // Settings
  settings: JarvisSettings;
  
  // Custom panels / features
  searchResults: SearchResultData | null;
  searchResultsVisible: boolean;
  activities: ActivityItem[];
  activityPanelOpen: boolean;
  
  // Camera widget
  isCameraActive: boolean;
  camFacingMode: 'user' | 'environment';
  camVisionMode: boolean;
  isCameraMinimized: boolean;
  captureFrameFn: (() => Promise<string | null>) | null;

  // Context Engine / Dashboard States
  currentFocus: string;
  activeProject: string;
  cpuUsage: string;
  memoryUsage: string;
  systemStatus: 'online' | 'offline';
  messages: ChatMessage[];
  activeTab: string;
  dashboardRawData: any;

  // Actions
  setSessionId: (id: string | null) => void;
  setCurrentMode: (mode: 'jarvis' | 'general' | 'realtime') => void;
  setIsStreaming: (val: boolean) => void;
  setIsListening: (val: boolean) => void;
  setIsSpeaking: (val: boolean) => void;
  setTtsSpeaking: (val: boolean) => void;
  setIsOrbActive: (val: boolean) => void;
  setAutoListenMode: (val: boolean) => void;
  setSpeechWidget: (visible: boolean, text?: string) => void;
  updateSetting: <K extends keyof JarvisSettings>(key: K, value: JarvisSettings[K]) => void;
  setSearchResults: (results: SearchResultData | null) => void;
  setSearchResultsVisible: (val: boolean) => void;
  addActivity: (text: string, type?: ActivityItem['type']) => void;
  clearActivities: () => void;
  setActivityPanelOpen: (val: boolean) => void;
  setCameraActive: (val: boolean) => void;
  setCamFacingMode: (mode: 'user' | 'environment') => void;
  setCamVisionMode: (val: boolean) => void;
  setCameraMinimized: (val: boolean) => void;
  registerCaptureFrameFn: (fn: (() => Promise<string | null>) | null) => void;
  setDashboardData: (data: any) => void;
  setSystemStatus: (status: 'online' | 'offline') => void;
  addChatMessage: (msg: Omit<ChatMessage, 'id'>) => string;
  updateChatMessage: (id: string, updates: Partial<ChatMessage>) => void;
  clearChatMessages: () => void;
  setActiveTab: (tab: string) => void;
}

const SETTINGS_KEY = 'jarvis_settings';
const DEFAULT_SETTINGS: JarvisSettings = {
  autoOpenActivity: true,
  autoOpenSearchResults: true,
  thinkingSounds: true,
  voiceInterrupt: true,
};

const loadSettings = (): JarvisSettings => {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;
  try {
    const stored = localStorage.getItem(SETTINGS_KEY);
    if (stored) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
    }
  } catch (e) {
    console.error('Failed to load settings', e);
  }
  return DEFAULT_SETTINGS;
};

export const useJarvisStore = create<JarvisState>((set) => ({
  // Initial States
  sessionId: null,
  currentMode: 'jarvis',
  isStreaming: false,
  isListening: false,
  isSpeaking: false,
  ttsSpeaking: false,
  isOrbActive: false,
  autoListenMode: false,
  speechWidgetVisible: false,
  speechWidgetText: '',
  settings: loadSettings(),
  searchResults: null,
  searchResultsVisible: false,
  activities: [],
  activityPanelOpen: false,
  isCameraActive: false,
  camFacingMode: 'user',
  camVisionMode: false,
  isCameraMinimized: false,
  captureFrameFn: null,
  currentFocus: 'No focus set',
  activeProject: 'No active project',
  cpuUsage: '0%',
  memoryUsage: '0%',
  systemStatus: 'offline',
  messages: [],
  activeTab: 'home',
  dashboardRawData: null,

  // Actions
  setSessionId: (id) => set({ sessionId: id }),
  setCurrentMode: (currentMode) => set({ currentMode }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setIsListening: (isListening) => set({ isListening }),
  setIsSpeaking: (isSpeaking) => set({ isSpeaking }),
  setTtsSpeaking: (ttsSpeaking) => set({ ttsSpeaking }),
  setIsOrbActive: (isOrbActive) => set({ isOrbActive }),
  setAutoListenMode: (autoListenMode) => set({ autoListenMode }),
  setSpeechWidget: (visible, text = '') => 
    set({ speechWidgetVisible: visible, speechWidgetText: text }),
  
  updateSetting: (key, value) => set((state) => {
    const updatedSettings = { ...state.settings, [key]: value };
    try {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(updatedSettings));
    } catch (_) {}
    return { settings: updatedSettings };
  }),

  setSearchResults: (searchResults) => set({ searchResults }),
  setSearchResultsVisible: (searchResultsVisible) => set({ searchResultsVisible }),

  addActivity: (text, type = 'status') => set((state) => {
    const newItem: ActivityItem = {
      id: Math.random().toString(36).substring(2, 9),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      type,
      text,
    };
    return { activities: [...state.activities, newItem] };
  }),
  
  clearActivities: () => set({ activities: [] }),
  setActivityPanelOpen: (activityPanelOpen) => set({ activityPanelOpen }),

  setCameraActive: (isCameraActive) => set({ isCameraActive }),
  setCamFacingMode: (camFacingMode) => set({ camFacingMode }),
  setCamVisionMode: (camVisionMode) => set({ camVisionMode }),
  setCameraMinimized: (isCameraMinimized) => set({ isCameraMinimized }),
  registerCaptureFrameFn: (fn) => set({ captureFrameFn: fn }),
  setDashboardData: (data) => set({
    currentFocus: data.current_focus || 'No focus set',
    activeProject: data.active_project || 'No active project',
    cpuUsage: data.computer_summary?.cpu_usage || '0%',
    memoryUsage: data.computer_summary?.memory_usage || '0%',
    systemStatus: 'online',
    dashboardRawData: data,
  }),
  setSystemStatus: (systemStatus) => set({ systemStatus }),
  addChatMessage: (msg) => {
    const id = Math.random().toString(36).substring(2, 9);
    set((state) => ({
      messages: [...state.messages, { ...msg, id }],
    }));
    return id;
  },
  updateChatMessage: (id, updates) => set((state) => ({
    messages: state.messages.map((m) => m.id === id ? { ...m, ...updates } : m),
  })),
  clearChatMessages: () => set({ messages: [] }),
  setActiveTab: (activeTab) => set({ activeTab }),
}));
