"use client";

import React from "react";
import { motion } from "framer-motion";
import { useTranslations } from "next-intl";
import { 
  Menu, 
  Search, 
  Bell, 
  HelpCircle
} from "lucide-react";

interface HeaderProps {
  user: { full_name?: string | null; email: string } | null;
  setIsSidebarOpen: (open: boolean) => void;
}

export default function Header({ user, setIsSidebarOpen }: HeaderProps) {
  const t = useTranslations("Header");

  return (
    <motion.header 
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="md:ml-64 h-20 sticky top-0 z-40 bg-surface/80 backdrop-blur-md flex justify-between items-center px-12 border-b border-outline"
    >
      <div className="flex items-center flex-1 max-w-2xl">
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="md:hidden mr-6 p-2 rounded-lg text-emerald-light hover:bg-emerald/5 transition-colors"
          aria-label={t("toggleSidebar")}
        >
          <Menu size={24} />
        </button>
        
        <div className="relative w-full hidden md:block">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant opacity-40" size={18} />
          <input 
            className="w-full pl-12 pr-4 py-2.5 rounded-full bg-surface-variant/50 border border-outline text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-emerald-light/30 focus:ring-4 focus:ring-emerald-light/5 transition-all" 
            placeholder="Search proposals, grants, or keywords..." 
            type="text"
          />
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <button className="p-2.5 rounded-full text-on-surface-variant hover:text-emerald-light hover:bg-emerald/5 transition-all relative">
            <Bell size={20} />
            <span className="absolute top-2 right-2 w-2 h-2 bg-copper rounded-full ring-4 ring-surface"></span>
          </button>
          <button className="p-2.5 rounded-full text-on-surface-variant hover:text-emerald-light hover:bg-emerald/5 transition-all">
            <HelpCircle size={20} />
          </button>
        </div>

        <div className="h-8 w-[1px] bg-outline mx-2" />

        <button className="flex items-center gap-3 group" title={user?.full_name || "User Profile"}>
          <div className="w-10 h-10 rounded-full bg-emerald/10 border border-emerald/20 flex items-center justify-center transition-all group-hover:border-emerald-light/50 overflow-hidden">
             {/* eslint-disable-next-line @next/next/no-img-element */}
             <img 
               src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-1.2.1&auto=format&fit=facearea&facepad=2&w=256&h=256&q=80" 
               alt={user?.full_name || "User Profile"}
               className="w-full h-full object-cover"
             />
          </div>
        </button>
      </div>
    </motion.header>
  );
}
