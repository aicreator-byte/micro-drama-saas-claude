"use client"

import { useState } from "react"
import { useAuthStore } from "@/lib/auth-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { User, Mail, Lock, Save, Loader2, AlertCircle, CheckCircle } from "lucide-react"
import { clsx } from "clsx"

export default function SettingsPage() {
  const { user, logout } = useAuthStore()

  const [activeTab, setActiveTab] = useState<"profile" | "security" | "account">("profile")
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null)

  // Profile form
  const [profileData, setProfileData] = useState({
    username: user?.username || "",
    email: user?.email || "",
    full_name: user?.full_name || "",
  })

  // Security form
  const [securityData, setSecurityData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  })

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage(null)

    try {
      // In a real app, this would call an API endpoint
      // For now, just update local state
      setMessage({ type: "success", text: "Profile updated successfully" })
    } catch (error) {
      setMessage({ type: "error", text: "Failed to update profile" })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSecuritySubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage(null)

    if (securityData.new_password !== securityData.confirm_password) {
      setMessage({ type: "error", text: "New passwords do not match" })
      setIsLoading(false)
      return
    }

    if (securityData.new_password.length < 8) {
      setMessage({ type: "error", text: "Password must be at least 8 characters" })
      setIsLoading(false)
      return
    }

    try {
      // In a real app, this would call an API endpoint
      setSecurityData({ current_password: "", new_password: "", confirm_password: "" })
      setMessage({ type: "success", text: "Password updated successfully" })
    } catch (error) {
      setMessage({ type: "error", text: "Failed to update password" })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteAccount = () => {
    if (confirm("Are you sure you want to delete your account? This action cannot be undone.")) {
      if (confirm("This will permanently delete all your projects and data. Type 'DELETE' to confirm.")) {
        // In a real app, call delete account API
        alert("Account deletion not implemented in MVP")
      }
    }
  }

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "security", label: "Security", icon: Lock },
    { id: "account", label: "Account", icon: AlertCircle },
  ]

  return (
    <DashboardLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Settings</h1>
          <p className="text-dark-600 dark:text-dark-400 mt-1">Manage your account settings</p>
        </div>

        {/* Tabs */}
        <Card variant="outlined">
          <CardContent className="p-0">
            <div className="border-b border-dark-200 dark:border-dark-700">
              <nav className="flex" aria-label="Settings tabs">
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
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

              {/* Profile Tab */}
              {activeTab === "profile" && (
                <form onSubmit={handleProfileSubmit} className="space-y-4">
                  <div className="flex items-center gap-4 mb-6">
                    <div className="w-20 h-20 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                      <span className="text-2xl font-bold text-primary-700 dark:text-primary-300">
                        {user?.username?.charAt(0).toUpperCase() || "U"}
                      </span>
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-dark-900 dark:text-white">{user?.username}</h3>
                      <p className="text-dark-500 dark:text-dark-400">{user?.email}</p>
                    </div>
                  </div>

                  <Input
                    label="Username"
                    value={profileData.username}
                    onChange={(e) => setProfileData({ ...profileData, username: e.target.value })}
                    placeholder="Enter username"
                    required
                    minLength={3}
                    maxLength={100}
                  />

                  <Input
                    label="Email"
                    type="email"
                    value={profileData.email}
                    onChange={(e) => setProfileData({ ...profileData, email: e.target.value })}
                    placeholder="you@example.com"
                    required
                  />

                  <Input
                    label="Full Name"
                    value={profileData.full_name}
                    onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
                    placeholder="John Doe"
                  />

                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    Save Profile
                  </Button>
                </form>
              )}

              {/* Security Tab */}
              {activeTab === "security" && (
                <form onSubmit={handleSecuritySubmit} className="space-y-4">
                  <div className="mb-4 p-4 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
                    <h4 className="font-medium text-primary-800 dark:text-primary-200 mb-2">Change Password</h4>
                    <p className="text-sm text-primary-700 dark:text-primary-300">
                      Your password must be at least 8 characters long.
                    </p>
                  </div>

                  <Input
                    label="Current Password"
                    type="password"
                    value={securityData.current_password}
                    onChange={(e) => setSecurityData({ ...securityData, current_password: e.target.value })}
                    placeholder="••••••••"
                    required
                  />

                  <Input
                    label="New Password"
                    type="password"
                    value={securityData.new_password}
                    onChange={(e) => setSecurityData({ ...securityData, new_password: e.target.value })}
                    placeholder="••••••••"
                    required
                    minLength={8}
                  />

                  <Input
                    label="Confirm New Password"
                    type="password"
                    value={securityData.confirm_password}
                    onChange={(e) => setSecurityData({ ...securityData, confirm_password: e.target.value })}
                    placeholder="••••••••"
                    required
                    minLength={8}
                  />

                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    Update Password
                  </Button>
                </form>
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