"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useApp } from "@/components/providers/AppProvider";

interface BreadcrumbsProps {
  appSlug: string;
}

const sectionMap: Record<string, string> = {
  endpoints: "Endpoints",
  logs: "Logs",
  analytics: "Analytics",
  monitors: "Monitors",
  settings: "Settings",
};

export default function Breadcrumbs({ appSlug }: BreadcrumbsProps) {
  const pathname = usePathname();
  const { app } = useApp();

  const parts = pathname.split("/").filter(Boolean);
  const section = parts[2];
  const sectionName = section ? (sectionMap[section] || section.charAt(0).toUpperCase() + section.slice(1)) : null;
  const displayName = app?.name || appSlug;

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol className="breadcrumbs-list">
        <li className="breadcrumbs-item">
          <Link href="/apps" className="breadcrumbs-link">Apps</Link>
        </li>
        <ChevronRight size={14} className="breadcrumbs-separator" />
        <li className="breadcrumbs-item">
          <Link href={`/apps/${appSlug}`} className="breadcrumbs-link breadcrumbs-app">
            {displayName}
          </Link>
        </li>
        {sectionName && (
          <>
            <ChevronRight size={14} className="breadcrumbs-separator" />
            <li className="breadcrumbs-item">
              <span className="breadcrumbs-current">{sectionName}</span>
            </li>
          </>
        )}
      </ol>
    </nav>
  );
}
