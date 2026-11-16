import { create } from "zustand"
import { persist } from "zustand/middleware"
import {
  projectApi,
  seriesBibleApi,
  characterApi,
  locationApi,
  episodeApi,
  sceneApi,
  dialogueApi,
  promptApi,
  assetApi,
  googleAccountApi,
  flowApi,
  storyEngineApi,
} from "@/lib/api"
import type {
  ProjectRead,
  SeriesBibleRead,
  CharacterRead,
  LocationRead,
  EpisodeRead,
  SceneRead,
  DialogueRead,
  PromptRead,
  AssetRead,
  GoogleAccountRead,
  FlowBridgeRead,
  StoryEngineRead,
} from "@/types/api"

interface ProjectState {
  // Current project
  currentProject: ProjectRead | null

  // Data
  projects: ProjectRead[]
  seriesBible: SeriesBibleRead | null
  characters: CharacterRead[]
  locations: LocationRead[]
  episodes: EpisodeRead[]
  scenes: SceneRead[]
  dialogues: DialogueRead[]
  prompts: PromptRead[]
  assets: AssetRead[]
  googleAccounts: GoogleAccountRead[]
  flowTasks: FlowBridgeRead[]
  storyGenerations: StoryEngineRead[]

  // UI State
  isLoading: boolean
  error: string | null
  selectedScene: string | null
  selectedEpisode: string | null

  // Actions
  setCurrentProject: (project: ProjectRead | null) => void
  setSelectedScene: (sceneId: string | null) => void
  setSelectedEpisode: (episodeId: string | null) => void
  setError: (error: string | null) => void
  clearError: () => void

  // Project actions
  fetchProjects: () => Promise<void>
  createProject: (data: any) => Promise<ProjectRead>
  updateProject: (id: string, data: any) => Promise<ProjectRead>
  deleteProject: (id: string) => Promise<void>

  // Series Bible actions
  fetchSeriesBible: (projectId: string) => Promise<void>
  createSeriesBible: (projectId: string, data: any) => Promise<SeriesBibleRead>
  updateSeriesBible: (projectId: string, data: any) => Promise<SeriesBibleRead>

  // Character actions
  fetchCharacters: (projectId: string) => Promise<void>
  createCharacter: (projectId: string, data: any) => Promise<CharacterRead>
  updateCharacter: (projectId: string, id: string, data: any) => Promise<CharacterRead>
  deleteCharacter: (projectId: string, id: string) => Promise<void>
  reorderCharacters: (projectId: string, ids: string[]) => Promise<void>

  // Location actions
  fetchLocations: (projectId: string) => Promise<void>
  createLocation: (projectId: string, data: any) => Promise<LocationRead>
  updateLocation: (projectId: string, id: string, data: any) => Promise<LocationRead>
  deleteLocation: (projectId: string, id: string) => Promise<void>
  reorderLocations: (projectId: string, ids: string[]) => Promise<void>

  // Episode actions
  fetchEpisodes: (projectId: string) => Promise<void>
  createEpisode: (projectId: string, data: any) => Promise<EpisodeRead>
  updateEpisode: (projectId: string, id: string, data: any) => Promise<EpisodeRead>
  deleteEpisode: (projectId: string, id: string) => Promise<void>
  reorderEpisodes: (projectId: string, ids: string[]) => Promise<void>

  // Scene actions
  fetchScenes: (episodeId: string) => Promise<void>
  createScene: (episodeId: string, data: any) => Promise<SceneRead>
  updateScene: (episodeId: string, id: string, data: any) => Promise<SceneRead>
  deleteScene: (episodeId: string, id: string) => Promise<void>
  reorderScenes: (episodeId: string, ids: string[]) => Promise<void>
  addCharacterToScene: (episodeId: string, sceneId: string, data: any) => Promise<SceneRead>
  removeCharacterFromScene: (episodeId: string, sceneId: string, characterId: string) => Promise<SceneRead>

  // Dialogue actions
  fetchDialogues: (sceneId: string) => Promise<void>
  createDialogue: (sceneId: string, data: any) => Promise<DialogueRead>
  updateDialogue: (sceneId: string, id: string, data: any) => Promise<DialogueRead>
  deleteDialogue: (sceneId: string, id: string) => Promise<void>
  reorderDialogues: (sceneId: string, ids: string[]) => Promise<void>

