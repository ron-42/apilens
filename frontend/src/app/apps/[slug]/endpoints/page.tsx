"use client";

import { Layers } from "lucide-react";
import PageHeader from "@/components/dashboard/PageHeader";

export default function EndpointsPage() {
  return (
    <div className="placeholder-page">
      <PageHeader title="Endpoints" description="Endpoint monitoring and management will appear here." />
      <div className="placeholder-icon">
        <Layers size={32} />
      </div>
    </div>
  );
}
