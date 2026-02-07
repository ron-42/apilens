"use client";

import Link from "next/link";
import { Settings, User } from "lucide-react";

export type SettingsTab = "general" | "account";

interface SettingsSidebarProps {
  activeTab: SettingsTab;
}

const menuItems: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
  { id: "general", label: "General", icon: Settings },
  { id: "account", label: "Account", icon: User },
];

export default function SettingsSidebar({ activeTab }: SettingsSidebarProps) {
  return (
    <nav className="settings-sidebar">
      <ul className="settings-sidebar-menu">
        {menuItems.map((item) => (
          <li key={item.id}>
            <Link
              href={`/settings/${item.id}`}
              className={`settings-sidebar-item ${activeTab === item.id ? "active" : ""}`}
            >
              <item.icon size={16} />
              <span>{item.label}</span>
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
