"use client";

import React, { useState, useEffect } from "react";
import { CreditCard, Loader2, Settings, TrendingUp, Building2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import { z } from "zod";
import { logger } from "@/utils/logger";

const BillingStatusSchema = z.object({
  tier: z.string(),
  status: z.string(),
  current_period_end: z.string().nullable().optional(),
  has_customer: z.boolean(),
});

type BillingStatus = z.infer<typeof BillingStatusSchema>;

export default function BillingSettings() {
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState<string | null>(null);

  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const res = await apiFetch("/billing/status");
      if (!res.ok) throw new Error("Failed to fetch billing status");
      const data = await res.json();
      const parsed = BillingStatusSchema.parse(data);
      setStatus(parsed);
    } catch (err) {
      logger.error("Billing fetch error:", err);
      toast.error("Could not load billing information");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchStatus();
  }, []);



  const handleCheckout = async (tier: string) => {
    setIsProcessing(tier);
    try {
      const res = await apiFetch("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ tier }),
      });
      if (!res.ok) throw new Error("Checkout session creation failed");
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      logger.error("Checkout error:", err);
      toast.error("Failed to start checkout process");
    } finally {
      setIsProcessing(null);
    }
  };

  const handlePortal = async () => {
    setIsProcessing("portal");
    try {
      const res = await apiFetch("/billing/portal", { method: "POST" });
      if (!res.ok) throw new Error("Portal session creation failed");
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      logger.error("Portal error:", err);
      toast.error("Failed to open customer portal");
    } finally {
      setIsProcessing(null);
    }
  };

  if (isLoading) {
    return (
      <div className="premium-card p-10 bg-surface/50 border border-white/5 rounded-2xl flex items-center justify-center min-h-[300px]">
        <Loader2 className="w-8 h-8 text-emerald-light animate-spin" />
      </div>
    );
  }

  const isSubscribed = status?.status === "active" && status?.tier !== "free";

  return (
    <div className="premium-card p-10 bg-surface/50 border border-white/5 rounded-2xl space-y-8 shadow-xl relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald/5 rounded-full blur-3xl pointer-events-none" />

      <div className="flex items-center gap-3 pb-6 border-b border-white/5 relative z-10">
        <CreditCard size={20} className="text-emerald-light" />
        <div>
          <h2 className="text-lg font-bold text-on-surface">Subscription & Billing</h2>
          <p className="text-xs text-on-surface-variant">Manage your current plan, billing history, and payment methods.</p>
        </div>
      </div>

      <div className="relative z-10 space-y-8">
        {/* Current Status Banner */}
        <div className="flex items-center justify-between p-6 rounded-xl bg-background/40 border border-white/5">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/80 mb-1">Current Plan</p>
            <div className="flex items-center gap-3">
              <h3 className="text-2xl font-black text-white capitalize">{status?.tier || "Free"} Tier</h3>
              {isSubscribed && (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald/10 text-emerald-light border border-emerald/20">
                  Active
                </span>
              )}
            </div>
            {isSubscribed && status?.current_period_end && (
              <p className="text-xs text-on-surface-variant mt-2">
                Renews on {new Date(status.current_period_end).toLocaleDateString()}
              </p>
            )}
          </div>

          {isSubscribed && (
            <button
              onClick={handlePortal}
              disabled={isProcessing === "portal"}
              className="py-2.5 px-5 rounded-lg bg-emerald/10 border border-emerald/30 text-emerald-light text-xs font-bold uppercase tracking-wider hover:bg-emerald/20 transition-all flex items-center gap-2"
            >
              {isProcessing === "portal" ? <Loader2 size={14} className="animate-spin" /> : <Settings size={14} />}
              Manage Subscription
            </button>
          )}
        </div>

        {/* Pricing Tiers (Show only if not subscribed or if we want to allow upgrade) */}
        {!isSubscribed && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
            {/* Free */}
            <div className="p-6 rounded-xl border border-white/5 bg-background/20 opacity-70 grayscale">
              <h4 className="text-lg font-bold text-white mb-2">Free</h4>
              <p className="text-xs text-on-surface-variant mb-6 min-h-[40px]">Basic exploration of the grant matrix.</p>
              <button disabled className="w-full py-2.5 rounded-lg bg-white/5 text-white/50 text-xs font-bold uppercase cursor-not-allowed">
                Current Plan
              </button>
            </div>

            {/* Growth */}
            <div className="p-6 rounded-xl border border-copper/30 bg-copper/5 relative shadow-[0_0_20px_rgba(180,83,9,0.05)]">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-copper text-white text-[10px] font-black uppercase tracking-widest shadow-md">
                Recommended
              </div>
              <TrendingUp className="text-copper mb-4" size={24} />
              <h4 className="text-lg font-bold text-white mb-2">Growth</h4>
              <p className="text-xs text-on-surface-variant mb-6 min-h-[40px]">Unlock AI-powered semantic matching and basic RAG generation.</p>
              <button 
                onClick={() => handleCheckout("growth")}
                disabled={isProcessing !== null}
                className="w-full py-2.5 rounded-lg bg-copper hover:brightness-110 text-white text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-md shadow-copper/20 disabled:opacity-50"
              >
                {isProcessing === "growth" ? <Loader2 size={14} className="animate-spin" /> : "Upgrade to Growth"}
              </button>
            </div>

            {/* Scale */}
            <div className="p-6 rounded-xl border border-emerald/20 bg-emerald/5 hover:border-emerald/40 transition-colors">
              <Building2 className="text-emerald-light mb-4" size={24} />
              <h4 className="text-lg font-bold text-white mb-2">Scale</h4>
              <p className="text-xs text-on-surface-variant mb-6 min-h-[40px]">Unlimited RAG pipelines, custom schemas, and VIP support.</p>
              <button 
                onClick={() => handleCheckout("scale")}
                disabled={isProcessing !== null}
                className="w-full py-2.5 rounded-lg bg-emerald hover:bg-emerald-light text-surface text-xs font-bold uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-md shadow-emerald/10 disabled:opacity-50"
              >
                {isProcessing === "scale" ? <Loader2 size={14} className="animate-spin" /> : "Upgrade to Scale"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
