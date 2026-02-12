"use client";

import { TrendingUp } from "lucide-react";
import PageHeader from "@/components/dashboard/PageHeader";

export default function AnalyticsPage() {
  return (
    <div className="placeholder-page">
      <PageHeader title="Analytics" description="API usage analytics and insights will appear here." />
      <div className="placeholder-icon">
        <TrendingUp size={32} />
      </div>
    </div>
  );
}
