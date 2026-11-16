"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Select } from "@/components/ui/Select"
import { Plus, Edit, Trash2, GripVertical, Save, X, Clapperboard, Loader2 } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

export default function EpisodesPage() {
  const { currentProject, setCurrentProject, episodes, fetchEpisodes, createEpisode, updateEpisode, deleteEpisode, reorderEpisodes, isLoading } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingEpisode, setEditingEpisode] = useState<any>(null)
  const [formData, setFormData] = useState({
    episode_number: "1",
    title: "",
    synopsis: "",
    status: "planned",
    estimated_duration: "",
    notes: "",
  })
  const [dragIndex, setDragIndex] = useState<number | null>(null)

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  useEffect(() => {
    if (selectedProjectId) {
      setCurrentProject(projects.find(p => p.id === selectedProjectId) || null)
      fetchEpisodes(selectedProjectId)
    }
  }, [selectedProjectId, fetchEpisodes, setCurrentProject, projects])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProjectId) return

    try {
      const data = {
        ...formData,
        episode_number: parseInt(formData.episode_number),
        estimated_duration: formData.estimated_duration ? parseInt(formData.estimated_duration) : undefined,
      }

      if (editingEpisode) {
        await updateEpisode(selectedProjectId, editingEpisode.id, data)
      } else {
        await createEpisode(selectedProjectId, data)
      }
      setShowCreateModal(false)
      setEditingEpisode(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save episode:", error)
    }
  }

  const handleEdit = (episode: any) => {
    setEditingEpisode(episode)
    setFormData({
      episode_number: episode.episode_number,
      title: episode.title || "",
      synopsis: episode.synopsis || "",
      status: episode.status,
      estimated_duration: episode.estimated_duration?.toString() || "",
      notes: episode.notes || "",
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this episode?")) {
      try {
        await deleteEpisode(selectedProjectId, id)
      } catch (error) {
        console.error("Failed to delete episode:", error)
      }
    }
  }

  const resetForm = () => {
    const nextNumber = episodes.length > 0 ? Math.max(...episodes.map(e => e.episode_number)) + 1 : 1
    setFormData({
      episode_number: nextNumber.toString(),
      title: "",
      synopsis: "",
      status: "planned",
      estimated_duration: "",
      notes: "",
    })
  }

  const openCreateModal = () => {
    setEditingEpisode(null)
    resetForm()
    setShowCreateModal(true)
  }

  const handleDragStart = (index: number) => {
    setDragIndex(index)
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (dragIndex !== null && dragIndex !== index) {
      setDragIndex(index)
    }
  }

  const handleDragEnd = () => {
    if (dragIndex !== null) {
      const ids = episodes.map(e => e.id)
      reorderEpisodes(selectedProjectId, ids)
    }
    setDragIndex(null)
  }

  const statusOptions = [
    { value: "planned", label: "Planned" },
    { value: "writing", label: "Writing" },
    { value: "scenes_done", label: "Scenes Done" },
    { value: "prompts_ready", label: "Prompts Ready" },
    { value: "assets_generating", label: "Assets Generating" },
    { value: "assets_ready", label: "Assets Ready" },
    { value: "editing", label: "Editing" },
    { value: "completed", label: "Completed" },
  ]

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      planned: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
      writing: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
      scenes_done: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
      prompts_ready: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
      assets_generating: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
      assets_ready: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
      editing: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
      completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    }
    return colors[status] || colors.planned
  }

  if (!user) return null

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Episode Manager</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Manage your 20-episode series</p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-800 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.title}</option>
              ))}
            </select>
            <Button onClick={openCreateModal}>
              <Plus className="w-4 h-4" />
              Add Episode
            </Button>
          </div>
        </div>

        {selectedProjectId && (
          <Card>
            <CardHeader>
              <CardTitle>Episodes ({episodes.length})</CardTitle>
              <CardDescription>Drag to reorder. Target: 20 episodes for a full series.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-20 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                  ))}
                </div>
              ) : episodes.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                    <Clapperboard className="w-8 h-8 text-dark-400" />
                  </div>
                  <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No episodes yet</h3>
                  <p className="text-dark-500 dark:text-dark-400 mb-6">Create your first episode</p>
                  <Button onClick={openCreateModal}>
                    <Plus className="w-4 h-4" />
                    Add Episode
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {episodes.map((episode, index) => (
                    <div
                      key={episode.id}
                      draggable
                      onDragStart={() => handleDragStart(index)}
                      onDragOver={(e) => handleDragOver(e, index)}
                      onDragEnd={handleDragEnd}
                      className={clsx(
                        "flex items-center gap-4 p-4 rounded-lg border transition-colors",
                        dragIndex === index ? "bg-primary-50 dark:bg-primary-900/20 border-primary-300" : "border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-800/50"
                      )}
                    >
                      <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-600 dark:text-primary-400 flex-shrink-0 cursor-grab">
                        <GripVertical className="w-5 h-5" />
                      </div>

                      <div className="w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                        <span className="text-lg font-bold text-primary-700 dark:text-primary-300">
                          {episode.episode_number}
                        </span>
                      </div>

                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-dark-900 dark:text-white truncate">
                          {episode.title || `Episode ${episode.episode_number}`}
                        </h4>
                        {episode.synopsis && (
                          <p className="text-sm text-dark-500 dark:text-dark-400 truncate mt-1">
                            {episode.synopsis}
                          </p>
                        )}
                      </div>

                      <span className={clsx("text-xs font-medium px-2 py-1 rounded-full", getStatusColor(episode.status))}>
                        {episode.status.replace("_", " ")}
                      </span>

                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(episode)} className="p-1.5">
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(episode.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {!selectedProjectId && projects.length === 0 && (
          <Card variant="outlined">
            <CardContent className="p-12 text-center">
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No projects yet</h3>
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start adding episodes</p>
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
                  <CardTitle>{editingEpisode ? "Edit Episode" : "New Episode"}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Episode Number"
                    type="number"
                    value={formData.episode_number}
                    onChange={(e) => setFormData({ ...formData, episode_number: e.target.value })}
                    placeholder="1"
                    required
                    min={1}
                    max={100}
                  />
                  <Select
                    label="Status"
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    options={statusOptions}
                  />
                </div>
                <Input
                  label="Title"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Episode title"
                />
                <Textarea
                  label="Synopsis"
                  value={formData.synopsis}
                  onChange={(e) => setFormData({ ...formData, synopsis: e.target.value })}
                  placeholder="Brief summary of the episode..."
                  rows={3}
                />
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Estimated Duration (seconds)"
                    type="number"
                    value={formData.estimated_duration}
                    onChange={(e) => setFormData({ ...formData, estimated_duration: e.target.value })}
                    placeholder="300"
                    min={1}
                  />
                </div>
                <Textarea
                  label="Notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Production notes..."
                  rows={2}
                />
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    {editingEpisode ? "Update" : "Create"}
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