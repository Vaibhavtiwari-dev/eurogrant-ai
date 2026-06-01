"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Link } from "@/i18n/routing";
import { motion } from "framer-motion";
import { Mail, Lock, ShieldCheck, ArrowRight } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const res = await login(email, password);
    if (!res.success) {
      setError(res.error || "Intelligence access denied");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative bg-background overflow-hidden font-inter">
      {/* Premium Ambient Background */}
      <div className="absolute inset-0 z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-emerald/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-copper/5 rounded-full blur-[120px]" />
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
            className="inline-block mb-6"
          >
            <div className="p-4 rounded-lg bg-emerald/10 border border-emerald/20 shadow-emerald">
              <ShieldCheck className="text-emerald-light w-10 h-10" />
            </div>
          </motion.div>
          <h1 className="text-4xl font-bold text-on-surface tracking-tight mb-3">
            EuroGrant <span className="text-emerald-light">AI</span>
          </h1>
          <p className="text-xs font-bold text-on-surface-variant uppercase tracking-widest opacity-60">
            Secure Intelligence Access
          </p>
        </div>

        <div className="tonal-surface rounded-lg p-10 relative overflow-hidden backdrop-blur-xl border border-outline shadow-2xl">
          <div className="flex items-center gap-4 mb-10">
            <h2 className="text-2xl font-bold text-on-surface">Sign In</h2>
            <div className="h-[1px] flex-1 bg-outline opacity-40" />
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="bg-error-container/20 border border-error/20 text-error text-xs font-bold uppercase tracking-widest p-4 rounded-lg text-center"
              >
                {error}
              </motion.div>
            )}
            
            <div className="space-y-4">
              <div className="group relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant opacity-40 group-focus-within:text-emerald-light group-focus-within:opacity-100 transition-all">
                  <Mail size={18} />
                </div>
                <input
                  type="email"
                  required
                  aria-label="Email"
                  className="w-full bg-background border border-outline rounded-lg py-4 pl-12 pr-4 text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-4 focus:ring-emerald/5 focus:border-emerald-light/50 focus-visible:outline-2 focus-visible:outline-emerald-light transition-all text-sm font-medium"
                  placeholder="Intelligence ID (Email)"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="group relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant opacity-40 group-focus-within:text-emerald-light group-focus-within:opacity-100 transition-all">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  required
                  aria-label="Password"
                  className="w-full bg-background border border-outline rounded-lg py-4 pl-12 pr-4 text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-4 focus:ring-emerald/5 focus:border-emerald-light/50 focus-visible:outline-2 focus-visible:outline-emerald-light transition-all text-sm font-medium"
                  placeholder="Security Key (Password)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-4 pt-4">
              <button
                type="submit"
                aria-label="Sign In"
                className="group relative w-full py-4 bg-copper text-white font-bold uppercase tracking-widest text-xs rounded-lg overflow-hidden transition-all hover:scale-[1.01] active:scale-[0.99] flex items-center justify-center gap-2 hover:brightness-110 shadow-lg shadow-copper/10 focus-visible:outline-2 focus-visible:outline-copper focus-visible:outline-offset-2"
              >
                <span>Authorize Access</span>
                <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </form>

          <div className="mt-10 text-center border-t border-outline pt-8">
            <Link href="/register" className="group inline-flex items-center gap-2 text-[10px] font-bold text-on-surface-variant hover:text-emerald-light uppercase tracking-widest transition-all focus-visible:outline-2 focus-visible:outline-emerald-light rounded">
              <span>Request Intelligence Access</span>
              <div className="w-4 h-[1px] bg-outline opacity-40 group-hover:bg-emerald-light group-hover:w-8 group-hover:opacity-100 transition-all" />
            </Link>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