  // Prompt actions
  fetchPrompts: (projectId: string, params?: any) => Promise<void>
  createPrompt: (data: any) => Promise<PromptRead>
  updatePrompt: (projectId: string, id: string, data: any) => Promise<PromptRead>
  deletePrompt: (projectId: string, id: string) => Promise<void>
  generatePrompt: (data: any) => Promise<PromptRead>

  // Asset actions
  fetchAssets: (projectId: string, params?: any) => Promise<void>
  createAsset: (data: any) => Promise<AssetRead>
  updateAsset: (projectId: string, id: string, data: any) => Promise<AssetRead>
  deleteAsset: (projectId: string, id: string) => Promise<void>
  initUpload: (data: any) => Promise<any>
  completeUpload: (assetId: string, filePath: string) => Promise<AssetRead>

  // Google Account actions
  fetchGoogleAccounts: () => Promise<void>
  createGoogleAccount: (data: any) => Promise<GoogleAccountRead>
  updateGoogleAccount: (id: string, data: any) => Promise<GoogleAccountRead>
  deleteGoogleAccount: (id: string) => Promise<void>
  startOAuth: (data?: any) => Promise<any>
  oauthCallback: (data: any) => Promise<GoogleAccountRead>

  // Flow Bridge actions
  fetchFlowTasks: (projectId: string, params?: any) => Promise<void>
  createFlowTask: (data: any) => Promise<FlowBridgeRead>
  updateFlowTask: (projectId: string, id: string, data: any) => Promise<FlowBridgeRead>
  deleteFlowTask: (projectId: string, id: string) => Promise<void>
  exportForFlow: (data: any) => Promise<any>
  importFromFlow: (data: any) => Promise<FlowBridgeRead>
  getFlowDeeplink: (projectId: string, id: string) => Promise<any>

  // Story Engine actions
  fetchStoryGenerations: (projectId: string, params?: any) => Promise<void>
  generateStory: (data: any) => Promise<StoryEngineRead>
  deleteStoryGeneration: (projectId: string, id: string) => Promise<void>
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      // State
      currentProject: null,
      projects: [],
      seriesBible: null,
      characters: [],
      locations: [],
      episodes: [],
      scenes: [],
      dialogues: [],
      prompts: [],
      assets: [],
      googleAccounts: [],
      flowTasks: [],
      storyGenerations: [],
      isLoading: false,
      error: null,
      selectedScene: null,
      selectedEpisode: null,

      // Basic actions
      setCurrentProject: (project) => set({ currentProject: project }),
      setSelectedScene: (sceneId) => set({ selectedScene: sceneId }),
      setSelectedEpisode: (episodeId) => set({ selectedEpisode: episodeId }),
      setError: (error) => set({ error }),
      clearError: () => set({ error: null }),

