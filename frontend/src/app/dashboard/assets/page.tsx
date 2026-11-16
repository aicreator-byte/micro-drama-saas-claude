"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Select } from "@/components/ui/Select"
import { Plus, Edit, Trash2, Save, X, Image, Loader2, FileVideo, FileAudio, FileText, Download, Upload, Eye } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

const ASSET_TYPES = [
  { value: "character_image", label: "Character Image", icon: Image },
  { value: "location_image", label: "Location Image", icon: Image },
  { value: "scene_image", label: "Scene Image", icon: Image },
  { value: "video_clip", label: "Video Clip", icon: FileVideo },
  { value: "audio_clip", label: "Audio Clip", icon: FileAudio },
  { value: "background_music", label: "Background Music", icon: FileAudio },
  { value: "sound_effect", label: "Sound Effect", icon: FileAudio },
  { value: "subtitle_file", label: "Subtitle File", icon: FileText },
  { value: "final_episode", label: "Final Episode", icon: FileVideo },
  { value: "thumbnail", label: "Thumbnail", icon: Image },
  { value: "reference", label: "Reference", icon: Image },
]

const ASSET_STATUSES = [
  { value: "pending", label: "Pending" },
  { value: "uploading", label: "Uploading" },
  { value: "ready", label: "Ready" },
  { value: "failed", label: "Failed" },
]

