"use client";

import React, { useState, useEffect } from "react";
import { motion, useReducedMotion, AnimatePresence } from "framer-motion";
import DocumentUpload from "@/components/DocumentUpload";
import DocumentList from "@/components/DocumentList";
import CompanyProfile from "@/components/CompanyProfile";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { 
  BrainCircuit, 
  Compass, 
  Briefcase, 
  LineChart, 
  Upload, 
  Search, 
  Bell, 
  Settings, 
  Menu,
  X,
  ChevronRight,
  Plus,
  LogOut
} from "lucide-react";

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2,
    },
  },
};

const sidebarVariants = {
  open: { 
    x: 0,
    transition: { type: "spring" as const, stiffness: 300, damping: 30 }
  },
  closed: { 
    x: "-100%",
    transition: { type: "spring" as const, stiffness: 300, damping: 30 }
  }
};

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const shouldReduceMotion = useReducedMotion();
  const [refreshKey, setRefreshKey] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const itemVariants = {
    hidden: { opacity: 0, y: shouldReduceMotion ? 0 : 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        duration: 0.5,
        ease: "easeOut" as const,
      },
    },
  };

  const handleUploadSuccess = () => {
    setRefreshKey(prev => prev + 1);
    setIsProcessing(true);
    setIsUploadModalOpen(false);
  };

  const checkProcessingStatus = async () => {
    try {
      const response = await apiFetch("/uploads/documents");
      if (response.ok) {
        const docs = await response.json();
        const pending = docs.some((doc: any) => doc.status === "pending");
        
        if (!pending && isProcessing) {
            setIsProcessing(false);
            setRefreshKey(prev => prev + 1);
        } else if (pending) {
            setIsProcessing(true);
        }
      }
    } catch (error) {
      console.error("Failed to check processing status:", error);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isProcessing) {
      interval = setInterval(checkProcessingStatus, 5000);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  // Get user initials for profile
  const getInitials = () => {
    if (!user) return "??";
    if (user.full_name) {
      return user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    return user.email.slice(0, 2).toUpperCase();
  };

  return (
    <div className="min-h-screen text-on-background relative">
      {/* Sidebar Navigation */}
      <motion.nav 
        initial={false}
        animate={isMobile ? (isSidebarOpen ? "open" : "closed") : "open"}
        variants={sidebarVariants}
        className="fixed left-0 top-0 h-screen w-64 z-50 glass-sidebar flex flex-col py-8"
      >
        <div className="px-6 mb-12">
          <div className="flex items-center gap-3">
            <div className="bg-white/10 p-2 rounded-lg shadow-sm border border-white/10">
              <BrainCircuit className="text-white h-6 w-6" />
            </div>
            <div>
              <h1 className="text-lg font-headline-lg italic text-white leading-tight">EuroGrant AI</h1>
              <p className="text-[10px] text-slate-300 font-label-sm uppercase tracking-widest mt-0.5">Elite Intelligence</p>
            </div>
          </div>
        </div>
        
        <div className="flex-1 px-4 space-y-2">
          <SidebarItem icon={<BrainCircuit size={18} />} label="Intelligence" active />
          <SidebarItem icon={<Compass size={18} />} label="Discovery" />
          <SidebarItem icon={<Briefcase size={18} />} label="Workbench" />
          <SidebarItem icon={<LineChart size={18} />} label="Analytics" />
        </div>

        <div className="px-4 mt-auto space-y-4">
          <motion.button 
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setIsUploadModalOpen(true)}
            className="w-full py-3 px-4 rounded-lg bg-slate-800/50 border border-white/20 text-white text-sm font-headline-md hover:bg-slate-700/60 transition-colors flex items-center justify-center gap-2 group"
          >
            <span>Submit Documentation</span>
            <Upload size={14} className="group-hover:translate-y-[-2px] transition-transform" />
          </motion.button>
          
          <button 
            onClick={logout}
            className="w-full py-2 px-4 rounded-lg text-slate-300 text-xs font-label-sm hover:text-white hover:bg-white/10 transition-colors flex items-center justify-center gap-2"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </motion.nav>

      {/* Top Header */}
      <motion.header 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="md:ml-64 h-20 sticky top-0 z-40 bg-transparent flex justify-between items-center px-10 text-slate-200 font-headline-md tracking-wide transition-all duration-300"
      >
        <div className="flex items-center">
          <Menu className="md:hidden mr-4 cursor-pointer text-white" onClick={() => setIsSidebarOpen(true)} />
          <h2 className="text-xl text-white opacity-90 hidden md:block text-shadow-sm">Dashboard</h2>
        </div>
        <div className="flex items-center gap-6">
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input 
              className="pl-10 pr-4 py-2 rounded-full bg-slate-900/50 border border-slate-700 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 w-64 backdrop-blur-md transition-all focus:w-80" 
              placeholder="Search insights..." 
              type="text"
            />
          </div>
          <div className="flex items-center gap-4">
            <button className="p-2 rounded-full text-slate-300 hover:bg-slate-800/40 transition-colors relative">
              <Bell size={18} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-sky-400 rounded-full"></span>
            </button>
            <button className="p-2 rounded-full text-slate-300 hover:bg-slate-800/40 transition-colors">
              <Settings size={18} />
            </button>
            <div className="flex items-center gap-3 ml-2 group cursor-pointer">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-medium text-white group-hover:text-sky-300 transition-colors leading-none">{user?.full_name || "Authorized Agent"}</p>
                <p className="text-[10px] text-slate-300 font-label-sm uppercase tracking-tighter mt-1">Level 4 Clearance</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-slate-800 border border-white/20 flex items-center justify-center alpine-shadow group-hover:border-sky-400 transition-all">
                <span className="text-sm font-bold text-white group-hover:text-sky-300">{getInitials()}</span>
              </div>
            </div>
          </div>
        </div>
      </motion.header>

      {/* Main Content Area */}
      <motion.main 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 md:ml-64 pt-8 px-12 pb-24 min-h-screen"
      >
        <div className="max-w-7xl mx-auto space-y-12">
          {/* Page Header */}
          <motion.div variants={itemVariants} className="flex items-baseline justify-between border-b border-white/10 pb-6">
            <div>
              <p className="font-body-lg text-body-lg text-slate-200 mt-2 text-shadow-sm">Executive Intelligence Dashboard</p>
            </div>
            <div className="flex gap-4">
              <button className="px-6 py-2.5 rounded-full border border-white/20 text-white font-label-sm text-label-sm hover:bg-white/5 transition-colors">Export Report</button>
              <button className="px-6 py-2.5 rounded-full bg-slate-800 text-white font-label-sm text-label-sm hover:bg-slate-700 transition-colors shadow-lg flex items-center gap-2">
                <Plus size={14} />
                New Analysis
              </button>
            </div>
          </motion.div>

          {/* Dashboard Grid */}
          <div className="grid grid-cols-12 gap-8">
            {/* Probability Indicator (Span 4) */}
            <motion.div variants={itemVariants} className="col-span-12 lg:col-span-4 h-full">
              <div className="glass-card rounded-2xl p-8 h-full flex flex-col items-center justify-center relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-b from-transparent to-slate-900/50 pointer-events-none"></div>
                <h3 className="font-headline-md text-headline-md text-slate-300 mb-8 self-start absolute top-8 left-8 text-shadow-sm">Global Probability</h3>
                <div className="relative w-48 h-48 mt-12 flex items-center justify-center">
                  {/* Glowing Ring */}
                  <div className="absolute inset-0 rounded-full neon-ring animate-[spin_10s_linear_infinite]"></div>
                  {/* Inner Dark Circle to mask ring */}
                  <div className="absolute inset-2 rounded-full bg-surface-container-low z-10"></div>
                  <div className="relative z-20 text-center">
                    <span className="font-display-xl text-5xl text-white">94</span><span className="font-headline-lg text-slate-400">%</span>
                    <p className="font-label-sm text-label-sm text-sky-400 mt-2 uppercase tracking-widest">Optimal</p>
                  </div>
                </div>
                <p className="font-body-md text-body-md text-slate-300 text-center mt-8 z-10">Based on active parameters across EU frameworks.</p>
              </div>
            </motion.div>

            {/* Discovery Feed (Span 8) - DocumentList Integration */}
            <motion.div variants={itemVariants} className="col-span-12 lg:col-span-8">
              <DocumentList refreshKey={refreshKey} />
            </motion.div>

            {/* Health Profile Integration (Span 12) - CompanyProfile Integration */}
            <motion.div variants={itemVariants} className="col-span-12">
              <div className="glass-card rounded-2xl p-8">
                <div className="flex justify-between items-center mb-8 border-b border-white/10 pb-4">
                  <h3 className="font-headline-md text-headline-md text-slate-300 text-shadow-sm">Company Intelligence Profile</h3>
                  <button className="text-sky-400 font-label-sm text-label-sm hover:text-sky-300 transition-colors">View Deep Dive</button>
                </div>
                <CompanyProfile refreshKey={refreshKey} />
              </div>
            </motion.div>
          </div>
        </div>
      </motion.main>

      {/* Upload Modal Overlay */}
      <AnimatePresence>
        {isUploadModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" 
              onClick={() => setIsUploadModalOpen(false)}
            ></motion.div>
            <motion.div 
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="relative w-full max-w-2xl glass-card rounded-2xl p-8"
            >
              <button 
                onClick={() => setIsUploadModalOpen(false)}
                className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
              >
                <X size={24} />
              </button>
              <div className="mb-8">
                <h2 className="text-2xl font-headline-lg text-white mb-2">Submit Documentation</h2>
                <p className="text-slate-300 text-sm">Upload your business plan, pitch deck, or financials for AI-driven extraction.</p>
              </div>
              <DocumentUpload onUploadSuccess={handleUploadSuccess} />
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Mobile Sidebar Close Overlay */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[45] bg-black/60 md:hidden" 
            onClick={() => setIsSidebarOpen(false)}
          ></motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SidebarItem({ icon, label, active = false }: { icon: React.ReactNode; label: string; active?: boolean }) {
  return (
    <motion.a 
      whileHover={{ 
        x: 4,
        backgroundColor: "rgba(255, 255, 255, 0.05)",
      }}
      whileTap={{ scale: 0.98 }}
      href="#" 
      className={`relative flex items-center gap-4 px-4 py-3 rounded-xl font-medium transition-all duration-300 ease-out group ${
        active 
          ? "text-white bg-white/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.15)] border border-white/10" 
          : "text-slate-400 hover:text-white"
      }`}
    >
      <span className={`transition-all duration-300 ${active ? "text-white scale-110 drop-shadow-[0_0_8px_rgba(255,255,255,0.5)]" : "text-slate-500 group-hover:text-slate-300"}`}>
        {icon}
      </span>
      <span className="text-sm tracking-wide">{label}</span>
      {active && (
        <motion.div 
          layoutId="activeTab"
          className="absolute left-0 w-1 h-6 bg-sky-400 rounded-r-full shadow-[0_0_12px_rgba(56,189,248,0.8)]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        />
      )}
    </motion.a>
  );
}
