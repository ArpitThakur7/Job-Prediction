"use client";

import React, { createContext, useContext, useState, useEffect } from "react";

export interface Message {
  role: "user" | "bot";
  content: string;
  sources?: any[];
  provider_used?: string;
}

export interface InfraStatus {
  backend: boolean;
  mongodb: boolean;
  redis: boolean;
  pinecone: boolean;
  groq: boolean;
  gemini: boolean;
  openai: boolean;
  anthropic: boolean;
  openrouter: boolean;
}

export type ThemeType = "luminary" | "emerald" | "cyberpunk" | "quantum" | "gold" | "aurora";

export interface ThemeColors {
  primary: string;
  secondary: string;
  accent: string;
  bgDark: string;
  glow: string;
  badgeBg: string;
  badgeBorder: string;
  badgeText: string;
  isDark?: boolean;
  bgGradient?: string;
  panelBg?: string;
  panelBorder?: string;
  sidebarBg?: string;
  headerBg?: string;
  textColor?: string;
  textMuted?: string;
}

export const themePresets: Record<ThemeType, ThemeColors> = {
  luminary: {
    primary: "#2563eb",
    secondary: "#10b981",
    accent: "#06b6d4",
    bgDark: "#FAFBFF",
    glow: "rgba(37, 99, 235, 0.25)",
    badgeBg: "rgba(37, 99, 235, 0.08)",
    badgeBorder: "rgba(37, 99, 235, 0.25)",
    badgeText: "#1d4ed8",
    isDark: false,
    bgGradient: "linear-gradient(180deg, #FAFBFF 0%, #EEF2FF 100%)",
    panelBg: "rgba(255, 255, 255, 0.8)",
    panelBorder: "rgba(224, 231, 255, 0.85)",
    sidebarBg: "rgba(255, 255, 255, 0.88)",
    headerBg: "rgba(255, 255, 255, 0.78)",
    textColor: "#0F172A",
    textMuted: "#64748B",
  },
  emerald: {
    primary: "#059669",
    secondary: "#0284c7",
    accent: "#6366f1",
    bgDark: "#F0FDF4",
    glow: "rgba(5, 150, 105, 0.25)",
    badgeBg: "rgba(5, 150, 105, 0.08)",
    badgeBorder: "rgba(5, 150, 105, 0.25)",
    badgeText: "#047857",
    isDark: false,
    bgGradient: "linear-gradient(180deg, #F0FDF4 0%, #ECFDF5 100%)",
    panelBg: "rgba(255, 255, 255, 0.82)",
    panelBorder: "rgba(209, 250, 229, 0.85)",
    sidebarBg: "rgba(255, 255, 255, 0.88)",
    headerBg: "rgba(255, 255, 255, 0.8)",
    textColor: "#064E3B",
    textMuted: "#047857",
  },
  cyberpunk: {
    primary: "#00f3ff",
    secondary: "#ff007f",
    accent: "#9d00ff",
    bgDark: "#04060e",
    glow: "rgba(0, 243, 255, 0.4)",
    badgeBg: "rgba(0, 243, 255, 0.15)",
    badgeBorder: "rgba(0, 243, 255, 0.35)",
    badgeText: "#00f3ff",
    isDark: true,
    bgGradient: "linear-gradient(180deg, #04060e 0%, #0c0818 100%)",
    panelBg: "rgba(12, 15, 30, 0.82)",
    panelBorder: "rgba(0, 243, 255, 0.22)",
    sidebarBg: "rgba(7, 9, 20, 0.94)",
    headerBg: "rgba(7, 9, 20, 0.88)",
    textColor: "#F8FAFC",
    textMuted: "#94A3B8",
  },
  gold: {
    primary: "#fbbf24",
    secondary: "#f59e0b",
    accent: "#d97706",
    bgDark: "#0b0a08",
    glow: "rgba(251, 191, 36, 0.35)",
    badgeBg: "rgba(251, 191, 36, 0.15)",
    badgeBorder: "rgba(251, 191, 36, 0.35)",
    badgeText: "#fbbf24",
    isDark: true,
    bgGradient: "linear-gradient(180deg, #0b0a08 0%, #17140e 100%)",
    panelBg: "rgba(22, 19, 14, 0.82)",
    panelBorder: "rgba(251, 191, 36, 0.25)",
    sidebarBg: "rgba(14, 12, 9, 0.94)",
    headerBg: "rgba(14, 12, 9, 0.88)",
    textColor: "#FEF3C7",
    textMuted: "#D97706",
  },
  aurora: {
    primary: "#38bdf8",
    secondary: "#10b981",
    accent: "#3b82f6",
    bgDark: "#040d18",
    glow: "rgba(56, 189, 248, 0.35)",
    badgeBg: "rgba(56, 189, 248, 0.15)",
    badgeBorder: "rgba(56, 189, 248, 0.35)",
    badgeText: "#38bdf8",
    isDark: true,
    bgGradient: "linear-gradient(180deg, #040d18 0%, #061826 100%)",
    panelBg: "rgba(7, 21, 36, 0.82)",
    panelBorder: "rgba(56, 189, 248, 0.25)",
    sidebarBg: "rgba(5, 15, 27, 0.94)",
    headerBg: "rgba(5, 15, 27, 0.88)",
    textColor: "#F0F9FF",
    textMuted: "#7DD3FC",
  },
  quantum: {
    primary: "#818cf8",
    secondary: "#00ff88",
    accent: "#38bdf8",
    bgDark: "#060713",
    glow: "rgba(129, 140, 248, 0.35)",
    badgeBg: "rgba(129, 140, 248, 0.15)",
    badgeBorder: "rgba(129, 140, 248, 0.35)",
    badgeText: "#a5b4fc",
    isDark: true,
    bgGradient: "linear-gradient(180deg, #060713 0%, #0d1026 100%)",
    panelBg: "rgba(15, 19, 40, 0.82)",
    panelBorder: "rgba(129, 140, 248, 0.22)",
    sidebarBg: "rgba(10, 13, 28, 0.94)",
    headerBg: "rgba(10, 13, 28, 0.88)",
    textColor: "#F1F5F9",
    textMuted: "#94A3B8",
  },
};

