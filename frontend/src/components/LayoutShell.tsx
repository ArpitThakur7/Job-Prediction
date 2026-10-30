"use client";

import React, { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Briefcase,
  FileSearch,
  FileText,
  Home,
  LayoutList,
  LogOut,
  Menu,
  ScanSearch,
  Settings,
  UserRound,
  X,
  type LucideIcon,
} from "lucide-react";
import { useApp } from "@/context/AppContext";
import ThemeSwitcher from "@/components/3d/ThemeSwitcher";

type NavItem = { name: string; href: string; icon: LucideIcon; desc?: string };

const navGroups: { label: string; items: NavItem[] }[] = [
  {
    label: "Find work",
    items: [
      { name: "Home", href: "/", icon: Home },
      { name: "Job feed", href: "/jobs", icon: Briefcase },
      { name: "Tracker", href: "/applications", icon: LayoutList },
    ],
  },
  {
    label: "Your resume",
    items: [
      { name: "Resume studio", href: "/resume", icon: FileText, desc: "Edit and export your resume" },
      { name: "Resume check", href: "/analyzer", icon: ScanSearch, desc: "Find skill gaps against real jobs" },
      { name: "Job post reader", href: "/parser", icon: FileSearch, desc: "Pull requirements out of a posting" },
    ],
  },
  {
    label: "Help",
    items: [{ name: "Career coach", href: "/coach", icon: Bot, desc: "Ask about interviews and resumes" }],
  },
];

const footerNav: NavItem[] = [
  { name: "Account", href: "/account", icon: UserRound, desc: "Profile and sign-in" },
  { name: "Settings", href: "/settings", icon: Settings, desc: "Keys, engine and services" },
];

const mobilePrimary: NavItem[] = [
  { name: "Home", href: "/", icon: Home },
  { name: "Jobs", href: "/jobs", icon: Briefcase },
  { name: "Tracker", href: "/applications", icon: LayoutList },
  { name: "Resume", href: "/resume", icon: FileText },
];

const mobileMore: NavItem[] = [...navGroups[1].items.slice(1), ...navGroups[2].items, ...footerNav];

const pageTitles: Record<string, string> = {
  "/jobs": "Job feed",
  "/job-board": "Job feed",
  "/applications": "Application tracker",
  "/resume": "Resume studio",
  "/analyzer": "Resume check",
  "/parser": "Job post reader",
  "/coach": "Career coach",
  "/account": "Account",
  "/settings": "Settings",
  "/settings/salvo": "Salvo engine settings",
};

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(href + "/");
}

