"use client";

import { useApp } from "@/components/providers/AppProvider";

interface PageHeaderProps {
  title: string;
  description?: string;
}

export default function PageHeader({ title, description }: PageHeaderProps) {
  const { app } = useApp();

  return (
    <div className="page-header">
      {app && <span className="page-header-app">{app.name}</span>}
      <h1 className="page-header-title">{title}</h1>
      {description && <p className="page-header-desc">{description}</p>}
    </div>
  );
}
