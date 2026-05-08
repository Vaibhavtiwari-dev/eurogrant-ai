"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Link from "next/link";
import { motion } from "framer-motion";
import { Mail, Lock, ShieldCheck, Zap } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login, bypassLogin } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const res = await login(email, password);
    if (!res.success) {
      setError(res.error || "Intelligence access denied");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative bg-background overflow-hidden">
      {/* Premium Ambient Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-900/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-slate-900/30 rounded-full blur-[120px]" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="max-w-md w-full z-10"
      >
        <div className="text-center mb-12">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            className="inline-block mb-4"
          >
            <div className="p-3 rounded-2xl bg-surface-container-high border border-glass-border shadow-luxury">
              <ShieldCheck className="text-primary w-8 h-8" />
            </div>
          </motion.div>
          <h1 className="font-headline-lg text-4xl text-white font-black tracking-tight mb-3">
            EUROGRANT <span className="text-secondary italic font-light">AI</span>
          </h1>
          <p className="font-label-sm text-[10px] text-secondary tracking-[0.3em] uppercase opacity-70">
            Elite Intelligence Portal
          </p>
        </div>

        <motion.div 
          whileHover={{ 
            rotateX: 2, 
            rotateY: -2,
            transition: { duration: 0.4 }
          }}
          style={{ perspective: 1000 }}
          className="glass-card rounded-2xl p-10 border border-glass-border relative overflow-hidden"
        >
          {/* Subtle Metallic Shine Effect */}
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
          
          <div className="flex items-center gap-4 mb-10">
            <h2 className="font-headline-md text-2xl text-white">Sign In</h2>
            <div className="h-[1px] flex-1 bg-gradient-to-r from-white/10 to-transparent" />
          </div>

          <form className="space-y-8" onSubmit={handleSubmit}>
            {error && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="bg-error-container/20 border border-error/20 text-error text-[10px] font-black uppercase tracking-widest p-4 rounded-xl text-center"
              >
                {error}
              </motion.div>
            )}
            
            <div className="space-y-5">
              <div className="group relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors">
                  <Mail size={18} />
                </div>
                <input
                  type="email"
                  required
                  className="w-full bg-surface-container-low/40 border border-glass-border rounded-xl py-4 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/30 transition-all font-body-md text-sm"
                  placeholder="Intelligence ID (Email)"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              
              <div className="group relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  required
                  className="w-full bg-surface-container-low/40 border border-glass-border rounded-xl py-4 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/30 transition-all font-body-md text-sm"
                  placeholder="Security Key (Password)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-4">
              <button
                type="submit"
                className="group relative w-full py-5 bg-white text-background font-black uppercase tracking-[0.2em] text-[10px] rounded-xl overflow-hidden transition-all hover:scale-[1.02] active:scale-[0.98] shadow-luxury"
              >
                <span className="relative z-10">Authorize Access</span>
                <div className="absolute inset-0 bg-gradient-to-r from-slate-200 to-white opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>

              <button
                type="button"
                onClick={bypassLogin}
                className="w-full py-4 bg-surface-container-high/50 text-slate-300 font-bold uppercase tracking-widest text-[9px] rounded-xl border border-glass-border hover:bg-slate-800 hover:text-white transition-all flex items-center justify-center gap-2"
              >
                <Zap size={14} className="text-secondary" />
                Quick Entry (Dev Mode)
              </button>
            </div>
          </form>

          <div className="mt-10 text-center">
            <Link href="/register" className="group inline-flex items-center gap-2 font-label-sm text-[9px] text-slate-500 hover:text-white uppercase tracking-[0.2em] transition-all">
              <span>Request Intelligence Access</span>
              <div className="w-4 h-[1px] bg-slate-700 group-hover:bg-white group-hover:w-8 transition-all" />
            </Link>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