      // Project actions
      fetchProjects: async () => {
        set({ isLoading: true, error: null })
        try {
          const response = await projectApi.list()
          set({ projects: response.data.items, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch projects", isLoading: false })
        }
      },

      createProject: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await projectApi.create(data)
          set((state) => ({ projects: [response.data, ...state.projects], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create project", isLoading: false })
          throw error
        }
      },

      updateProject: async (id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await projectApi.update(id, data)
          set((state) => ({
            projects: state.projects.map((p) => (p.id === id ? response.data : p)),
            currentProject: state.currentProject?.id === id ? response.data : state.currentProject,
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update project", isLoading: false })
          throw error
        }
      },

      deleteProject: async (id) => {
        set({ isLoading: true, error: null })
        try {
          await projectApi.delete(id)
          set((state) => ({
            projects: state.projects.filter((p) => p.id !== id),
            currentProject: state.currentProject?.id === id ? null : state.currentProject,
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete project", isLoading: false })
          throw error
        }
      },

      // Series Bible actions
      fetchSeriesBible: async (projectId) => {
        set({ isLoading: true, error: null })
        try {
          const response = await seriesBibleApi.get(projectId)
          set({ seriesBible: response.data, isLoading: false })
        } catch (error: any) {
          if (error.response?.status !== 404) {
            set({ error: error.response?.data?.detail || "Failed to fetch series bible" })
          }
          set({ seriesBible: null, isLoading: false })
        }
      },

      createSeriesBible: async (projectId, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await seriesBibleApi.create(projectId, data)
          set({ seriesBible: response.data, isLoading: false })
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create series bible", isLoading: false })
          throw error
        }
      },

      updateSeriesBible: async (projectId, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await seriesBibleApi.update(projectId, data)
          set({ seriesBible: response.data, isLoading: false })
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update series bible", isLoading: false })
          throw error
        }
      },

      // Character actions
      fetchCharacters: async (projectId) => {
        set({ isLoading: true, error: null })
        try {
          const response = await characterApi.list(projectId)
          set({ characters: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch characters", isLoading: false })
        }
      },

      createCharacter: async (projectId, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await characterApi.create(projectId, data)
          set((state) => ({ characters: [...state.characters, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create character", isLoading: false })
          throw error
        }
      },

      updateCharacter: async (projectId, id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await characterApi.update(projectId, id, data)
          set((state) => ({
            characters: state.characters.map((c) => (c.id === id ? response.data : c)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update character", isLoading: false })
          throw error
        }
      },

      deleteCharacter: async (projectId, id) => {
        set({ isLoading: true, error: null })
        try {
          await characterApi.delete(projectId, id)
          set((state) => ({
            characters: state.characters.filter((c) => c.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete character", isLoading: false })
          throw error
        }
      },

      reorderCharacters: async (projectId, ids) => {
        set({ isLoading: true, error: null })
        try {
          const response = await characterApi.reorder(projectId, ids)
          set({ characters: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to reorder characters", isLoading: false })
        }
      },

      // Location actions
      fetchLocations: async (projectId) => {
        set({ isLoading: true, error: null })
        try {
          const response = await locationApi.list(projectId)
          set({ locations: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch locations", isLoading: false })
        }
      },

      createLocation: async (projectId, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await locationApi.create(projectId, data)
          set((state) => ({ locations: [...state.locations, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create location", isLoading: false })
          throw error
        }
      },

      updateLocation: async (projectId, id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await locationApi.update(projectId, id, data)
          set((state) => ({
            locations: state.locations.map((l) => (l.id === id ? response.data : l)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update location", isLoading: false })
          throw error
        }
      },

      deleteLocation: async (projectId, id) => {
        set({ isLoading: true, error: null })
        try {
          await locationApi.delete(projectId, id)
          set((state) => ({
            locations: state.locations.filter((l) => l.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete location", isLoading: false })
          throw error
        }
      },

      reorderLocations: async (projectId, ids) => {
        set({ isLoading: true, error: null })
        try {
          const response = await locationApi.reorder(projectId, ids)
          set({ locations: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to reorder locations", isLoading: false })
        }
      },

      // Episode actions
      fetchEpisodes: async (projectId) => {
        set({ isLoading: true, error: null })
        try {
          const response = await episodeApi.list(projectId)
          set({ episodes: response.data.items, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch episodes", isLoading: false })
        }
      },

      createEpisode: async (projectId, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await episodeApi.create(projectId, data)
          set((state) => ({ episodes: [...state.episodes, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create episode", isLoading: false })
          throw error
        }
      },

      updateEpisode: async (projectId, id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await episodeApi.update(projectId, id, data)
          set((state) => ({
            episodes: state.episodes.map((e) => (e.id === id ? response.data : e)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update episode", isLoading: false })
          throw error
        }
      },

      deleteEpisode: async (projectId, id) => {
        set({ isLoading: true, error: null })
        try {
          await episodeApi.delete(projectId, id)
          set((state) => ({
            episodes: state.episodes.filter((e) => e.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete episode", isLoading: false })
          throw error
        }
      },

      reorderEpisodes: async (projectId, ids) => {
        set({ isLoading: true, error: null })
        try {
          const response = await episodeApi.reorder(projectId, ids)
          set({ episodes: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to reorder episodes", isLoading: false })
        }
      },

      // Scene actions
      fetchScenes: async (episodeId) => {
        set({ isLoading: true, error: null })
        try {
          const response = await sceneApi.list(episodeId)
          set({ scenes: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch scenes", isLoading: false })
        }
      },

      createScene: async (episodeId, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await sceneApi.create(episodeId, data)
          set((state) => ({ scenes: [...state.scenes, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create scene", isLoading: false })
          throw error
        }
      },

      updateScene: async (episodeId, id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await sceneApi.update(episodeId, id, data)
          set((state) => ({
            scenes: state.scenes.map((s) => (s.id === id ? response.data : s)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update scene", isLoading: false })
          throw error
        }
      },

      deleteScene: async (episodeId, id) => {
        set({ isLoading: true, error: null })
        try {
          await sceneApi.delete(episodeId, id)
          set((state) => ({
            scenes: state.scenes.filter((s) => s.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete scene", isLoading: false })
          throw error
        }
      },

      reorderScenes: async (episodeId, ids) => {
        set({ isLoading: true, error: null })
        try {
          const response = await sceneApi.reorder(episodeId, ids)
          set({ scenes: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to reorder scenes", isLoading: false })
        }
      },

      addCharacterToScene: async (episodeId, sceneId, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await sceneApi.addCharacter(episodeId, sceneId, data)
          set((state) => ({
            scenes: state.scenes.map((s) => (s.id === sceneId ? response.data : s)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to add character to scene", isLoading: false })
          throw error
        }
      },

      removeCharacterFromScene: async (episodeId, sceneId, characterId) => {
        set({ isLoading: true, error: null })
        try {
          const response = await sceneApi.removeCharacter(episodeId, sceneId, characterId)
          set((state) => ({
            scenes: state.scenes.map((s) => (s.id === sceneId ? response.data : s)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to remove character from scene", isLoading: false })
          throw error
        }
      },

      // Dialogue actions
      fetchDialogues: async (sceneId) => {
        set({ isLoading: true, error: null })
        try {
          const response = await dialogueApi.list(sceneId)
          set({ dialogues: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch dialogues", isLoading: false })
        }
      },

      createDialogue: async (sceneId, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await dialogueApi.create(sceneId, data)
          set((state) => ({ dialogues: [...state.dialogues, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create dialogue", isLoading: false })
          throw error
        }
      },

      updateDialogue: async (sceneId, id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await dialogueApi.update(sceneId, id, data)
          set((state) => ({
            dialogues: state.dialogues.map((d) => (d.id === id ? response.data : d)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update dialogue", isLoading: false })
          throw error
        }
      },

      deleteDialogue: async (sceneId, id) => {
        set({ isLoading: true, error: null })
        try {
          await dialogueApi.delete(sceneId, id)
          set((state) => ({
            dialogues: state.dialogues.filter((d) => d.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete dialogue", isLoading: false })
          throw error
        }
      },

      reorderDialogues: async (sceneId, ids) => {
        set({ isLoading: true, error: null })
        try {
          const response = await dialogueApi.reorder(sceneId, ids)
          set({ dialogues: response.data, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to reorder dialogues", isLoading: false })
        }
      },

      // Prompt actions
      fetchPrompts: async (projectId, params) => {
        set({ isLoading: true, error: null })
        try {
          const response = await promptApi.list(projectId, params)
          set({ prompts: response.data.items, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch prompts", isLoading: false })
        }
      },

      createPrompt: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await promptApi.create(data)
          set((state) => ({ prompts: [...state.prompts, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create prompt", isLoading: false })
          throw error
        }
      },

      updatePrompt: async (projectId, id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await promptApi.update(projectId, id, data)
          set((state) => ({
            prompts: state.prompts.map((p) => (p.id === id ? response.data : p)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update prompt", isLoading: false })
          throw error
        }
      },

      deletePrompt: async (projectId, id) => {
        set({ isLoading: true, error: null })
        try {
          await promptApi.delete(projectId, id)
          set((state) => ({
            prompts: state.prompts.filter((p) => p.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete prompt", isLoading: false })
          throw error
        }
      },

      generatePrompt: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await promptApi.generate(data)
          set((state) => ({ prompts: [...state.prompts, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to generate prompt", isLoading: false })
          throw error
        }
      },

      // Asset actions
      fetchAssets: async (projectId, params) => {
        set({ isLoading: true, error: null })
        try {
          const response = await assetApi.list(projectId, params)
          set({ assets: response.data.items, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch assets", isLoading: false })
        }
      },

      createAsset: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await assetApi.create(data)
          set((state) => ({ assets: [...state.assets, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create asset", isLoading: false })
          throw error
        }
      },

      updateAsset: async (projectId, id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await assetApi.update(projectId, id, data)
          set((state) => ({
            assets: state.assets.map((a) => (a.id === id ? response.data : a)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update asset", isLoading: false })
          throw error
        }
      },

      deleteAsset: async (projectId, id) => {
        set({ isLoading: true, error: null })
        try {
          await assetApi.delete(projectId, id)
          set((state) => ({
            assets: state.assets.filter((a) => a.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete asset", isLoading: false })
          throw error
        }
      },

      initUpload: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await assetApi.initUpload(data)
          set({ isLoading: false })
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to initialize upload", isLoading: false })
          throw error
        }
      },

      completeUpload: async (assetId, filePath) => {
        set({ isLoading: true, error: null })
        try {
          const response = await assetApi.completeUpload(assetId, { file_path: filePath })
          set((state) => ({
            assets: state.assets.map((a) => (a.id === assetId ? response.data : a)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to complete upload", isLoading: false })
          throw error
        }
      },

      // Google Account actions
      fetchGoogleAccounts: async () => {
        set({ isLoading: true, error: null })
        try {
          const response = await googleAccountApi.list()
          set({ googleAccounts: response.data.items, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch Google accounts", isLoading: false })
        }
      },

      createGoogleAccount: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await googleAccountApi.create(data)
          set((state) => ({ googleAccounts: [...state.googleAccounts, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create Google account", isLoading: false })
          throw error
        }
      },

      updateGoogleAccount: async (id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await googleAccountApi.update(id, data)
          set((state) => ({
            googleAccounts: state.googleAccounts.map((a) => (a.id === id ? response.data : a)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update Google account", isLoading: false })
          throw error
        }
      },

      deleteGoogleAccount: async (id) => {
        set({ isLoading: true, error: null })
        try {
          await googleAccountApi.delete(id)
          set((state) => ({
            googleAccounts: state.googleAccounts.filter((a) => a.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete Google account", isLoading: false })
          throw error
        }
      },

      startOAuth: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await googleAccountApi.startOAuth(data)
          set({ isLoading: false })
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to start OAuth", isLoading: false })
          throw error
        }
      },

      oauthCallback: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await googleAccountApi.oauthCallback(data)
          set((state) => ({ googleAccounts: [...state.googleAccounts, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "OAuth callback failed", isLoading: false })
          throw error
        }
      },

      // Flow Bridge actions
      fetchFlowTasks: async (projectId, params) => {
        set({ isLoading: true, error: null })
        try {
          const response = await flowApi.list(projectId, params)
          set({ flowTasks: response.data.items, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch Flow tasks", isLoading: false })
        }
      },

      createFlowTask: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await flowApi.create(data)
          set((state) => ({ flowTasks: [...state.flowTasks, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to create Flow task", isLoading: false })
          throw error
        }
      },

      updateFlowTask: async (projectId, id, data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await flowApi.update(projectId, id, data)
          set((state) => ({
            flowTasks: state.flowTasks.map((t) => (t.id === id ? response.data : t)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to update Flow task", isLoading: false })
          throw error
        }
      },

      deleteFlowTask: async (projectId, id) => {
        set({ isLoading: true, error: null })
        try {
          await flowApi.delete(projectId, id)
          set((state) => ({
            flowTasks: state.flowTasks.filter((t) => t.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete Flow task", isLoading: false })
          throw error
        }
      },

      exportForFlow: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await flowApi.export(data)
          set({ isLoading: false })
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to export for Flow", isLoading: false })
          throw error
        }
      },

      importFromFlow: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await flowApi.import(data)
          set((state) => ({
            flowTasks: state.flowTasks.map((t) => (t.id === response.data.id ? response.data : t)),
            isLoading: false,
          }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to import from Flow", isLoading: false })
          throw error
        }
      },

      getFlowDeeplink: async (projectId, id) => {
        set({ isLoading: true, error: null })
        try {
          const response = await flowApi.getDeeplink(projectId, id)
          set({ isLoading: false })
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to get Flow deeplink", isLoading: false })
          throw error
        }
      },

      // Story Engine actions
      fetchStoryGenerations: async (projectId, params) => {
        set({ isLoading: true, error: null })
        try {
          const response = await storyEngineApi.list(projectId, params)
          set({ storyGenerations: response.data.items, isLoading: false })
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to fetch story generations", isLoading: false })
        }
      },

      generateStory: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await storyEngineApi.generate(data)
          set((state) => ({ storyGenerations: [...state.storyGenerations, response.data], isLoading: false }))
          return response.data
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to generate story", isLoading: false })
          throw error
        }
      },

      deleteStoryGeneration: async (projectId, id) => {
        set({ isLoading: true, error: null })
        try {
          await storyEngineApi.delete(projectId, id)
          set((state) => ({
            storyGenerations: state.storyGenerations.filter((s) => s.id !== id),
            isLoading: false,
          }))
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Failed to delete story generation", isLoading: false })
          throw error
        }
      },
    }),
    {
      name: "project-storage",
      partialize: (state) => ({
        currentProject: state.currentProject,
        selectedScene: state.selectedScene,
        selectedEpisode: state.selectedEpisode,
      }),
    }
  )
)