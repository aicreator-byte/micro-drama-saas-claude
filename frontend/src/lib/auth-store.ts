import { create } from "zustand"
import { persist } from "zustand/middleware"
import { api, authApi } from "@/lib/api"
import type { UserRead, Token } from "@/types/api"

interface AuthState {
  user: UserRead | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean | undefined
  isLoading: boolean
  error: string | null

  // Actions
  login: (email: string, password: string) => Promise<void>
  register: (data: { email: string; username: string; password: string; full_name?: string }) => Promise<void>
  logout: () => void
  checkAuth: () => Promise<void>
  refreshAccessToken: () => Promise<void>
  setUser: (user: UserRead) => void
  setTokens: (tokens: Token) => void
  clearError: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: undefined,
      isLoading: false,
      error: null,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.login({ email, password })
          const { access_token, refresh_token } = response.data
          get().setTokens({ access_token, refresh_token, token_type: "bearer" })

          // Fetch user info
          await get().checkAuth()
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Login failed", isLoading: false })
          throw error
        }
      },

      register: async (data) => {
        set({ isLoading: true, error: null })
        try {
          const response = await authApi.register(data)
          // Auto-login after registration
          await get().login(data.email, data.password)
        } catch (error: any) {
          set({ error: error.response?.data?.detail || "Registration failed", isLoading: false })
          throw error
        }
      },

      logout: () => {
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
        localStorage.removeItem("user")
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },

      checkAuth: async () => {
        const token = localStorage.getItem("access_token")
        if (!token) {
          set({ isAuthenticated: false, isLoading: false })
          return
        }

        set({ isLoading: true })
        try {
          const response = await authApi.me()
          set({
            user: response.data,
            isAuthenticated: true,
            isLoading: false,
          })
        } catch (error) {
          // Try to refresh token
          try {
            await get().refreshAccessToken()
            await get().checkAuth()
          } catch {
            get().logout()
          }
        }
      },

      refreshAccessToken: async () => {
        const refreshToken = localStorage.getItem("refresh_token")
        if (!refreshToken) throw new Error("No refresh token")

        try {
          const response = await authApi.refresh(refreshToken)
          const { access_token, refresh_token } = response.data
          get().setTokens({ access_token, refresh_token, token_type: "bearer" })
        } catch {
          get().logout()
          throw new Error("Token refresh failed")
        }
      },

      setUser: (user) => set({ user }),

      setTokens: (tokens) => {
        localStorage.setItem("access_token", tokens.access_token)
        localStorage.setItem("refresh_token", tokens.refresh_token)
        set({
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
        })
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)