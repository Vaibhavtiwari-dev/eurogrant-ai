"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Link from "next/link";
import { LogIn, Mail, Lock } from "lucide-react";

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
    <div className="min-h-screen flex items-center justify-center text-on-surface px-4 relative">
      <div className="max-w-md w-full z-10">
        <div className="text-center mb-10">
          <h1 className="font-headline-lg text-headline-lg text-white font-black tracking-tight mb-2">EuroGrant AI</h1>
          <p className="font-label-sm text-label-sm text-secondary tracking-widest uppercase">Elite Intelligence Portal</p>
        </div>

        <div className="glass-card rounded-xl p-8 shadow-2xl border-l-4 border-secondary/30">
          <div className="flex items-center gap-3 mb-8">
            <div className="bg-secondary/10 p-2 rounded-lg text-secondary">
              <LogIn size={20} />
            </div>
            <h2 className="font-headline-md text-headline-md text-white">Sign In</h2>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-error/10 border border-error/20 text-error text-xs font-black uppercase tracking-widest p-4 rounded-lg text-center animate-pulse">
                {error}
              </div>
            )}
            
            <div className="space-y-4">
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant opacity-40" size={18} />
                <input
                  type="email"
                  required
                  className="w-full bg-surface-container/50 border border-white/10 rounded-lg py-3 pl-12 pr-4 text-white placeholder-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-secondary/50 focus:border-secondary/50 transition-all font-body-md"
                  placeholder="Intelligence ID (Email)"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-on-surface-variant opacity-40" size={18} />
                <input
                  type="password"
                  required
                  className="w-full bg-surface-container/50 border border-white/10 rounded-lg py-3 pl-12 pr-4 text-white placeholder-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-secondary/50 focus:border-secondary/50 transition-all font-body-md"
                  placeholder="Security Key (Password)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-4 bg-secondary text-on-secondary-fixed font-black uppercase tracking-widest text-[11px] rounded-xl hover:bg-white hover:text-black transition-all shadow-[0_0_20px_rgba(123,208,255,0.2)] hover:shadow-[0_0_30px_rgba(123,208,255,0.4)]"
            >
              Authorize Access
            </button>
          </form>

          <div className="mt-8 text-center">
            <Link href="/register" className="font-label-sm text-[11px] text-on-surface-variant hover:text-secondary uppercase tracking-widest transition-colors">
              Request Intelligence Access (Register)
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