interface AppContextType {
  token: string | null;
  user: any | null;
  resumeId: string | null;
  resumeData: any | null;
  matchResults: any[] | null;
  groqApiKey: string;
  pineconeApiKey: string;
  openaiApiKey: string;
  anthropicApiKey: string;
  geminiApiKey: string;
  openrouterApiKey: string;
  primaryProvider: string;
  chatHistory: Message[];
  infraStatus: InfraStatus;
  theme: ThemeType;
  setTheme: (t: ThemeType) => void;
  currentThemeColors: ThemeColors;
  login: (token: string, user: any) => void;
  logout: () => void;
  setResume: (id: string, data: any) => void;
  setMatchResults: (results: any[]) => void;
  setGroqApiKey: (key: string) => void;
  setPineconeApiKey: (key: string) => void;
  setOpenaiApiKey: (key: string) => void;
  setAnthropicApiKey: (key: string) => void;
  setGeminiApiKey: (key: string) => void;
  setOpenrouterApiKey: (key: string) => void;
  setPrimaryProvider: (provider: string) => void;
  addChatMessage: (msg: Message) => void;
  clearChat: () => void;
  refreshDiagnostics: () => Promise<void>;
  apiBase: string;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const [token, setTokenState] = useState<string | null>(null);
  const [user, setUserState] = useState<any | null>(null);
  const [resumeId, setResumeIdState] = useState<string | null>(null);
  const [resumeData, setResumeDataState] = useState<any | null>(null);
  const [matchResults, setMatchResultsState] = useState<any[] | null>(null);
  const [groqApiKey, setGroqApiState] = useState<string>("");
  const [pineconeApiKey, setPineconeApiState] = useState<string>("");
  const [openaiApiKey, setOpenaiApiState] = useState<string>("");
  const [anthropicApiKey, setAnthropicApiState] = useState<string>("");
  const [geminiApiKey, setGeminiApiState] = useState<string>("");
  const [openrouterApiKey, setOpenrouterApiState] = useState<string>("");
  const [primaryProvider, setPrimaryProviderState] = useState<string>("groq");
  const [theme, setThemeState] = useState<ThemeType>("luminary");
  const [chatHistory, setChatHistoryState] = useState<Message[]>([]);
  const [infraStatus, setInfraStatus] = useState<InfraStatus>({
    backend: false,
    mongodb: false,
    redis: false,
    pinecone: false,
    groq: false,
    gemini: false,
    openai: false,
    anthropic: false,
    openrouter: false,
  });

