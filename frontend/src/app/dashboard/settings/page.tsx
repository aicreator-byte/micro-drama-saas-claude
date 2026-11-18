"use client"

import { useEffect, useState } from "react"
import { useAuthStore } from "@/lib/auth-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { User, Lock, Save, Loader2, AlertCircle, CheckCircle, Cpu, KeyRound } from "lucide-react"
import { clsx } from "clsx"
import { settingsApi } from "@/lib/api"

interface AIProvider {
  id: string
  provider: string
  model: string
  key_env: string
  enabled: boolean
  priority: number
  key_configured: boolean
}

type TabId = "profile" | "ai-providers" | "google-oauth" | "security" | "account"

export default function SettingsPage() {
  const { user, logout } = useAuthStore()

  const [activeTab, setActiveTab] = useState<TabId>("ai-providers")
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  // Real settings from GET /api/settings
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [googleOAuthConfigured, setGoogleOAuthConfigured] = useState(false)
  const [oauthForm, setOauthForm] = useState({ client_id: "", client_secret: "" })

  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      try {
        const res = await settingsApi.get()
        setProviders(res.data.ai_providers || [])
        setGoogleOAuthConfigured(!!res.data.google_oauth_configured)
      } catch (error: any) {
        setMessage({ type: "error", text: error.response?.data?.detail || "Failed to load settings" })
      } finally {
        setIsLoading(false)
      }
    }
    load()
  }, [])

  const handleSaveProviders = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setMessage(null)
    try {
      const res = await settingsApi.update({ ai_providers: providers })
      setProviders(res.data.ai_providers || [])
      setMessage({ type: "success", text: "AI providers saved" })
    } catch (error: any) {
      setMessage({ type: "error", text: error.response?.data?.detail || "Failed to save AI providers" })
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveOAuth = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setMessage(null)
    try {
      const res = await settingsApi.update({
        google_oauth_client_id: oauthForm.client_id || undefined,
        google_oauth_client_secret: oauthForm.client_secret || undefined,
      })
      setGoogleOAuthConfigured(!!res.data.google_oauth_configured)
      setOauthForm({ client_id: "", client_secret: "" })
      setMessage({ type: "success", text: "Google OAuth credentials saved (encrypted server-side)" })
    } catch (error: any) {
      setMessage({ type: "error", text: error.response?.data?.detail || "Failed to save Google OAuth credentials" })
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteAccount = () => {
    if (confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
      // No backend endpoint exists for account deletion yet — say so honestly.
      alert("Account deletion is not available yet: there is no backend endpoint for it.")
    }
  }

  const tabs: { id: TabId; label: string; icon: any }[] = [
    { id: "profile", label: "Profile", icon: User },
    { id: "ai-providers", label: "AI Providers", icon: Cpu },
    { id: "google-oauth", label: "Google OAuth", icon: KeyRound },
    { id: "security", label: "Security", icon: Lock },
    { id: "account", label: "Account", icon: AlertCircle },
  ]

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Settings</h1>
          <p className="text-dark-600 dark:text-dark-400 mt-1">Manage AI providers, Google OAuth, and your account</p>
        </div>

        {/* Tabs */}
        <Card variant="outlined">
          <CardContent className="p-0">
            <div className="border-b border-dark-200 dark:border-dark-700">
              <nav className="flex flex-wrap" aria-label="Settings tabs">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={clsx(
                      "flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-colors",
                      activeTab === tab.id
                        ? "border-primary-600 text-primary-600 dark:text-primary-400"
                        : "border-transparent text-dark-500 hover:text-dark-700 dark:text-dark-400 dark:hover:text-white"
                    )}
                    aria-current={activeTab === tab.id ? "page" : undefined}
                  >
                    <tab.icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                ))}
              </nav>
            </div>

            <div className="p-6">
              {message && (
                <div className={clsx(
                  "flex items-center gap-2 p-3 rounded-lg mb-4",
                  message.type === "success"
                    ? "bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300"
                    : "bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300"
                )}>
                  {message.type === "success" ? (
                    <CheckCircle className="w-4 h-4 flex-shrink-0" />
                  ) : (
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  )}
                  <span>{message.text}</span>
                </div>
              )}

              {isLoading && (
                <div className="flex items-center gap-2 text-dark-500 dark:text-dark-400 py-4">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading settings…
                </div>
              )}

              {/* Profile Tab — read-only: no backend endpoint for profile updates yet */}
              {activeTab === "profile" && (
                <div className="space-y-4">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-20 h-20 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                      <span className="text-2xl font-bold text-primary-700 dark:text-primary-300">
                        {user?.username?.charAt(0).toUpperCase() || "U"}
                      </span>
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-dark-900 dark:text-white">{user?.username}</h3>
                      <p className="text-dark-500 dark:text-dark-400">{user?.email}</p>
                      {user?.full_name && <p className="text-dark-500 dark:text-dark-400">{user.full_name}</p>}
                    </div>
                  </div>
                  <p className="text-sm text-dark-500 dark:text-dark-400">
                    Profile editing is not available yet — the backend has no profile-update
                    endpoint. What you see above is your account as registered.
                  </p>
                </div>
              )}

              {/* AI Providers Tab — wired to GET/PATCH /api/settings */}
              {activeTab === "ai-providers" && !isLoading && (
                <form onSubmit={handleSaveProviders} className="space-y-4">
                  <p className="text-sm text-dark-500 dark:text-dark-400">
                    Providers are tried in priority order. API keys are read from the server
                    environment (never shown here) — <code>key_configured</code> only tells
                    whether the key exists.
                  </p>
                  {providers.length === 0 && (
                    <p className="text-sm text-dark-500 dark:text-dark-400">No providers configured.</p>
                  )}
                  {providers.map((p, idx) => (
                    <Card key={p.id} variant="outlined">
                      <CardContent className="space-y-3 pt-4">
                        <div className="flex items-center justify-between">
                          <h4 className="font-medium text-dark-900 dark:text-white">
                            {p.provider} <span className="text-sm text-dark-500">({p.id})</span>
                          </h4>
                          <span className={clsx(
                            "text-xs font-medium px-2 py-1 rounded-full",
                            p.key_configured
                              ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                              : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300"
                          )}>
                            {p.key_configured ? `Key configured (${p.key_env})` : `Key missing (${p.key_env})`}
                          </span>
                        </div>
                        <Input
                          label="Model"
                          value={p.model}
                          onChange={(e) => setProviders(providers.map((x, i) => i === idx ? { ...x, model: e.target.value } : x))}
                        />
                        <div className="flex items-center gap-4">
                          <label className="flex items-center gap-2 text-sm text-dark-700 dark:text-dark-300">
                            <input
                              type="checkbox"
                              checked={p.enabled}
                              onChange={(e) => setProviders(providers.map((x, i) => i === idx ? { ...x, enabled: e.target.checked } : x))}
                            />
                            Enabled
                          </label>
                          <label className="flex items-center gap-2 text-sm text-dark-700 dark:text-dark-300">
                            Priority
                            <input
                              type="number"
                              min={1}
                              value={p.priority}
                              onChange={(e) => setProviders(providers.map((x, i) => i === idx ? { ...x, priority: Number(e.target.value) || 1 } : x))}
                              className="w-16 px-2 py-1 border border-dark-200 dark:border-dark-700 rounded bg-transparent"
                            />
                          </label>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                  <Button type="submit" loading={isSaving} disabled={providers.length === 0}>
                    <Save className="w-4 h-4" />
                    Save Providers
                  </Button>
                </form>
              )}

              {/* Google OAuth Tab — wired to PATCH /api/settings */}
              {activeTab === "google-oauth" && !isLoading && (
                <form onSubmit={handleSaveOAuth} className="space-y-4">
                  <div className="mb-4 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
                    <h4 className="font-medium text-primary-800 dark:text-primary-200 mb-2">
                      Google OAuth {googleOAuthConfigured ? "— configured" : "— not configured"}
                    </h4>
                    <p className="text-sm text-primary-700 dark:text-primary-300">
                      These credentials enable “Connect Google Account (OAuth)” on the Google
                      Accounts page. They are stored encrypted server-side and are never
                      returned by the API — leave a field blank to keep its current value.
                    </p>
                  </div>

                  <Input
                    label="Google OAuth Client ID"
                    value={oauthForm.client_id}
                    onChange={(e) => setOauthForm({ ...oauthForm, client_id: e.target.value })}
                    placeholder="1234567890-abc.apps.googleusercontent.com"
                    autoComplete="off"
                  />

                  <Input
                    label="Google OAuth Client Secret"
                    type="password"
                    value={oauthForm.client_secret}
                    onChange={(e) => setOauthForm({ ...oauthForm, client_secret: e.target.value })}
                    placeholder="GOCSPX-••••••••"
                    autoComplete="off"
                  />

                  <Button type="submit" loading={isSaving}>
                    <Save className="w-4 h-4" />
                    Save OAuth Credentials
                  </Button>
                </form>
              )}

              {/* Security Tab — honest: no change-password endpoint exists yet */}
              {activeTab === "security" && (
                <div className="space-y-4">
                  <div className="mb-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
                    <h4 className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">Change Password — not available yet</h4>
                    <p className="text-sm text-yellow-700 dark:text-yellow-300">
                      The backend has no change-password endpoint yet, so this form is disabled
                      rather than pretending to succeed. Passwords can currently only be set at
                      registration.
                    </p>
                  </div>
                  <Input label="Current Password" type="password" value="" disabled placeholder="••••••••" />
                  <Input label="New Password" type="password" value="" disabled placeholder="••••••••" />
                  <Input label="Confirm New Password" type="password" value="" disabled placeholder="••••••••" />
                  <Button type="button" disabled>
                    <Save className="w-4 h-4" />
                    Update Password
                  </Button>
                </div>
              )}

              {/* Account Tab */}
              {activeTab === "account" && (
                <div className="space-y-6">
                  <Card variant="outlined">
                    <CardHeader>
                      <CardTitle className="text-red-600 dark:text-red-400 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5" />
                        Danger Zone
                      </CardTitle>
                      <CardDescription>Irreversible actions. Please be careful.</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center justify-between p-4 border border-dark-200 dark:border-dark-700 rounded-lg">
                        <div>
                          <h4 className="font-medium text-dark-900 dark:text-white">Delete Account</h4>
                          <p className="text-sm text-dark-500 dark:text-dark-400 mt-1">
                            Permanently delete your account and all associated data including projects, characters, and assets.
                          </p>
                        </div>
                        <Button variant="destructive" onClick={handleDeleteAccount}>
                          Delete Account
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Session Management</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between p-3 border border-dark-200 dark:border-dark-700 rounded-lg">
                          <div>
                            <p className="font-medium text-dark-900 dark:text-white">Current Session</p>
                            <p className="text-sm text-dark-500 dark:text-dark-400">Active on this device</p>
                          </div>
                          <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full">
                            Active
                          </span>
                        </div>
                        <Button variant="outline" onClick={() => logout()}>
                          <Loader2 className="w-4 h-4" />
                          Sign Out Everywhere
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
