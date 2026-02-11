import { getSession, setSession, clearSession } from "./session";

const DJANGO_API_URL = process.env.DJANGO_API_URL || "http://localhost:8000/api/v1";

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

export interface DjangoUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  picture: string;
  email_verified: boolean;
  has_password: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface DjangoUserContext {
  id: string;
  email: string;
  display_name: string;
  picture: string;
  is_authenticated: boolean;
  permissions: string[];
  role: string;
}

export interface SessionInfo {
  id: string;
  device_info: string;
  ip_address: string | null;
  location: string;
  last_used_at: string;
  created_at: string;
  is_current: boolean;
}

export interface ApiKeyInfo {
  id: string;
  name: string;
  prefix: string;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeyCreateResult {
  key: string;
  id: string;
  name: string;
  prefix: string;
  created_at: string;
}

export interface AppInfo {
  id: string;
  name: string;
  slug: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface AppListItem {
  id: string;
  name: string;
  slug: string;
  description: string;
  api_key_count: number;
  created_at: string;
}

async function fetchDjango<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const session = await getSession();
  if (!session) {
    return { error: "Not authenticated", status: 401 };
  }

  const url = `${DJANGO_API_URL}${endpoint}`;

  try {
    let response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.accessToken}`,
        ...options.headers,
      },
    });

    // Auto-refresh on 401
    if (response.status === 401) {
      const refreshResult = await refreshTokens(session.refreshToken);
      if (!refreshResult) {
        await clearSession();
        return { error: "Session expired", status: 401 };
      }

      response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${refreshResult.accessToken}`,
          ...options.headers,
        },
      });
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        error: errorData.detail || errorData.error || `Request failed with status ${response.status}`,
        status: response.status,
      };
    }

    const data = await response.json();
    return { data, status: response.status };
  } catch (error) {
    console.error(`API error (${endpoint}):`, error);
    return {
      error: error instanceof Error ? error.message : "Unknown error",
      status: 500,
    };
  }
}

async function refreshTokens(
  refreshToken: string,
): Promise<{ accessToken: string; refreshToken: string } | null> {
  try {
    const response = await fetch(`${DJANGO_API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) return null;

    const data = await response.json();

    const session = await getSession();
    if (session) {
      await setSession({
        ...session,
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
      });
    }

    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    };
  } catch {
    return null;
  }
}

export const apiClient = {
  async getCurrentUser(): Promise<ApiResponse<DjangoUser>> {
    return fetchDjango<DjangoUser>("/users/me");
  },

  async getUserContext(): Promise<ApiResponse<DjangoUserContext>> {
    return fetchDjango<DjangoUserContext>("/users/context");
  },

  async updateProfile(data: {
    first_name?: string;
    last_name?: string;
  }): Promise<ApiResponse<DjangoUser>> {
    return fetchDjango<DjangoUser>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteAccount(): Promise<ApiResponse<{ message: string }>> {
    return fetchDjango<{ message: string }>("/users/me", {
      method: "DELETE",
    });
  },

  async logoutAll(): Promise<ApiResponse<{ message: string }>> {
    return fetchDjango<{ message: string }>("/users/logout-all", {
      method: "POST",
    });
  },

  async getSessions(): Promise<ApiResponse<SessionInfo[]>> {
    return fetchDjango<SessionInfo[]>("/users/sessions");
  },

  async revokeSession(
    sessionId: string,
  ): Promise<ApiResponse<{ message: string }>> {
    return fetchDjango<{ message: string }>(`/users/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },

  async uploadPicture(file: Blob): Promise<ApiResponse<{ picture: string; message: string }>> {
    const session = await getSession();
    if (!session) {
      return { error: "Not authenticated", status: 401 };
    }

    const formData = new FormData();
    formData.append("file", file, "profile.jpg");

    const url = `${DJANGO_API_URL}/users/me/picture`;

    try {
      let response = await fetch(url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.accessToken}`,
        },
        body: formData,
      });

      if (response.status === 401) {
        const refreshResult = await refreshTokens(session.refreshToken);
        if (!refreshResult) {
          await clearSession();
          return { error: "Session expired", status: 401 };
        }

        response = await fetch(url, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${refreshResult.accessToken}`,
          },
          body: formData,
        });
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          error: errorData.detail || errorData.message || "Upload failed",
          status: response.status,
        };
      }

      const data = await response.json();
      return { data, status: response.status };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Upload failed",
        status: 500,
      };
    }
  },

  async removePicture(): Promise<ApiResponse<{ message: string }>> {
    return fetchDjango<{ message: string }>("/users/me/picture", {
      method: "DELETE",
    });
  },

  // ── Apps ──────────────────────────────────────────────────────────

  async getApps(): Promise<ApiResponse<AppListItem[]>> {
    return fetchDjango<AppListItem[]>("/apps");
  },

  async getApp(appId: string): Promise<ApiResponse<AppInfo>> {
    return fetchDjango<AppInfo>(`/apps/${appId}`);
  },

  async createApp(data: { name: string; description?: string }): Promise<ApiResponse<AppInfo>> {
    return fetchDjango<AppInfo>("/apps", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateApp(appId: string, data: { name?: string; description?: string }): Promise<ApiResponse<AppInfo>> {
    return fetchDjango<AppInfo>(`/apps/${appId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  async deleteApp(appId: string): Promise<ApiResponse<{ message: string }>> {
    return fetchDjango<{ message: string }>(`/apps/${appId}`, {
      method: "DELETE",
    });
  },

  // ── App-scoped API Keys ────────────────────────────────────────────

  async getAppApiKeys(appId: string): Promise<ApiResponse<ApiKeyInfo[]>> {
    return fetchDjango<ApiKeyInfo[]>(`/apps/${appId}/api-keys`);
  },

  async createAppApiKey(appId: string, name: string): Promise<ApiResponse<ApiKeyCreateResult>> {
    return fetchDjango<ApiKeyCreateResult>(`/apps/${appId}/api-keys`, {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },

  async revokeAppApiKey(appId: string, keyId: string): Promise<ApiResponse<{ message: string }>> {
    return fetchDjango<{ message: string }>(`/apps/${appId}/api-keys/${keyId}`, {
      method: "DELETE",
    });
  },

  async setPassword(data: {
    new_password: string;
    confirm_password: string;
    current_password?: string;
  }): Promise<ApiResponse<{ message: string }>> {
    return fetchDjango<{ message: string }>("/users/me/password", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async validateSession(refreshToken: string): Promise<ApiResponse<{ valid: boolean }>> {
    try {
      const response = await fetch(`${DJANGO_API_URL}/auth/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      const data = await response.json();
      return { data, status: response.status };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Validation failed",
        status: 500,
      };
    }
  },

  async healthCheck(): Promise<
    ApiResponse<{ status: string; service: string }>
  > {
    try {
      const response = await fetch(`${DJANGO_API_URL}/health`);
      const data = await response.json();
      return { data, status: response.status };
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "Unknown error",
        status: 500,
      };
    }
  },
};
