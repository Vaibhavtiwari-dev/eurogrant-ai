"use strict";

import { z } from "zod";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");

export function apiUrl(endpoint: string): string {
  return `${API_BASE_URL}/api/v1${endpoint}`;
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit,
  schema: z.ZodSchema<T>
): Promise<T>;

export async function apiFetch(
  endpoint: string,
  options?: RequestInit
): Promise<Response>;

export async function apiFetch<T>(
  endpoint: string, 
  options: RequestInit & { _retry?: boolean } = {}, 
  schema?: z.ZodSchema<T>
): Promise<T | Response> {
  const isBrowser = typeof window !== "undefined";
  
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  // Only set default content-type if not already set and not FormData
  if (!headers["Content-Type"] && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(apiUrl(endpoint), {
    ...options,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && isBrowser) {
    const path = window.location.pathname;
    const isPublicPage = path.includes("/login") || path.includes("/register");
    if (!isPublicPage) {
      if (!options._retry) {
        options._retry = true;
        try {
          // Attempt to refresh the token
          const refreshRes = await fetch(apiUrl("/auth/refresh"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
          });
          
          if (refreshRes.ok) {
            // Retry original request
            return await apiFetch(endpoint, options, schema as z.ZodSchema<T>);
          }
        } catch {
          // Fall through to redirect
        }
        
        // Refresh failed, redirect to login
        localStorage.removeItem("token");
        window.location.href = "/login";
      } else {
        localStorage.removeItem("token");
        window.location.href = "/login";
      }
    }
    return response as unknown as T;
  }

  if (response.ok && schema) {
    const data = await response.json();
    return schema.parse(data);
  }

  return response;
}
