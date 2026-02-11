"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { X, Check } from "lucide-react";
import type { App } from "@/types/app";
import AppSettingsSidebar, { AppSettingsTab } from "./AppSettingsSidebar";
import AppGeneralSection from "./AppGeneralSection";
import AppApiKeysSection from "./AppApiKeysSection";
import AppDangerZoneSection from "./AppDangerZoneSection";

interface ToastState {
  type: "success" | "error";
  message: string;
}

interface AppSettingsPageProps {
  appSlug: string;
  initialTab?: AppSettingsTab;
}

export default function AppSettingsPage({ appSlug, initialTab = "general" }: AppSettingsPageProps) {
  const router = useRouter();
  const activeTab = initialTab;
  const [app, setApp] = useState<App | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [toast, setToast] = useState<ToastState | null>(null);

  const showToast = useCallback((type: "success" | "error", message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  }, []);

  const fetchApp = useCallback(async () => {
    try {
      const res = await fetch(`/api/apps/${appSlug}`);
      if (!res.ok) throw new Error("Failed to fetch app");
      const data = await res.json();
      setApp(data);
    } catch (error) {
      console.error("Error fetching app:", error);
    }
  }, [appSlug]);

  useEffect(() => {
    fetchApp().finally(() => setIsLoading(false));
  }, [fetchApp]);

  const handleUpdateApp = async (data: { name?: string; description?: string }) => {
    try {
      const res = await fetch(`/api/apps/${appSlug}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        const result = await res.json();
        throw new Error(result.error || "Failed to update app");
      }

      const updated = await res.json();
      setApp(updated);
      showToast("success", "App updated successfully");
    } catch (error) {
      showToast("error", error instanceof Error ? error.message : "Failed to update app");
    }
  };

  const handleDeleteApp = async () => {
    try {
      const res = await fetch(`/api/apps/${appSlug}`, {
        method: "DELETE",
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to delete app");
      }

      router.push("/apps");
    } catch (error) {
      showToast("error", error instanceof Error ? error.message : "Failed to delete app");
    }
  };

  if (isLoading) {
    return (
      <div className="settings-page">
        <div className="settings-page-header">
          <h1 className="settings-page-title">App Settings</h1>
        </div>
        <div className="settings-page-loading">
          <div className="loading-spinner" />
        </div>
      </div>
    );
  }

  if (!app) {
    return (
      <div className="settings-page">
        <div className="settings-page-header">
          <h1 className="settings-page-title">App not found</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="settings-page">
      {toast && (
        <div className={`settings-toast settings-toast-${toast.type}`}>
          <div className="settings-toast-icon">
            {toast.type === "success" ? <Check size={16} /> : <X size={16} />}
          </div>
          <span>{toast.message}</span>
          <button className="settings-toast-close" onClick={() => setToast(null)}>
            <X size={14} />
          </button>
        </div>
      )}

      <div className="settings-page-header">
        <h1 className="settings-page-title">{app.name} Settings</h1>
      </div>

      <div className="settings-page-body">
        <AppSettingsSidebar appSlug={appSlug} activeTab={activeTab} />

        <div className="settings-page-content">
          {activeTab === "general" && (
            <AppGeneralSection app={app} onUpdate={handleUpdateApp} />
          )}
          {activeTab === "api-keys" && (
            <div className="settings-section-content">
              <AppApiKeysSection appSlug={appSlug} showToast={showToast} />
            </div>
          )}
          {activeTab === "danger-zone" && (
            <div className="settings-section-content">
              <AppDangerZoneSection app={app} onDelete={handleDeleteApp} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
