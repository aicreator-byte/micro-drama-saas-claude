import axios, { AxiosError, InternalAxiosRequestConfig } from "axios"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    "Content-Type": "application/json",
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token")
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor to handle 401
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear auth and redirect to login
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
        localStorage.removeItem("user")
        window.location.href = "/login"
      }
    }
    return Promise.reject(error)
  }
)

// Auth endpoints
export const authApi = {
  register: (data: { email: string; username: string; password: string; full_name?: string }) =>
    api.post("/auth/register", data),
  login: (data: { email: string; password: string }) =>
    api.post("/auth/login", data),
  refresh: (refresh_token: string) =>
    // Backend expects a JSON object {refresh_token}; sending the raw
    // string used to 422 (audit ronde 2, P0-18).
    api.post("/auth/refresh", { refresh_token }),
  me: () => api.get("/auth/me"),
}

// Settings endpoints (AI providers + Google OAuth credentials)
export const settingsApi = {
  get: () => api.get("/settings"),
  update: (data: any) => api.patch("/settings", data),
}

// Project endpoints
export const projectApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get("/projects", { params }),
  create: (data: { title: string; description?: string; genre?: string; themes?: string }) =>
    api.post("/projects", data),
  get: (id: string) => api.get(`/projects/${id}`),
  update: (id: string, data: Partial<{ title: string; description: string; genre: string; themes: string; status: string }>) =>
    api.patch(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),
}

// Series Bible endpoints
export const seriesBibleApi = {
  create: (projectId: string, data: any) =>
    api.post(`/series-bible/${projectId}`, data),
  get: (projectId: string) => api.get(`/series-bible/${projectId}`),
  update: (projectId: string, data: any) =>
    api.patch(`/series-bible/${projectId}`, data),
  delete: (projectId: string) => api.delete(`/series-bible/${projectId}`),
}

// Character endpoints
export const characterApi = {
  list: (projectId: string) => api.get(`/characters/${projectId}`),
  create: (projectId: string, data: any) =>
    api.post(`/characters/${projectId}`, data),
  get: (projectId: string, id: string) => api.get(`/characters/${projectId}/${id}`),
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/characters/${projectId}/${id}`, data),
  delete: (projectId: string, id: string) => api.delete(`/characters/${projectId}/${id}`),
  reorder: (projectId: string, character_ids: string[]) =>
    api.post(`/characters/${projectId}/reorder`, { character_ids }),
}

// Location endpoints
export const locationApi = {
  list: (projectId: string) => api.get(`/locations/${projectId}`),
  create: (projectId: string, data: any) =>
    api.post(`/locations/${projectId}`, data),
  get: (projectId: string, id: string) => api.get(`/locations/${projectId}/${id}`),
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/locations/${projectId}/${id}`, data),
  delete: (projectId: string, id: string) => api.delete(`/locations/${projectId}/${id}`),
  reorder: (projectId: string, location_ids: string[]) =>
    api.post(`/locations/${projectId}/reorder`, { location_ids }),
}

// Episode endpoints
export const episodeApi = {
  list: (projectId: string, params?: { page?: number; page_size?: number; status?: string }) =>
    api.get(`/episodes/${projectId}`, { params }),
  create: (projectId: string, data: any) =>
    api.post(`/episodes/${projectId}`, data),
  get: (projectId: string, id: string) => api.get(`/episodes/${projectId}/${id}`),
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/episodes/${projectId}/${id}`, data),
  delete: (projectId: string, id: string) => api.delete(`/episodes/${projectId}/${id}`),
  reorder: (projectId: string, episode_ids: string[]) =>
    api.post(`/episodes/${projectId}/reorder`, { episode_ids }),
}

// Scene endpoints
export const sceneApi = {
  list: (episodeId: string, params?: { status?: string }) =>
    api.get(`/scenes/${episodeId}`, { params }),
  create: (episodeId: string, data: any) =>
    api.post(`/scenes/${episodeId}`, data),
  get: (episodeId: string, id: string) => api.get(`/scenes/${episodeId}/${id}`),
  update: (episodeId: string, id: string, data: any) =>
    api.patch(`/scenes/${episodeId}/${id}`, data),
  delete: (episodeId: string, id: string) => api.delete(`/scenes/${episodeId}/${id}`),
  reorder: (episodeId: string, scene_ids: string[]) =>
    api.post(`/scenes/${episodeId}/reorder`, { scene_ids }),
  addCharacter: (episodeId: string, sceneId: string, data: { character_id: string; role_in_scene?: string; notes?: string }) =>
    api.post(`/scenes/${episodeId}/${sceneId}/characters`, data),
  removeCharacter: (episodeId: string, sceneId: string, characterId: string) =>
    api.delete(`/scenes/${episodeId}/${sceneId}/characters/${characterId}`),
}

// Dialogue endpoints
export const dialogueApi = {
  list: (sceneId: string) => api.get(`/dialogues/${sceneId}`),
  create: (sceneId: string, data: any) =>
    api.post(`/dialogues/${sceneId}`, data),
  get: (sceneId: string, id: string) => api.get(`/dialogues/${sceneId}/${id}`),
  update: (sceneId: string, id: string, data: any) =>
    api.patch(`/dialogues/${sceneId}/${id}`, data),
  delete: (sceneId: string, id: string) => api.delete(`/dialogues/${sceneId}/${id}`),
  reorder: (sceneId: string, dialogue_ids: string[]) =>
    api.post(`/dialogues/${sceneId}/reorder`, { dialogue_ids }),
}

// Prompt endpoints
export const promptApi = {
  list: (projectId: string, params?: { page?: number; page_size?: number; prompt_type?: string; episode_id?: string; scene_id?: string }) =>
    api.get(`/prompts/${projectId}`, { params }),
  create: (data: any) => api.post("/prompts", data),
  get: (projectId: string, id: string) => api.get(`/prompts/${projectId}/${id}`),
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/prompts/${projectId}/${id}`, data),
  delete: (projectId: string, id: string) => api.delete(`/prompts/${projectId}/${id}`),
  generate: (data: any) => api.post("/prompts/generate", data),
}