export const LayoutShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const pathname = usePathname();
  const { infraStatus, user, logout, currentThemeColors } = useApp();
  const [moreOpen, setMoreOpen] = useState(false);

  const title = pathname.startsWith("/jobs/") ? "Job details" : pageTitles[pathname];
  const moreActive = mobileMore.some((i) => isActive(pathname, i.href));

  return (
    <div className="relative flex min-h-screen overflow-x-clip" style={{ color: "var(--theme-text, #0F172A)" }}>
      {/* Colour fields behind the glass */}
      <div className="mesh-field" aria-hidden>
        <span style={{ width: "46vw", height: "46vw", left: "-12vw", top: "-14vw", background: currentThemeColors.primary }} />
        <span style={{ width: "38vw", height: "38vw", right: "-10vw", top: "18vh", background: currentThemeColors.accent, animationDelay: "-8s" }} />
        <span style={{ width: "34vw", height: "34vw", left: "30vw", bottom: "-16vw", background: currentThemeColors.secondary, animationDelay: "-16s" }} />
      </div>

      {/* Desktop sidebar */}
      <aside className="hidden min-[821px]:flex sticky top-0 h-screen w-[248px] shrink-0 p-3 z-20">
        <div className="glass-strong flex flex-col w-full rounded-[28px] p-4">
          <Link href="/" className="flex items-center gap-2.5 px-2 pt-1 pb-5">
            <FletchMark color={currentThemeColors.primary} accent={currentThemeColors.secondary} />
            <span className="font-display text-[22px] font-extrabold leading-none">Fletch</span>
          </Link>

          <nav className="flex-1 overflow-y-auto space-y-5 pr-1" aria-label="Main">
            {navGroups.map((group) => (
              <div key={group.label}>
                <p className="px-3 mb-1.5 text-xs font-medium" style={{ color: "var(--theme-text-muted)" }}>
                  {group.label}
                </p>
                <ul className="space-y-0.5">
                  {group.items.map((item) => (
                    <li key={item.href}>
                      <SideLink item={item} active={isActive(pathname, item.href)} color={currentThemeColors.primary} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>

          <div className="pt-3 mt-3 space-y-0.5 border-t" style={{ borderColor: "var(--glass-line)" }}>
            {footerNav.map((item) => (
              <SideLink key={item.href} item={item} active={isActive(pathname, item.href)} color={currentThemeColors.primary} />
            ))}
            <div className="flex items-center justify-between gap-2 px-2 pt-3">
              <ServiceStatus status={infraStatus} />
              {user && (
                <button
                  onClick={() => logout()}
                  className="p-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/10 transition-colors"
                  title="Sign out"
                  aria-label="Sign out"
                >
                  <LogOut size={16} />
                </button>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main column */}
      {/* No z-index here: page overlays (drawers, sheets) must be able to cover the sidebar. */}
      <div className="relative flex-1 flex flex-col min-w-0 pb-24 min-[821px]:pb-8">
        <header className="flex items-center justify-between gap-3 px-4 sm:px-6 min-[821px]:px-8 pt-4 pb-2 min-[821px]:pt-6">
          <div className="flex items-center gap-2 min-w-0">
            <Link href="/" className="min-[821px]:hidden flex items-center gap-2 mr-1" aria-label="Fletch home">
              <FletchMark color={currentThemeColors.primary} accent={currentThemeColors.secondary} />
            </Link>
            {title && <h1 className="font-display text-xl sm:text-2xl font-bold truncate">{title}</h1>}
          </div>
          <div className="flex items-center gap-2">
            <div className="hidden sm:block">
              <ThemeSwitcher />
            </div>
            <div className="min-[821px]:hidden">
              <ServiceStatus status={infraStatus} compact />
            </div>
            <Link
              href="/account"
              className="glass flex items-center gap-2 pl-1.5 pr-3 py-1.5 rounded-full text-sm font-semibold"
            >
              <span
                className="w-7 h-7 rounded-full grid place-items-center text-white text-xs font-bold"
                style={{ background: `linear-gradient(135deg, ${currentThemeColors.primary}, ${currentThemeColors.accent})` }}
              >
                {user?.full_name?.charAt(0).toUpperCase() || <UserRound size={14} />}
              </span>
              <span className="hidden sm:inline">{user ? user.full_name?.split(" ")[0] : "Sign in"}</span>
            </Link>
          </div>
        </header>

        <main className="flex-1 px-3 sm:px-6 min-[821px]:px-8 pt-2 pb-6 fade-in">{children}</main>
      </div>

      {/* Mobile bottom bar */}
      <nav
        className="glass-strong fixed bottom-3 left-3 right-3 z-40 rounded-3xl flex justify-around items-center min-[821px]:hidden"
        style={{ paddingBottom: "max(6px, env(safe-area-inset-bottom))", paddingTop: 6 }}
        aria-label="Main"
      >
        {mobilePrimary.map((item) => {
          const active = isActive(pathname, item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex flex-col items-center gap-0.5 px-3 py-1 text-[11px] font-semibold min-w-[56px]"
              style={{ color: active ? currentThemeColors.primary : "var(--theme-text-muted)" }}
              aria-current={active ? "page" : undefined}
            >
              <Icon size={20} strokeWidth={active ? 2.4 : 1.8} />
              {item.name}
            </Link>
          );
        })}
        <button
          onClick={() => setMoreOpen(true)}
          className="flex flex-col items-center gap-0.5 px-3 py-1 text-[11px] font-semibold min-w-[56px]"
          style={{ color: moreActive ? currentThemeColors.primary : "var(--theme-text-muted)" }}
          aria-expanded={moreOpen}
        >
          <Menu size={20} />
          More
        </button>
      </nav>

      {moreOpen && (
        <div className="fixed inset-0 z-50 min-[821px]:hidden flex flex-col justify-end bg-black/30 backdrop-blur-sm" onClick={() => setMoreOpen(false)}>
          <div
            className="glass-strong rounded-t-[28px] p-5 pb-10 space-y-4"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="More pages"
          >
            <div className="flex items-center justify-between">
              <span className="font-display text-lg font-bold">More</span>
              <button onClick={() => setMoreOpen(false)} className="p-2 rounded-full hover:bg-black/5" aria-label="Close">
                <X size={18} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {mobileMore.map((item) => {
                const Icon = item.icon;
                const active = isActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMoreOpen(false)}
                    className="glass rounded-2xl p-3 flex flex-col gap-1"
                    style={active ? { borderColor: currentThemeColors.primary } : undefined}
                  >
                    <span className="flex items-center gap-2 font-semibold text-sm">
                      <Icon size={16} style={{ color: currentThemeColors.primary }} />
                      {item.name}
                    </span>
                    {item.desc && <span className="text-xs" style={{ color: "var(--theme-text-muted)" }}>{item.desc}</span>}
                  </Link>
                );
              })}
            </div>
            <ThemeSwitcher />
          </div>
        </div>
      )}
    </div>
  );
};

function SideLink({ item, active, color }: { item: NavItem; active: boolean; color: string }) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      aria-current={active ? "page" : undefined}
      className="relative flex items-center gap-3 px-3 py-2 rounded-2xl text-[15px] font-medium transition-colors hover:bg-black/[0.04] dark:hover:bg-white/[0.06]"
      style={
        active
          ? { background: `${color}18`, color, fontWeight: 650 }
          : { color: "var(--theme-text)" }
      }
    >
      <Icon size={18} strokeWidth={active ? 2.3 : 1.8} />
      {item.name}
    </Link>
  );
}

type Infra = { backend: boolean; mongodb: boolean; pinecone: boolean; groq: boolean };

function ServiceStatus({ status, compact = false }: { status: Infra; compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const services: [string, boolean][] = [
    ["Prediction API", status.backend],
    ["Database", status.mongodb],
    ["Vector search", status.pinecone],
    ["AI writer", status.groq],
  ];
  const up = services.filter(([, ok]) => ok).length;
  const allUp = up === services.length;
  const color = allUp ? "var(--fit-high)" : up === 0 ? "#E5484D" : "var(--fit-mid)";

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={`flex items-center gap-2 rounded-full text-xs font-medium ${compact ? "glass p-2.5" : "px-2 py-1.5 hover:bg-black/5 dark:hover:bg-white/10"}`}
        aria-expanded={open}
        aria-label={`${up} of ${services.length} services running`}
      >
        <span className="w-2 h-2 rounded-full" style={{ background: color, boxShadow: `0 0 0 3px color-mix(in srgb, ${color} 25%, transparent)` }} />
        {!compact && (allUp ? "All services on" : `${up} of ${services.length} services on`)}
      </button>
      {open && (
        <div className={`glass-strong absolute z-50 w-56 rounded-2xl p-3 space-y-2 text-sm ${compact ? "right-0 top-12" : "left-0 bottom-10"}`}>
          {services.map(([name, ok]) => (
            <div key={name} className="flex items-center justify-between">
              <span>{name}</span>
              <span className="text-xs font-semibold" style={{ color: ok ? "var(--fit-high)" : "#E5484D" }}>
                {ok ? "Running" : "Offline"}
              </span>
            </div>
          ))}
          {!allUp && (
            <Link href="/settings" className="block pt-2 text-xs font-semibold" style={{ color: "var(--theme-primary)" }}>
              Open settings to fix
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

/** An arrow's arc with its fletching trail — one shot, aimed. */
function FletchMark({ color, accent }: { color: string; accent: string }) {
  // Unique per instance: the sidebar copy is display:none on mobile and would swallow a shared id.
  const id = "fletch-g" + useId().replace(/[^a-zA-Z0-9_-]/g, "");
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden>
      <defs>
        <linearGradient id={id} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor={color} />
          <stop offset="1" stopColor={accent} />
        </linearGradient>
      </defs>
      <rect width="32" height="32" rx="10" fill={`url(#${id})`} />
      <path d="M7 23c4-9 9-13 18-14" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" fill="none" />
      <path d="M7 18c3-5 6-7 11-8" stroke="#fff" strokeOpacity=".7" strokeWidth="2.4" strokeLinecap="round" fill="none" />
      <circle cx="25" cy="9" r="2.6" fill="#fff" />
    </svg>
  );
}

export default LayoutShell;
