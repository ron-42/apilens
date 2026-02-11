import { notFound } from "next/navigation";
import { AppSettingsPage } from "@/components/apps";
import type { AppSettingsTab } from "@/components/apps/AppSettingsSidebar";

const validTabs: AppSettingsTab[] = ["general", "api-keys", "danger-zone"];

export async function generateMetadata({ params }: { params: Promise<{ tab: string }> }) {
  const { tab } = await params;
  const tabTitles: Record<string, string> = {
    general: "General",
    "api-keys": "API Keys",
    "danger-zone": "Danger Zone",
  };

  return {
    title: `${tabTitles[tab] || "Settings"} — App Settings | APILens`,
  };
}

export default async function AppSettingsTabPage({
  params,
}: {
  params: Promise<{ id: string; tab: string }>;
}) {
  const { id, tab } = await params;

  if (!validTabs.includes(tab as AppSettingsTab)) {
    notFound();
  }

  return <AppSettingsPage appId={id} initialTab={tab as AppSettingsTab} />;
}
