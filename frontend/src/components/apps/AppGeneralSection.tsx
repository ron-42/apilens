"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";
import SettingsCard from "@/components/settings/SettingsCard";
import type { App } from "@/types/app";

interface AppGeneralSectionProps {
  app: App;
  onUpdate: (data: { name?: string; description?: string }) => Promise<void>;
}

export default function AppGeneralSection({ app, onUpdate }: AppGeneralSectionProps) {
  const [name, setName] = useState(app.name);
  const [description, setDescription] = useState(app.description);
  const [isSaving, setIsSaving] = useState(false);

  const hasChanges = name !== app.name || description !== app.description;

  const handleSave = async () => {
    if (!name.trim()) return;
    setIsSaving(true);
    try {
      const updates: { name?: string; description?: string } = {};
      if (name !== app.name) updates.name = name.trim();
      if (description !== app.description) updates.description = description.trim();
      await onUpdate(updates);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="settings-section-content">
      <SettingsCard title="App Details" description="Update your app name and description">
        <div className="app-general-form">
          <div className="create-app-field">
            <label htmlFor="app-name" className="create-app-label">
              App name
            </label>
            <input
              id="app-name"
              className="create-app-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={100}
            />
          </div>

          <div className="create-app-field">
            <label htmlFor="app-description" className="create-app-label">
              Description
            </label>
            <textarea
              id="app-description"
              className="create-app-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={500}
              rows={3}
            />
          </div>

          <div className="app-general-actions">
            <button
              className="settings-btn settings-btn-primary"
              disabled={isSaving || !hasChanges || !name.trim()}
              onClick={handleSave}
            >
              {isSaving ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Saving...
                </>
              ) : (
                "Save changes"
              )}
            </button>
          </div>
        </div>
      </SettingsCard>
    </div>
  );
}
