"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import {
  Layers,
  ScrollText,
  TrendingUp,
  Radio,
  Settings,
  Bell,
  CircleHelpIcon,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { useSidebar } from "@/components/providers/SidebarProvider";

interface SidebarProps {
  appSlug: string;
}

export default function Sidebar({ appSlug }: SidebarProps) {
  const pathname = usePathname();
  const { collapsed, toggleSidebar } = useSidebar();

  const basePath = `/apps/${appSlug}`;

  const navigation = [
    { name: "Endpoints", href: `${basePath}/endpoints`, icon: Layers },
    { name: "Logs", href: `${basePath}/logs`, icon: ScrollText },
    { name: "Analytics", href: `${basePath}/analytics`, icon: TrendingUp },
    { name: "Monitors", href: `${basePath}/monitors`, icon: Radio },
    { name: "Settings", href: `${basePath}/settings/general`, icon: Settings },
  ];

  const secondaryNavigation = [
    { name: "Notifications", href: "/notifications", icon: Bell },
    { name: "Help & Support", href: "/help", icon: CircleHelpIcon },
  ];

  return (
    <aside className={`sidebar ${collapsed ? "sidebar-collapsed" : ""}`}>
      <div className="sidebar-header">
        <Link href="/apps" className="logo" title="Back to Apps">
          {collapsed ? (
            <Image
              src="/logo.svg"
              alt="ApiLens"
              width={28}
              height={28}
              className="logo-icon-collapsed"
            />
          ) : (
            <span className="logo-text">API Lens</span>
          )}
        </Link>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          {!collapsed && <span className="nav-section-title">Main</span>}
          <ul className="nav-list">
            {navigation.map((item) => {
              const isActive =
                item.name === "Settings"
                  ? pathname.startsWith(`${basePath}/settings`)
                  : pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className={`nav-item ${isActive ? "nav-item-active" : ""}`}
                    title={collapsed ? item.name : undefined}
                  >
                    <item.icon size={16} className="nav-icon" />
                    {!collapsed && <span>{item.name}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>

        <div className="nav-section">
          {!collapsed && <span className="nav-section-title">Support</span>}
          <ul className="nav-list">
            {secondaryNavigation.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <li key={item.name}>
                  <Link
                    href={item.href}
                    className={`nav-item ${isActive ? "nav-item-active" : ""}`}
                    title={collapsed ? item.name : undefined}
                  >
                    <item.icon size={16} className="nav-icon" />
                    {!collapsed && <span>{item.name}</span>}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-actions">
          <button
            className="sidebar-action-btn"
            onClick={toggleSidebar}
            title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
          >
            {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </div>
    </aside>
  );
}

