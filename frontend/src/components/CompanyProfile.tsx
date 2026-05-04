"use client";

import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Building2, Users, Banknote, Shield, Globe, Cpu, Loader2, Sparkles } from "lucide-react";

interface Organization {
  name: string;
  subscription_tier: string;
  sector?: string;
  headcount_range?: string;
  revenue_tier?: string;
  legal_entity_type?: string;
  countries_of_operation?: string;
  core_technologies?: string;
}

interface CompanyProfileProps {
  refreshKey: number;
}

export default function CompanyProfile({ refreshKey }: CompanyProfileProps) {
  const [org, setOrg] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchOrg = async () => {
    try {
      const response = await apiFetch("/organizations/me");
      if (response.ok) {
        const data = await response.json();
        setOrg(data);
      }
    } catch (error) {
      console.error("Failed to fetch organization:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOrg();
  }, [refreshKey]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-12">
        <Loader2 className="h-8 w-8 text-blue-500 animate-spin mb-4" />
        <p className="text-gray-500 font-bold">Loading profile...</p>
      </div>
    );
  }

  if (!org || !org.sector) {
    return (
      <div className="p-12 text-center bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200">
        <div className="bg-white p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4 shadow-sm">
          <Sparkles className="h-8 w-8 text-blue-500" />
        </div>
        <h3 className="text-xl font-black text-gray-900 mb-2">No AI Profile Found</h3>
        <p className="text-gray-500 font-medium max-w-sm mx-auto">
          Upload your business plan or company documents to let EuroGrant AI automatically profile your business.
        </p>
      </div>
    );
  }

  const countries = org.countries_of_operation ? JSON.parse(org.countries_of_operation) : [];
  const technologies = org.core_technologies ? JSON.parse(org.core_technologies) : [];

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ProfileItem
          icon={<Building2 className="h-5 w-5 text-blue-600" />}
          label="Sector"
          value={org.sector}
        />
        <ProfileItem
          icon={<Users className="h-5 w-5 text-blue-600" />}
          label="Headcount"
          value={org.headcount_range}
        />
        <ProfileItem
          icon={<Banknote className="h-5 w-5 text-blue-600" />}
          label="Revenue Tier"
          value={org.revenue_tier}
        />
        <ProfileItem
          icon={<Shield className="h-5 w-5 text-blue-600" />}
          label="Legal Entity"
          value={org.legal_entity_type}
        />
      </div>

      <div className="space-y-6">
        <div>
          <h4 className="flex items-center gap-2 text-sm font-black text-gray-400 uppercase tracking-widest mb-4">
            <Globe className="h-4 w-4" />
            Market Reach
          </h4>
          <div className="flex flex-wrap gap-2">
            {countries.map((country: string) => (
              <span key={country} className="bg-blue-50 text-blue-700 px-3 py-1 rounded-lg font-black text-xs border border-blue-100 uppercase">
                {country}
              </span>
            ))}
          </div>
        </div>

        <div>
          <h4 className="flex items-center gap-2 text-sm font-black text-gray-400 uppercase tracking-widest mb-4">
            <Cpu className="h-4 w-4" />
            Core Technologies
          </h4>
          <div className="flex flex-wrap gap-2">
            {technologies.map((tech: string) => (
              <span key={tech} className="bg-gray-100 text-gray-700 px-3 py-1 rounded-lg font-black text-xs border border-gray-200 uppercase">
                {tech}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ProfileItem({ icon, label, value }: { icon: React.ReactNode; label: string; value?: string }) {
  return (
    <div className="flex items-start gap-4 p-4 bg-gray-50 rounded-xl border border-gray-100">
      <div className="bg-white p-2.5 rounded-lg shadow-sm border border-gray-100">
        {icon}
      </div>
      <div>
        <p className="text-xs font-black text-gray-400 uppercase tracking-wider mb-1">{label}</p>
        <p className="text-lg font-black text-gray-900 tracking-tight">{value || "Not specified"}</p>
      </div>
    </div>
  );
}