export default function AssetsPage() {
  const {
    assets, fetchAssets, createAsset, updateAsset, deleteAsset, initUpload, completeUpload,
    episodes, fetchEpisodes,
    scenes, fetchScenes,
    isLoading
  } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string>("")
  const [selectedSceneId, setSelectedSceneId] = useState<string>("")
  const [assetTypeFilter, setAssetTypeFilter] = useState<string>("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingAsset, setEditingAsset] = useState<any>(null)
  const [formData, setFormData] = useState({
    asset_type: "character_image",
    file_name: "",
    file_path: "",
    file_size: "",
    mime_type: "",
    duration: "",
    width: "",
    height: "",
    status: "pending",
    episode_id: "",
    scene_id: "",
  })
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  useEffect(() => {
    if (selectedProjectId) {
      fetchAssets(selectedProjectId, {
        asset_type: assetTypeFilter || undefined,
        episode_id: selectedEpisodeId || undefined,
        scene_id: selectedSceneId || undefined,
        status: statusFilter || undefined,
      })
      fetchEpisodes(selectedProjectId)
    }
  }, [selectedProjectId, assetTypeFilter, selectedEpisodeId, selectedSceneId, statusFilter, fetchAssets, fetchEpisodes])

  useEffect(() => {
    if (selectedEpisodeId) {
      fetchScenes(selectedEpisodeId)
    }
  }, [selectedEpisodeId, fetchScenes])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProjectId) return

    try {
      const data = {
        ...formData,
        project_id: selectedProjectId,
        file_size: formData.file_size ? parseInt(formData.file_size) : undefined,
        duration: formData.duration ? parseFloat(formData.duration) : undefined,
        width: formData.width ? parseInt(formData.width) : undefined,
        height: formData.height ? parseInt(formData.height) : undefined,
        episode_id: formData.episode_id || undefined,
        scene_id: formData.scene_id || undefined,
      }

      if (editingAsset) {
        await updateAsset(selectedProjectId, editingAsset.id, data)
      } else {
        await createAsset(data)
      }
      setShowCreateModal(false)
      setEditingAsset(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save asset:", error)
    }
  }

  const handleEdit = (asset: any) => {
    setEditingAsset(asset)
    setFormData({
      asset_type: asset.asset_type,
      file_name: asset.file_name,
      file_path: asset.file_path,
      file_size: asset.file_size?.toString() || "",
      mime_type: asset.mime_type || "",
      duration: asset.duration?.toString() || "",
      width: asset.width?.toString() || "",
      height: asset.height?.toString() || "",
      status: asset.status,
      episode_id: asset.episode_id || "",
      scene_id: asset.scene_id || "",
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this asset?")) {
      try {
        await deleteAsset(selectedProjectId, id)
      } catch (error) {
        console.error("Failed to delete asset:", error)
      }
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selectedProjectId) return

    setUploading(true)
    setUploadProgress({ [file.name]: 0 })

    try {
      // Initialize upload
      const initResponse = await initUpload({
        project_id: selectedProjectId,
        episode_id: formData.episode_id || undefined,
        scene_id: formData.scene_id || undefined,
        asset_type: formData.asset_type,
        file_name: file.name,
        file_size: file.size,
        mime_type: file.type,
      })

      const { upload_id, upload_url } = initResponse

      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const current = prev[file.name] || 0
          if (current >= 90) {
            clearInterval(progressInterval)
            return prev
          }
          return { ...prev, [file.name]: current + 10 }
        })
      }, 200)

      // For local development, we'll simulate the upload
      // In production, this would be an actual S3 upload
      await new Promise(resolve => setTimeout(resolve, 1000))
      clearInterval(progressInterval)
      setUploadProgress(prev => ({ ...prev, [file.name]: 100 }))

      // Complete upload
      await completeUpload(upload_id, initResponse.file_path)

      setUploadProgress({})
      setUploading(false)
      // Reset file input
      e.target.value = ""
    } catch (error) {
      console.error("Upload failed:", error)
      setUploading(false)
      setUploadProgress({})
    }
  }

  const resetForm = () => {
    setFormData({
      asset_type: "character_image",
      file_name: "",
      file_path: "",
      file_size: "",
      mime_type: "",
      duration: "",
      width: "",
      height: "",
      status: "pending",
      episode_id: "",
      scene_id: "",
    })
  }

  const openCreateModal = () => {
    setEditingAsset(null)
    resetForm()
    setShowCreateModal(true)
  }

  const getAssetTypeIcon = (type: string) => {
    const typeInfo = ASSET_TYPES.find(t => t.value === type)
    return typeInfo ? typeInfo.icon : Image
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
      uploading: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
      ready: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
      failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
    }
    return colors[status] || colors.pending
  }

  const formatFileSize = (bytes?: number | null) => {
    if (!bytes) return "Unknown"
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  if (!user) return null

  const filteredAssets = assets.filter(a =>
    (!assetTypeFilter || a.asset_type === assetTypeFilter) &&
    (!statusFilter || a.status === statusFilter)
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Asset Manager</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Manage generated images, videos, audio, and other assets</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedProjectId}
              onChange={(e) => {
                setSelectedProjectId(e.target.value)
                setSelectedEpisodeId("")
                setSelectedSceneId("")
              }}
              className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-800 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.title}</option>
              ))}
            </select>

            {selectedProjectId && (
              <>
                <Select
                  value={assetTypeFilter}
                  onChange={(e) => setAssetTypeFilter(e.target.value)}
                  options={[{ value: "", label: "All Types" }, ...ASSET_TYPES]}
                  className="w-48"
                />
                <Select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  options={[{ value: "", label: "All Status" }, ...ASSET_STATUSES]}
                  className="w-40"
                />
                <Button onClick={openCreateModal}>
                  <Plus className="w-4 h-4" />
                  Add Asset
                </Button>
              </>
            )}
          </div>
        </div>

        {selectedProjectId && (
          <Card>
            <CardHeader>
              <CardTitle>Assets ({filteredAssets.length})</CardTitle>
              <CardDescription>Upload files or reference external URLs. Track status and metadata.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-24 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                  ))}
                </div>
              ) : filteredAssets.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                    <Image className="w-8 h-8 text-dark-400" />
                  </div>
                  <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No assets yet</h3>
                  <p className="text-dark-500 dark:text-dark-400 mb-6">Add your first asset</p>
                  <Button onClick={openCreateModal}>
                    <Plus className="w-4 h-4" />
                    Add Asset
                  </Button>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {filteredAssets.map((asset) => {
                    const Icon = getAssetTypeIcon(asset.asset_type)
                    return (
                      <div key={asset.id} className="p-4 rounded-lg border border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors group">
                        <div className="flex items-start justify-between mb-3">
                          <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                            <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                          </div>
                          <span className={clsx("text-xs font-medium px-2 py-1 rounded-full", getStatusColor(asset.status))}>
                            {asset.status}
                          </span>
                        </div>

                        <h4 className="font-medium text-dark-900 dark:text-white truncate mb-1">{asset.file_name}</h4>

                        <div className="space-y-1 text-sm text-dark-500 dark:text-dark-400 mb-3">
                          <p>{ASSET_TYPES.find(t => t.value === asset.asset_type)?.label || asset.asset_type}</p>
                          <p>{formatFileSize(asset.file_size)}</p>
                          {asset.duration && <p>{asset.duration.toFixed(1)}s</p>}
                          {asset.width && asset.height && <p>{asset.width}×{asset.height}</p>}
                        </div>

                        <div className="flex items-center gap-1">
                          {asset.status === "ready" && asset.file_path && (
                            <Button variant="ghost" size="sm" className="p-1.5" onClick={() => window.open(asset.file_path, "_blank")} title="View">
                              <Eye className="w-4 h-4" />
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(asset)} className="p-1.5">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(asset.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {!selectedProjectId && projects.length === 0 && (
          <Card variant="outlined">
            <CardContent className="p-12 text-center">
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No projects yet</h3>
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start managing assets</p>
              <Button onClick={() => window.location.href = "/dashboard/projects"}>
                Create Project
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Create/Edit Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowCreateModal(false)}>
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{editingAsset ? "Edit Asset" : "New Asset"}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <Select
                  label="Asset Type"
                  value={formData.asset_type}
                  onChange={(e) => setFormData({ ...formData, asset_type: e.target.value })}
                  options={ASSET_TYPES}
                  required
                />

                <div className="grid grid-cols-2 gap-4">
                  <Select
                    label="Episode (Optional)"
                    value={formData.episode_id}
                    onChange={(e) => setFormData({ ...formData, episode_id: e.target.value })}
                    options={[
                      { value: "", label: "None" },
                      ...episodes.map(e => ({ value: e.id, label: `Ep ${e.episode_number}: ${e.title || "Untitled"}` }))
                    ]}
                  />
                  <Select
                    label="Scene (Optional)"
                    value={formData.scene_id}
                    onChange={(e) => setFormData({ ...formData, scene_id: e.target.value })}
                    options={[
                      { value: "", label: "None" },
                      ...scenes.map(s => ({ value: s.id, label: `Scene ${s.scene_number}: ${s.title || "Untitled"}` }))
                    ]}
                  />
                </div>

                <Input
                  label="File Name"
                  value={formData.file_name}
                  onChange={(e) => setFormData({ ...formData, file_name: e.target.value })}
                  placeholder="e.g., character_john.png"
                  required
                />

                <Input
                  label="File Path / URL"
                  value={formData.file_path}
                  onChange={(e) => setFormData({ ...formData, file_path: e.target.value })}
                  placeholder="S3 key, local path, or external URL"
                  required
                />

                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="File Size (bytes)"
                    type="number"
                    value={formData.file_size}
                    onChange={(e) => setFormData({ ...formData, file_size: e.target.value })}
                    placeholder="1024000"
                  />
                  <Input
                    label="MIME Type"
                    value={formData.mime_type}
                    onChange={(e) => setFormData({ ...formData, mime_type: e.target.value })}
                    placeholder="image/png, video/mp4, audio/wav"
                  />
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <Input
                    label="Duration (seconds)"
                    type="number"
                    step="0.1"
                    value={formData.duration}
                    onChange={(e) => setFormData({ ...formData, duration: e.target.value })}
                    placeholder="30.5"
                  />
                  <Input
                    label="Width (px)"
                    type="number"
                    value={formData.width}
                    onChange={(e) => setFormData({ ...formData, width: e.target.value })}
                    placeholder="1920"
                  />
                  <Input
                    label="Height (px)"
                    type="number"
                    value={formData.height}
                    onChange={(e) => setFormData({ ...formData, height: e.target.value })}
                    placeholder="1080"
                  />
                </div>

                <Select
                  label="Status"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  options={ASSET_STATUSES}
                />

                {/* File Upload Section */}
                {!editingAsset && (
                  <div className="border-t border-dark-200 dark:border-dark-700 pt-4">
                    <h4 className="font-medium text-dark-900 dark:text-white mb-3 flex items-center gap-2">
                      <Upload className="w-5 h-5" />
                      Upload File
                    </h4>
                    <input
                      type="file"
                      onChange={handleFileUpload}
                      disabled={uploading}
                      className="w-full px-4 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-800 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    {Object.keys(uploadProgress).length > 0 && (
                      <div className="mt-3 space-y-2">
                        {Object.entries(uploadProgress).map(([fileName, progress]) => (
                          <div key={fileName} className="space-y-1">
                            <div className="flex justify-between text-sm">
                              <span className="text-dark-700 dark:text-dark-300">{fileName}</span>
                              <span className="text-dark-500 dark:text-dark-400">{progress}%</span>
                            </div>
                            <div className="h-2 bg-dark-200 dark:bg-dark-700 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary-600 transition-all duration-300"
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={isLoading || uploading}>
                    <Save className="w-4 h-4" />
                    {editingAsset ? "Update" : "Create"}
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