  useEffect(() => {
    if (typeof window !== "undefined") {
      setTokenState(localStorage.getItem("token"));
      try {
        const u = localStorage.getItem("user");
        if (u) setUserState(JSON.parse(u));
        const rData = localStorage.getItem("resumeData");
        if (rData) setResumeDataState(JSON.parse(rData));
      } catch (_) {}
      setResumeIdState(localStorage.getItem("resumeId"));
      setGroqApiState(localStorage.getItem("groqApiKey") || "");
      setPineconeApiState(localStorage.getItem("pineconeApiKey") || "");
      setOpenaiApiKey(localStorage.getItem("openaiApiKey") || "");
      setAnthropicApiKey(localStorage.getItem("anthropicApiKey") || "");
      setGeminiApiKey(localStorage.getItem("geminiApiKey") || "");
      setOpenrouterApiState(localStorage.getItem("openrouterApiKey") || "");
      setPrimaryProviderState(localStorage.getItem("primaryProvider") || "groq");
      setThemeState((localStorage.getItem("theme") as ThemeType) || "luminary");
      try {
        const h = localStorage.getItem("chatHistory");
        if (h) setChatHistoryState(JSON.parse(h));
      } catch (_) {}
    }
    
    refreshDiagnostics();
    const interval = setInterval(() => {
      refreshDiagnostics();
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const colors = themePresets[theme] || themePresets.luminary;
    const root = document.documentElement;

    root.setAttribute("data-theme", theme);
    if (colors.isDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }

    root.style.setProperty("--color-indigo", colors.primary);
    root.style.setProperty("--color-indigo-primary", colors.primary);
    root.style.setProperty("--color-teal", colors.secondary);
    root.style.setProperty("--color-teal-secondary", colors.secondary);
    root.style.setProperty("--color-coral-accent", colors.accent);
    root.style.setProperty("--glow-color", colors.glow);

    root.style.setProperty("--theme-primary", colors.primary);
    root.style.setProperty("--theme-secondary", colors.secondary);
    root.style.setProperty("--theme-accent", colors.accent);
    root.style.setProperty("--theme-bg", colors.bgDark);
    root.style.setProperty("--theme-bg-gradient", colors.bgGradient || colors.bgDark);
    root.style.setProperty("--theme-glow", colors.glow);
    root.style.setProperty("--theme-badge-bg", colors.badgeBg);
    root.style.setProperty("--theme-badge-border", colors.badgeBorder);
    root.style.setProperty("--theme-badge-text", colors.badgeText);
    root.style.setProperty("--theme-panel-bg", colors.panelBg || "rgba(255, 255, 255, 0.8)");
    root.style.setProperty("--theme-panel-border", colors.panelBorder || "rgba(224, 231, 255, 0.85)");
    root.style.setProperty("--theme-sidebar-bg", colors.sidebarBg || "rgba(255, 255, 255, 0.88)");
    root.style.setProperty("--theme-header-bg", colors.headerBg || "rgba(255, 255, 255, 0.78)");
    root.style.setProperty("--theme-text", colors.textColor || "#0F172A");
    root.style.setProperty("--theme-text-muted", colors.textMuted || "#64748B");
    root.style.setProperty("--background", colors.bgDark);
    root.style.setProperty("--foreground", colors.textColor || "#0F172A");

    document.body.style.background = colors.bgGradient || colors.bgDark;
    document.body.style.color = colors.textColor || "#0F172A";
  }, [theme]);

  const setTheme = (t: ThemeType) => {
    setThemeState(t);
    localStorage.setItem("theme", t);
  };

  const login = (t: string, u: any) => {
    setTokenState(t);
    setUserState(u);
    localStorage.setItem("token", t);
    localStorage.setItem("user", JSON.stringify(u));
  };

  const logout = () => {
    setTokenState(null);
    setUserState(null);
    setResumeIdState(null);
    setResumeDataState(null);
    setMatchResultsState(null);
    setChatHistoryState([]);
    localStorage.clear();
  };

  const setResume = (id: string, data: any) => {
    setResumeIdState(id);
    setResumeDataState(data);
    localStorage.setItem("resumeId", id);
    localStorage.setItem("resumeData", JSON.stringify(data));
  };

  const setMatchResults = (results: any[]) => {
    setMatchResultsState(results);
  };

  const setGroqApiKey = (key: string) => {
    setGroqApiState(key);
    localStorage.setItem("groqApiKey", key);
  };

  const setPineconeApiKey = (key: string) => {
    setPineconeApiState(key);
    localStorage.setItem("pineconeApiKey", key);
  };

  const setOpenaiApiKey = (key: string) => {
    setOpenaiApiState(key);
    localStorage.setItem("openaiApiKey", key);
  };

  const setAnthropicApiKey = (key: string) => {
    setAnthropicApiState(key);
    localStorage.setItem("anthropicApiKey", key);
  };

  const setGeminiApiKey = (key: string) => {
    setGeminiApiState(key);
    localStorage.setItem("geminiApiKey", key);
  };

  const setOpenrouterApiKey = (key: string) => {
    setOpenrouterApiState(key);
    localStorage.setItem("openrouterApiKey", key);
  };

  const setPrimaryProvider = (provider: string) => {
    setPrimaryProviderState(provider);
    localStorage.setItem("primaryProvider", provider);
  };

  const addChatMessage = (msg: Message) => {
    setChatHistoryState((prev) => {
      const updated = [...prev, msg];
      localStorage.setItem("chatHistory", JSON.stringify(updated));
      return updated;
    });
  };

  const clearChat = () => {
    setChatHistoryState([]);
    localStorage.removeItem("chatHistory");
  };

  const refreshDiagnostics = async () => {
    let backendOnline = false;
    let mongodbOnline = false;
    let redisOnline = false;
    let pineconeOnline = false;
    let groqOnline = false;
    let geminiOnline = false;
    let openaiOnline = false;
    let anthropicOnline = false;
    let openrouterOnline = false;

    try {
      const res = await fetch(`${apiBase}/health`, { signal: AbortSignal.timeout(3000) });
      if (res.status === 200) {
        backendOnline = true;
        const body = await res.json();
        const services = body?.data?.services || {};
        const providers = body?.data?.providers || {};
        
        mongodbOnline = !!services.mongodb;
        redisOnline = !!services.redis;
        pineconeOnline = !!services.pinecone || !!providers.pinecone;
        groqOnline = !!services.groq || !!providers.groq;
        geminiOnline = !!providers.gemini;
        openaiOnline = !!providers.openai;
        anthropicOnline = !!providers.anthropic;
        openrouterOnline = !!providers.openrouter;
      }
    } catch (_) {}

    // Fallback detection from client-entered keys if user explicitly supplied any
    if (pineconeApiKey && pineconeApiKey.trim().length > 10) pineconeOnline = true;
    if (groqApiKey && groqApiKey.trim().length > 10) groqOnline = true;
    if (geminiApiKey && geminiApiKey.trim().length > 10) geminiOnline = true;
    if (openaiApiKey && openaiApiKey.trim().length > 10) openaiOnline = true;
    if (anthropicApiKey && anthropicApiKey.trim().length > 10) anthropicOnline = true;
    if (openrouterApiKey && openrouterApiKey.trim().length > 10) openrouterOnline = true;

    setInfraStatus({
      backend: backendOnline,
      mongodb: mongodbOnline,
      redis: redisOnline,
      pinecone: pineconeOnline,
      groq: groqOnline,
      gemini: geminiOnline,
      openai: openaiOnline,
      anthropic: anthropicOnline,
      openrouter: openrouterOnline,
    });
  };

  return (
    <AppContext.Provider
      value={{
        token,
        user,
        resumeId,
        resumeData,
        matchResults,
        groqApiKey,
        pineconeApiKey,
        openaiApiKey,
        anthropicApiKey,
        geminiApiKey,
        openrouterApiKey,
        primaryProvider,
        chatHistory,
        infraStatus,
        theme,
        setTheme,
        currentThemeColors: themePresets[theme] || themePresets.cyberpunk,
        login,
        logout,
        setResume,
        setMatchResults,
        setGroqApiKey,
        setPineconeApiKey,
        setOpenaiApiKey,
        setAnthropicApiKey,
        setGeminiApiKey,
        setOpenrouterApiKey,
        setPrimaryProvider,
        addChatMessage,
        clearChat,
        refreshDiagnostics,
        apiBase,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error("useApp must be used within an AppProvider");
  }
  return context;
};
