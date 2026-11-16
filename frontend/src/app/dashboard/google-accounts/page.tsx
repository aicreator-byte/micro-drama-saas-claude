"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Plus, Edit, Trash2, Save, X, User, Loader2, Mail, CheckCircle, AlertCircle, RefreshCw, ExternalLink } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

export default function GoogleAccountsPage() {
  const {
    googleAccounts, fetchGoogleAccounts, createGoogleAccount, updateGoogleAccount, deleteGoogleAccount,
    startOAuth, oauthCallback,
    isLoading
  } = useProjectStore()
  const { user } = useAuthStore()

  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingAccount, setEditingAccount] = useState<any>(null)
  const [formData, setFormData] = useState({
    email: "",
    display_name: "",
    access_token: "",
    refresh_token: "",
    token_expiry: "",
    scopes: '["drive", "photos", "youtube"]',
  })
  const [oauthInitiated, setOauthInitiated] = useState(false)
  const [oauthUrl, setOauthUrl] = useState("")

  useEffect(() => {
    fetchGoogleAccounts()
  }, [fetchGoogleAccounts])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    try {
      const data = {
        ...formData,
        scopes: formData.scopes ? JSON.parse(formData.scopes) : undefined,
        token_expiry: formData.token_expiry || undefined,
        access_token: formData.access_token || undefined,
        refresh_token: formData.refresh_token || undefined,
      }

      if (editingAccount) {
        await updateGoogleAccount(editingAccount.id, data)
      } else {
        await createGoogleAccount(data)
      }
      setShowCreateModal(false)
      setEditingAccount(null)
      resetForm()
    } catch (error: any) {
      console.error("Failed to save Google account:", error)
      alert(error.response?.data?.detail || "Failed to save account")
    }
  }

  const handleEdit = (account: any) => {
    setEditingAccount(account)
    setFormData({
      email: account.email,
      display_name: account.display_name || "",
      access_token: "",
      refresh_token: "",
      token_expiry: "",
      scopes: '["drive", "photos", "youtube"]',
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to disconnect this Google account?")) {
      try {
        await deleteGoogleAccount(id)
      } catch (error) {
        console.error("Failed to delete account:", error)
      }
    }
  }

  const handleStartOAuth = async () => {
    try {
      const result = await startOAuth()
      setOauthUrl(result.authorization_url)
      setOauthInitiated(true)
      // Open in new tab
      window.open(result.authorization_url, "_blank", "width=600,height=700")
    } catch (error) {
      console.error("Failed to start OAuth:", error)
      alert("Failed to start OAuth flow")
    }
  }

  const handleOAuthCallback = async () => {
    const code = prompt("Enter the authorization code from Google:")
    if (!code) return

    try {
      await oauthCallback({ code, state: user?.id })
      setOauthInitiated(false)
      setOauthUrl("")
    } catch (error) {
      console.error("OAuth callback failed:", error)
      alert("OAuth callback failed")
    }
  }

  const resetForm = () => {
    setFormData({
      email: "",
      display_name: "",
      access_token: "",
      refresh_token: "",
      token_expiry: "",
      scopes: '["drive", "photos", "youtube"]',
    })
  }

  const openCreateModal = () => {
    setEditingAccount(null)
    resetForm()
    setShowCreateModal(true)
  }

  const getStatusIcon = (isActive: boolean) => {
    return isActive ? (
      <CheckCircle className="w-5 h-5 text-green-500" />
    ) : (
      <AlertCircle className="w-5 h-5 text-red-500" />
    )
  }

  if (!user) return null

  const connectedCount = googleAccounts.filter(a => a.is_active).length
  const maxAccounts = 20

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Google Accounts</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Connect and manage Google accounts for Flow integration</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-sm text-dark-600 dark:text-dark-400">
              {connectedCount} / {maxAccounts} accounts connected
            </div>
            <div className="w-40 h-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-600 transition-all duration-300"
                style={{ width: `${(connectedCount / maxAccounts) * 100}%` }}
              />
            </div>
            <Button onClick={openCreateModal} disabled={connectedCount >= maxAccounts}>
              <Plus className="w-4 h-4" />
              Add Account
            </Button>
          </div>
        </div>

        {/* OAuth Flow */}
        <Card variant="outlined">
          <CardHeader>
            <CardTitle>Google OAuth Connection</CardTitle>
            <CardDescription>Connect your Google account via OAuth 2.0 for secure access to Drive, Photos, and YouTube.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!oauthInitiated ? (
              <Button onClick={handleStartOAuth} className="w-full sm:w-auto" size="lg">
                <ExternalLink className="w-4 h-4" />
                Connect Google Account (OAuth)
              </Button>
            ) : (
              <div className="space-y-3">
                <div className="p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
                  <p className="text-sm text-primary-800 dark:text-primary-200 mb-2">
                    OAuth initiated. Complete the flow in the opened window.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" size="sm" onClick={() => window.open(oauthUrl, "_blank")}>
                      <ExternalLink className="w-3 h-3" />
                      Reopen OAuth Window
                    </Button>
                    <Button onClick={handleOAuthCallback}>
                      <RefreshCw className="w-3 h-3" />
                      I've Authorized - Complete Setup
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setOauthInitiated(false)}>
                      <X className="w-3 h-3" />
                      Cancel
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Manual Account Entry */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Connected Accounts ({googleAccounts.length})</CardTitle>
                <CardDescription>Manually added accounts or accounts added via OAuth callback</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-16 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                ))}
              </div>
            ) : googleAccounts.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                  <User className="w-8 h-8 text-dark-400" />
                </div>
                <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No Google accounts connected</h3>
                <p className="text-dark-500 dark:text-dark-400 mb-6">Use OAuth or add manually for Flow integration</p>
                <Button onClick={openCreateModal}>
                  <Plus className="w-4 h-4" />
                  Add Manually
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {googleAccounts.map((account) => (
                  <div key={account.id} className="p-4 rounded-lg border border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                          {getStatusIcon(account.is_active)}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium text-dark-900 dark:text-white">{account.email}</h4>
                            {account.display_name && (
                              <span className="text-sm text-dark-500 dark:text-dark-400">{account.display_name}</span>
                            )}
                            <span className={clsx(
                              "text-xs font-medium px-2 py-1 rounded-full",
                              account.is_active
                                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                                : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                            )}>
                              {account.is_active ? "Active" : "Inactive"}
                            </span>
                          </div>
                          {account.last_used_at && (
                            <p className="text-xs text-dark-500 dark:text-dark-400 mt-1">
                              Last used: {new Date(account.last_used_at).toLocaleDateString()}
                            </p>
                          )}
                          {account.scopes && (
                            <p className="text-xs text-dark-500 dark:text-dark-400 mt-1 font-mono">
                              Scopes: {account.scopes}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(account)} className="p-1.5">
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(account.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Limits Info */}
        <Card variant="outlined">
          <CardHeader>
            <CardTitle>Account Limits</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm text-dark-600 dark:text-dark-400">
              <p>• Maximum 20 Google accounts per SaaS user</p>
              <p>• Each account is strictly isolated - other users cannot access your accounts</p>
              <p>• OAuth tokens are encrypted at rest using Fernet encryption</p>
              <p>• Accounts can be used for Google Flow integration (Drive, Photos, YouTube)</p>
              <p>• Never store Google passwords directly - only OAuth tokens</p>
            </div>
          </CardContent>
        </Card>

        {/* Create/Edit Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowCreateModal(false)}>
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{editingAccount ? "Edit Google Account" : "Add Google Account Manually"}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <div className="space-y-2">
                  <label htmlFor="email" className="block text-sm font-medium text-dark-700 dark:text-dark-300">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-400" />
                    <Input
                      id="email"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      placeholder="user@gmail.com"
                      required
                      className="pl-10"
                      disabled={editingAccount}
                    />
                  </div>
                </div>

                <Input
                  label="Display Name (Optional)"
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                  placeholder="My Google Account"
                />

                <Input
                  label="Access Token (Optional - for manual entry)"
                  type="password"
                  value={formData.access_token}
                  onChange={(e) => setFormData({ ...formData, access_token: e.target.value })}
                  placeholder="ya29.a0AfH6SMC..."
                />

                <Input
                  label="Refresh Token (Optional - for manual entry)"
                  type="password"
                  value={formData.refresh_token}
                  onChange={(e) => setFormData({ ...formData, refresh_token: e.target.value })}
                  placeholder="1//0g... (starts with 1//)"
                />

                <Input
                  label="Token Expiry (ISO 8601, Optional)"
                  value={formData.token_expiry}
                  onChange={(e) => setFormData({ ...formData, token_expiry: e.target.value })}
                  placeholder="2026-12-31T23:59:59Z"
                />

                <Textarea
                  label="Scopes (JSON array)"
                  value={formData.scopes}
                  onChange={(e) => setFormData({ ...formData, scopes: e.target.value })}
                  placeholder='["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/photoslibrary"]'
                  rows={2}
                />

                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    {editingAccount ? "Update" : "Add Account"}
                  </Button>
                </div>
              </form>
            </Card>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}