"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

interface BreadcrumbsProps {
    appSlug: string;
}

export default function Breadcrumbs({ appSlug }: BreadcrumbsProps) {
    const pathname = usePathname();
    const [appName, setAppName] = useState<string | null>(null);

    useEffect(() => {
        async function fetchAppName() {
            try {
                const res = await fetch(`/api/apps/${appSlug}`);
                if (res.ok) {
                    const data = await res.json();
                    setAppName(data.name);
                }
            } catch {
                // Ignore errors, just show slug as fallback
            }
        }
        fetchAppName();
    }, [appSlug]);

    // Derive current section from pathname
    const getSectionName = () => {
        const parts = pathname.split("/").filter(Boolean);
        // /apps/{slug}/settings/general -> ["apps", slug, "settings", "general"]
        // /apps/{slug}/endpoints -> ["apps", slug, "endpoints"]
        const sectionIndex = 2; // After "apps" and slug
        const section = parts[sectionIndex];

        if (!section) return null;

        // Capitalize first letter
        const sectionMap: Record<string, string> = {
            endpoints: "Endpoints",
            logs: "Logs",
            analytics: "Analytics",
            monitors: "Monitors",
            settings: "Settings",
        };

        return sectionMap[section] || section.charAt(0).toUpperCase() + section.slice(1);
    };

    const sectionName = getSectionName();
    const displayName = appName || appSlug;

    return (
        <nav className="breadcrumbs" aria-label="Breadcrumb">
            <ol className="breadcrumbs-list">
                <li className="breadcrumbs-item">
                    <Link href="/apps" className="breadcrumbs-link">
                        Apps
                    </Link>
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