// Asset endpoints
export const assetApi = {
  list: (projectId: string, params?: { page?: number; page_size?: number; asset_type?: string; episode_id?: string; scene_id?: string; status?: string }) =>
    api.get(`/assets/${projectId}`, { params }),
  create: (data: any) => api.post("/assets", data),
  get: (projectId: string, id: string) => api.get(`/assets/${projectId}/${id}`),
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/assets/${projectId}/${id}`, data),
  delete: (projectId: string, id: string) => api.delete(`/assets/${projectId}/${id}`),
  initUpload: (data: any) => api.post("/assets/upload/init", data),
  completeUpload: (assetId: string, data: { file_path: string }) =>
    api.post(`/assets/upload/${assetId}`, data),
}

// Google Account endpoints
export const googleAccountApi = {
  list: (params?: { page?: number; page_size?: number; active_only?: boolean }) =>
    api.get("/google-accounts", { params }),
  create: (data: any) => api.post("/google-accounts", data),
  get: (id: string) => api.get(`/google-accounts/${id}`),
  update: (id: string, data: any) => api.patch(`/google-accounts/${id}`, data),
  delete: (id: string) => api.delete(`/google-accounts/${id}`),
  startOAuth: (data?: { redirect_url?: string }) => api.post("/google-accounts/oauth/start", data),
  oauthCallback: (data: { code: string; state?: string }) =>
    api.post("/google-accounts/oauth/callback", data),
}

// Flow Bridge endpoints
export const flowApi = {
  list: (projectId: string, params?: { page?: number; page_size?: number; status?: string; episode_id?: string; scene_id?: string }) =>
    api.get(`/flow/${projectId}`, { params }),
  create: (data: any) => api.post("/flow", data),
  get: (projectId: string, id: string) => api.get(`/flow/${projectId}/${id}`),
  update: (projectId: string, id: string, data: any) =>
    api.patch(`/flow/${projectId}/${id}`, data),
  delete: (projectId: string, id: string) => api.delete(`/flow/${projectId}/${id}`),
  export: (data: any) => api.post("/flow/export", data),
  import: (data: any) => api.post("/flow/import", data),
  getDeeplink: (projectId: string, id: string) => api.get(`/flow/${projectId}/${id}/deeplink`),
}

// Story Engine endpoints
export const storyEngineApi = {
  generate: (data: any) => api.post("/story-engine/generate", data),
  list: (projectId: string, params?: { page?: number; page_size?: number; generation_type?: string; episode_id?: string; scene_id?: string }) =>
    api.get(`/story-engine/${projectId}`, { params }),
  get: (projectId: string, id: string) => api.get(`/story-engine/${projectId}/${id}`),
  delete: (projectId: string, id: string) => api.delete(`/story-engine/${projectId}/${id}`),
}

// Auto-Generate endpoints (Fase 1 backend: POST runs the 5 steps synchronously
// and returns the finished job; GET is polled only while status === "running").
export const autoGenerateApi = {
  create: (projectId: string, data: { title: string; genre?: string; total_episodes?: number; premise?: string }) =>
    api.post(`/projects/${projectId}/auto-generate`, data),
  get: (projectId: string, jobId: string) =>
    api.get(`/projects/${projectId}/auto-generate/${jobId}`),
  retry: (projectId: string, jobId: string, step: string) =>
    api.post(`/projects/${projectId}/auto-generate/${jobId}/retry/${step}`),
}