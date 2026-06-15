"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { containerVariants, itemVariants } from "@/lib/animations";
import Sidebar from "@/components/dashboard/Sidebar";
import Header from "@/components/dashboard/Header";
import { useAuth } from "@/context/AuthContext";
import { Settings, User, Shield, AlertTriangle, Loader2, Save, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";
import BillingSettings from "@/components/dashboard/BillingSettings";

export default function SettingsPage() {
  const { user, loading, logout } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  const [profile, setProfile] = useState({ full_name: "", email: "" });
  const [passwordData, setPasswordData] = useState({ current: "", next: "", confirm: "" });
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [profileSaveSuccess, setProfileSaveSuccess] = useState(false);
  const [passwordSaveSuccess, setPasswordSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState("");

  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const hasInitialLoad = useRef(false);
  useEffect(() => {
    if (user && !hasInitialLoad.current) {
      hasInitialLoad.current = true;
      setProfile({
        full_name: user.full_name || "",
        email: user.email,
      });
    }
  }, [user]);

  const handleProfileSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    setSaveError("");
    setProfileSaveSuccess(false);
    try {
      const response = await apiFetch("/users/me", {
        method: "PUT",
        body: JSON.stringify({ full_name: profile.full_name }),
      });
      if (!response.ok) {
        throw new Error("Profile update failed");
      }
      setProfileSaveSuccess(true);
      setTimeout(() => setProfileSaveSuccess(false), 3000);
    } catch {
      setSaveError("Failed to update profile. Please try again.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handlePasswordSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaveError("");
    if (passwordData.next !== passwordData.confirm) {
      setSaveError("New passwords do not match.");
      return;
    }
    if (passwordData.next.length < 8) {
      setSaveError("Password must be at least 8 characters.");
      return;
    }
    setIsSavingPassword(true);
    try {
      const response = await apiFetch("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: passwordData.current,
          new_password: passwordData.next,
        }),
      });
      if (!response.ok) {
        throw new Error("Password update failed");
      }
      setPasswordData({ current: "", next: "", confirm: "" });
      setPasswordSaveSuccess(true);
      setTimeout(() => setPasswordSaveSuccess(false), 3000);
    } catch {
      setSaveError("Failed to change password. Check your current password.");
    } finally {
      setIsSavingPassword(false);
    }
  };

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-6">
          <Loader2 className="w-16 h-16 border-4 border-emerald/10 border-t-emerald-light rounded-full animate-spin" />
          <p className="text-emerald-light/60 font-bold uppercase tracking-[0.2em] text-xs animate-pulse">Loading Settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background text-on-background selection:bg-emerald/10">
      <Sidebar
        isMobile={isMobile}
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        setIsUploadModalOpen={() => {}}
        logout={logout}
      />

      <Header user={user} setIsSidebarOpen={setIsSidebarOpen} />

      <motion.main
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="relative z-10 md:ml-64 pt-12 px-12 pb-32 min-h-screen hero-gradient"
      >
        <div className="max-w-3xl mx-auto space-y-10">
          {/* Page Header */}
          <motion.div variants={itemVariants}>
            <h1 className="text-4xl font-bold text-on-surface mb-3 flex items-center gap-4">
              <Settings className="text-emerald-light" size={32} />
              Account Settings
            </h1>
            <p className="text-on-surface-variant max-w-xl text-sm leading-relaxed">
              Manage your profile, notification preferences, and security settings.
            </p>
          </motion.div>

          {/* Profile Section */}
          <motion.div variants={itemVariants}>
            <form onSubmit={handleProfileSave} className="premium-card p-10 bg-surface/50 border border-white/5 rounded-2xl space-y-8 shadow-xl">
              <div className="flex items-center gap-3 pb-6 border-b border-white/5">
                <User size={20} className="text-emerald-light" />
                <div>
                  <h2 className="text-lg font-bold text-on-surface">Profile Information</h2>
                  <p className="text-xs text-on-surface-variant">Update your display name and view your account details.</p>
                </div>
              </div>

              <div className="space-y-5">
                <div>
                  <label htmlFor="profile-full-name" className="block text-xs font-bold uppercase tracking-widest text-on-surface-variant/80 mb-2">Full Name</label>
                  <input
                    id="profile-full-name"
                    type="text"
                    value={profile.full_name}
                    onChange={(e) => setProfile(p => ({ ...p, full_name: e.target.value }))}
                    className="w-full px-5 py-3 rounded-xl bg-background/60 border border-white/10 text-on-surface text-sm placeholder:text-on-surface-variant/30 focus:border-emerald-light/40 focus:ring-1 focus:ring-emerald-light/10 outline-none transition-all"
                    placeholder="Your full name"
                  />
                </div>
                <div>
                  <label htmlFor="profile-email" className="block text-xs font-bold uppercase tracking-widest text-on-surface-variant/80 mb-2">Email Address</label>
                  <input
                    id="profile-email"
                    type="email"
                    value={profile.email}
                    readOnly
                    className="w-full px-5 py-3 rounded-xl bg-white/[0.02] border border-white/5 text-on-surface-variant text-sm cursor-not-allowed"
                  />
                  <p className="text-[10px] text-on-surface-variant/50 mt-1.5">Email cannot be changed — contact support for org transfers.</p>
                </div>
              </div>

              {profileSaveSuccess && (
                <div className="flex items-center gap-2 text-emerald-light text-xs font-bold">
                  <CheckCircle2 size={14} />
                  <span>Profile updated successfully.</span>
                </div>
              )}

              <div className="pt-4 border-t border-white/5 flex justify-end">
                <button
                  type="submit"
                  disabled={isSavingProfile}
                  className="py-3 px-8 rounded-lg bg-emerald hover:bg-emerald-light text-surface text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-md shadow-emerald/10 disabled:opacity-50 transition-all"
                >
                  {isSavingProfile ? <><Loader2 size={14} className="animate-spin" /> Saving...</> : <><Save size={14} /> Save Profile</>}
                </button>
              </div>
            </form>
          </motion.div>

          {/* Security / Password Section */}
          <motion.div variants={itemVariants}>
            <form onSubmit={handlePasswordSave} className="premium-card p-10 bg-surface/50 border border-white/5 rounded-2xl space-y-8 shadow-xl">
              <div className="flex items-center gap-3 pb-6 border-b border-white/5">
                <Shield size={20} className="text-emerald-light" />
                <div>
                  <h2 className="text-lg font-bold text-on-surface">Change Password</h2>
                  <p className="text-xs text-on-surface-variant">Update your account password. Minimum 8 characters.</p>
                </div>
              </div>

              <div className="space-y-5">
                {[
                  { key: "current", label: "Current Password", type: "password" },
                  { key: "next", label: "New Password", type: "password" },
                  { key: "confirm", label: "Confirm New Password", type: "password" },
                ].map(({ key, label, type }) => (
                  <div key={key}>
                    <label htmlFor={`password-${key}`} className="block text-xs font-bold uppercase tracking-widest text-on-surface-variant/80 mb-2">{label}</label>
                    <input
                      id={`password-${key}`}
                      type={type}
                      value={passwordData[key as keyof typeof passwordData]}
                      onChange={(e) => setPasswordData(d => ({ ...d, [key]: e.target.value }))}
                      className="w-full px-5 py-3 rounded-xl bg-background/60 border border-white/10 text-on-surface text-sm placeholder:text-on-surface-variant/30 focus:border-emerald-light/40 focus:ring-1 focus:ring-emerald-light/10 outline-none transition-all"
                      placeholder={"•".repeat(8)}
                    />
                  </div>
                ))}
              </div>

              {passwordSaveSuccess && (
                <div className="flex items-center gap-2 text-emerald-light text-xs font-bold">
                  <CheckCircle2 size={14} />
                  <span>Password updated successfully.</span>
                </div>
              )}
              {saveError && (
                <p className="text-red-400 text-xs font-bold">{saveError}</p>
              )}

              <div className="pt-4 border-t border-white/5 flex justify-end">
                <button
                  type="submit"
                  disabled={isSavingPassword}
                  className="py-3 px-8 rounded-lg bg-copper hover:brightness-110 text-white text-xs font-bold uppercase tracking-wider flex items-center gap-2 shadow-md shadow-copper/10 disabled:opacity-50 transition-all"
                >
                  {isSavingPassword ? <><Loader2 size={14} className="animate-spin" /> Updating...</> : <><Save size={14} /> Update Password</>}
                </button>
              </div>
            </form>
          </motion.div>

          {/* Billing / Subscription Section */}
          <motion.div variants={itemVariants}>
            <BillingSettings />
          </motion.div>

          {/* Danger Zone */}
          <motion.div variants={itemVariants} className="premium-card p-10 bg-red-500/[0.03] border border-red-500/10 rounded-2xl space-y-6">
            <div className="flex items-center gap-3">
              <AlertTriangle size={20} className="text-red-400" />
              <div>
                <h2 className="text-lg font-bold text-white">Danger Zone</h2>
                <p className="text-xs text-on-surface-variant">Irreversible actions — proceed with caution.</p>
              </div>
            </div>

            <div className="flex items-center justify-between p-5 rounded-xl bg-white/[0.02] border border-white/5">
              <div>
                <p className="text-sm font-bold text-on-surface">Delete Account</p>
                <p className="text-xs text-on-surface-variant mt-0.5">Permanently removes your account and all associated data. This cannot be undone.</p>
              </div>
              <button
                onClick={() => toast.error("Account deletion is not yet implemented. Contact support@eurogrant.ai to delete your account.")}
                className="py-2.5 px-5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-bold uppercase tracking-wider hover:bg-red-500/20 transition-all"
              >
                Delete Account
              </button>
            </div>
          </motion.div>
        </div>
      </motion.main>
    </div>
  );
}
