"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Link, useRouter } from "@/i18n/routing";
import { motion } from "framer-motion";
import { Mail, Lock, User, Building, KeyRound, ArrowRight } from "lucide-react";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState("");
  const { register } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const res = await register(email, password, fullName, organizationName, inviteCode);
    if (res.success) {
      router.push("/login");
    } else {
      setError(res.error || "Registration failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative bg-background overflow-hidden">
      {/* Premium Ambient Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-900/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[40%] h-[40%] bg-slate-900/30 rounded-full blur-[120px]" />
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="max-w-md w-full z-10 py-12"
      >
        <div className="text-center mb-10">
          <h1 className="font-headline-lg text-4xl text-white font-black tracking-tight mb-3">
            EUROGRANT <span className="text-secondary italic font-light">AI</span>
          </h1>
          <p className="font-label-sm text-[10px] text-secondary tracking-[0.3em] uppercase opacity-70">
            Elite Intelligence Enrollment
          </p>
        </div>

        <motion.div 
          whileHover={{ 
            rotateX: 1, 
            rotateY: -1,
            transition: { duration: 0.4 }
          }}
          style={{ perspective: 1000 }}
          className="glass-card rounded-2xl p-10 border border-glass-border relative overflow-hidden"
        >
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent" />
          
          <div className="flex items-center gap-4 mb-10">
            <h2 className="font-headline-md text-2xl text-white">Create Account</h2>
            <div className="h-[1px] flex-1 bg-gradient-to-r from-white/10 to-transparent" />
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-error-container/20 border border-error/20 text-error text-[10px] font-black uppercase tracking-widest p-4 rounded-xl text-center"
              >
                {error}
              </motion.div>
            )}
            
            <div className="space-y-4">
              <div className="group relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors">
                  <User size={18} />
                </div>
                <input
                  type="text"
                  required
                  className="w-full bg-surface-container-low/40 border border-glass-border rounded-xl py-3.5 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/30 transition-all font-body-md text-sm"
                  placeholder="Full Name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>

              <div className="group relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors">
                  <Building size={18} />
                </div>
                <input
                  type="text"
                  required
                  className="w-full bg-surface-container-low/40 border border-glass-border rounded-xl py-3.5 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/30 transition-all font-body-md text-sm"
                  placeholder="Organization Name"
                  value={organizationName}
                  onChange={(e) => setOrganizationName(e.target.value)}
                />
              </div>

              <div className="group relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors">
                  <Mail size={18} />
                </div>
                <input
                  type="email"
                  required
                  className="w-full bg-surface-container-low/40 border border-glass-border rounded-xl py-3.5 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/30 transition-all font-body-md text-sm"
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
                  className="w-full bg-surface-container-low/40 border border-glass-border rounded-xl py-3.5 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/30 transition-all font-body-md text-sm"
                  placeholder="Security Key (Password)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <div className="group relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-primary transition-colors">
                  <KeyRound size={18} />
                </div>
                <input
                  type="text"
                  required
                  className="w-full bg-surface-container-low/40 border border-glass-border rounded-xl py-3.5 pl-12 pr-4 text-white placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-primary/30 focus:border-primary/30 transition-all font-body-md text-sm"
                  placeholder="Master Invite Code"
                  value={inviteCode}
                  onChange={(e) => setInviteCode(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              className="group relative w-full py-4.5 bg-white text-background font-black uppercase tracking-[0.2em] text-[10px] rounded-xl overflow-hidden transition-all hover:scale-[1.02] active:scale-[0.98] shadow-luxury mt-4"
            >
              <span className="relative z-10 flex items-center justify-center gap-2">
                Enroll Agent <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-slate-200 to-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          </form>

          <div className="mt-10 text-center">
            <Link href="/login" className="group inline-flex items-center gap-2 font-label-sm text-[9px] text-slate-500 hover:text-white uppercase tracking-[0.2em] transition-all">
              <span>Secure Sign In</span>
              <div className="w-4 h-[1px] bg-slate-700 group-hover:bg-white group-hover:w-8 transition-all" />
            </Link>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
