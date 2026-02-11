"use client";

import Link from "next/link";
import { Key, Calendar } from "lucide-react";
import type { AppListItem } from "@/types/app";

interface AppCardProps {
  app: AppListItem;
}

export default function AppCard({ app }: AppCardProps) {
  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });

  return (
    <Link href={`/apps/${app.slug}`} className="app-card">
      <div className="app-card-header">
        <h3 className="app-card-name">{app.name}</h3>
      </div>
      {app.description && (
        <p className="app-card-description">{app.description}</p>
      )}
      <div className="app-card-footer">
        <span className="app-card-meta">
          <Key size={12} />
          {app.api_key_count} {app.api_key_count === 1 ? "key" : "keys"}
        </span>
        <span className="app-card-meta">
          <Calendar size={12} />
          {formatDate(app.created_at)}
        </span>
      </div>
    </Link>
  );
}
