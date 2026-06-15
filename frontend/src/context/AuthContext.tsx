"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, apiUrl } from "@/lib/api";
import { logger } from "@/utils/logger";

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  organization_id: number;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (email: string, password: string, fullName: string, organizationName: string, inviteCode: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const checkUser = async () => {
      try {
        const res = await apiFetch("/users/me");
        if (res && res.ok) {
          const userData = await res.json();
          setUser(userData);
        }
      } catch (error) {
        logger.error("Auth check failed", error);
      }
      setLoading(false);
    };
    checkUser();
  }, []);

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const getCookie = (name: string) => {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop()?.split(";").shift();
      return "";
    };
    const csrfToken = getCookie("csrf_token") || "";

    try {
      const res = await fetch(apiUrl("/auth/login"), {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRF-Token": csrfToken,
        },
        body: formData.toString(),
        credentials: "include",
      });

      if (res.ok) {
        const userRes = await apiFetch("/users/me");
        if (userRes && userRes.ok) {
          const userData = await userRes.json();
          setUser(userData);
        }
        router.push("/dashboard");
        return { success: true };
      } else {
        const error = await res.json();
        return { success: false, error: error.detail };
      }
    } catch {
      return { success: false, error: "Network error" };
    }
  };

  const register = async (email: string, password: string, fullName: string, organizationName: string, inviteCode: string) => {
    try {
      const res = await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({ 
          email, 
          password, 
          full_name: fullName, 
          organization_name: organizationName,
          invite_code: inviteCode
        }),
      });

      if (res && res.ok) {
        return { success: true };
      } else if (res) {
        const error = await res.json();
        return { success: false, error: error.detail };
      }
      return { success: false, error: "Unknown error" };
    } catch {
      return { success: false, error: "Network error" };
    }
  };

  const logout = async () => {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch {
      // Best-effort — continue with client-side cleanup regardless
    }
    // Clear any legacy localStorage tokens for migration safety
    localStorage.removeItem("token");
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
