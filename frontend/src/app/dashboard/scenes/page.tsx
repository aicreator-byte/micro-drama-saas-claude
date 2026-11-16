"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Select } from "@/components/ui/Select"
import { Plus, Edit, Trash2, GripVertical, Save, X, Film, Loader2, Users } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

export default function ScenesPage() {
  const {
    currentProject, setCurrentProject,
    scenes, fetchScenes, createScene, updateScene, deleteScene, reorderScenes,
    addCharacterToScene, removeCharacterFromScene,
    characters, fetchCharacters,
    episodes, fetchEpisodes,
    isLoading
  } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingScene, setEditingScene] = useState<any>(null)
  const [formData, setFormData] = useState({
    scene_number: "1",
    title: "",
    description: "",
    action: "",
    camera_directions: "",
    status: "planned",
    location_id: "",
    estimated_duration: "",
    characters: [] as string[],
  })
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [addingCharacterSceneId, setAddingCharacterSceneId] = useState<string | null>(null)

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  useEffect(() => {
    if (selectedProjectId) {
      setCurrentProject(projects.find(p => p.id === selectedProjectId) || null)
      fetchEpisodes(selectedProjectId)
      fetchCharacters(selectedProjectId)
    }
  }, [selectedProjectId, fetchEpisodes, fetchCharacters, setCurrentProject, projects])

  useEffect(() => {
    if (selectedEpisodeId) {
      fetchScenes(selectedEpisodeId)
    }
  }, [selectedEpisodeId, fetchScenes])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedEpisodeId) return

    try {
      const data = {
        ...formData,
        scene_number: parseInt(formData.scene_number),
        estimated_duration: formData.estimated_duration ? parseInt(formData.estimated_duration) : undefined,
        location_id: formData.location_id || undefined,
      }

      if (editingScene) {
        await updateScene(selectedEpisodeId, editingScene.id, data)
      } else {
        await createScene(selectedEpisodeId, data)
      }
      setShowCreateModal(false)
      setEditingScene(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save scene:", error)
    }
  }

  const handleEdit = (scene: any) => {
    setEditingScene(scene)
    setFormData({
      scene_number: scene.scene_number,
      title: scene.title || "",
      description: scene.description || "",
      action: scene.action || "",
      camera_directions: scene.camera_directions || "",
      status: scene.status,
      location_id: scene.location_id || "",
      estimated_duration: scene.estimated_duration?.toString() || "",
      characters: scene.characters?.map((c: any) => c.character_id) || [],
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this scene?")) {
      try {
        await deleteScene(selectedEpisodeId, id)
      } catch (error) {
        console.error("Failed to delete scene:", error)
      }
    }
  }

  const resetForm = () => {
    const nextNumber = scenes.length > 0 ? Math.max(...scenes.map(s => s.scene_number)) + 1 : 1
    setFormData({
      scene_number: nextNumber.toString(),
      title: "",
      description: "",
      action: "",
      camera_directions: "",
      status: "planned",
      location_id: "",
      estimated_duration: "",
      characters: [],
    })
  }

  const openCreateModal = () => {
    setEditingScene(null)
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
      const ids = scenes.map(s => s.id)
      reorderScenes(selectedEpisodeId, ids)
    }
    setDragIndex(null)
  }

  const handleAddCharacter = async (sceneId: string, characterId: string) => {
    try {
      await addCharacterToScene(selectedEpisodeId, sceneId, { character_id: characterId })
      setAddingCharacterSceneId(null)
    } catch (error) {
      console.error("Failed to add character:", error)
    }
  }

  const handleRemoveCharacter = async (sceneId: string, characterId: string) => {
    try {
      await removeCharacterFromScene(selectedEpisodeId, sceneId, characterId)
    } catch (error) {
      console.error("Failed to remove character:", error)
    }
  }

  const statusOptions = [
    { value: "planned", label: "Planned" },
    { value: "writing", label: "Writing" },
    { value: "prompts_ready", label: "Prompts Ready" },
    { value: "assets_generating", label: "Assets Generating" },
    { value: "assets_ready", label: "Assets Ready" },
    { value: "completed", label: "Completed" },
  ]

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      planned: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
      writing: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
      prompts_ready: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
      assets_generating: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
      assets_ready: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
      completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
    }
    return colors[status] || colors.planned
  }

  if (!user) return null

  const selectedEpisode = episodes.find(e => e.id === selectedEpisodeId)

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Scene Engine</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Break down episodes into scenes</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={selectedProjectId}
              onChange={(e) => {
                setSelectedProjectId(e.target.value)
                setSelectedEpisodeId("")
              }}
              className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-800 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.title}</option>
              ))}
            </select>

            {selectedProjectId && (
              <select
                value={selectedEpisodeId}
                onChange={(e) => setSelectedEpisodeId(e.target.value)}
                className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-800 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Select Episode</option>
                {episodes.map((ep) => (
                  <option key={ep.id} value={ep.id}>Ep {ep.episode_number}: {ep.title || "Untitled"}</option>
                ))}
              </select>
            )}

            {selectedEpisodeId && (
              <Button onClick={openCreateModal}>
                <Plus className="w-4 h-4" />
                Add Scene
              </Button>
            )}
          </div>
        </div>

        {selectedProjectId && !selectedEpisodeId && (
          <Card variant="outlined">
            <CardContent className="p-8 text-center">
              <Film className="w-12 h-12 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">Select an Episode</h3>
              <p className="text-dark-500 dark:text-dark-400">Choose an episode from the dropdown above to manage its scenes</p>
            </CardContent>
          </Card>
        )}

        {selectedEpisodeId && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Scenes - Episode {selectedEpisode?.episode_number} ({scenes.length})</CardTitle>
                  <CardDescription>Drag to reorder. Add characters, actions, and camera directions.</CardDescription>
                </div>
                <Button onClick={openCreateModal}>
                  <Plus className="w-4 h-4" />
                  Add Scene
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-20 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                  ))}
                </div>
              ) : scenes.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                    <Film className="w-8 h-8 text-dark-400" />
                  </div>
                  <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No scenes yet</h3>
                  <p className="text-dark-500 dark:text-dark-400 mb-6">Create your first scene</p>
                  <Button onClick={openCreateModal}>
                    <Plus className="w-4 h-4" />
                    Add Scene
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {scenes.map((scene, index) => (
                    <div
                      key={scene.id}
                      draggable
                      onDragStart={() => handleDragStart(index)}
                      onDragOver={(e) => handleDragOver(e, index)}
                      onDragEnd={handleDragEnd}
                      className={clsx(
                        "p-4 rounded-lg border transition-colors",
                        dragIndex === index ? "bg-primary-50 dark:bg-primary-900/20 border-primary-300" : "border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-800/50"
                      )}
                    >
                      <div className="flex items-start gap-4">
                        <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-600 dark:text-primary-400 flex-shrink-0 cursor-grab mt-1">
                          <GripVertical className="w-5 h-5" />
                        </div>

                        <div className="w-10 h-10 rounded-full bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0 mt-1">
                          <span className="text-lg font-bold text-primary-700 dark:text-primary-300">
                            {scene.scene_number}
                          </span>
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h4 className="font-medium text-dark-900 dark:text-white truncate">
                              {scene.title || `Scene ${scene.scene_number}`}
                            </h4>
                            <span className={clsx("text-xs font-medium px-2 py-1 rounded-full", getStatusColor(scene.status))}>
                              {scene.status.replace("_", " ")}
                            </span>
                          </div>

                          {scene.description && (
                            <p className="text-sm text-dark-500 dark:text-dark-400 mb-2">
                              {scene.description}
                            </p>
                          )}

                          {scene.action && (
                            <p className="text-sm text-dark-600 dark:text-dark-300 mb-2 italic">
                              Action: {scene.action}
                            </p>
                          )}

                          {scene.characters && scene.characters.length > 0 && (
                            <div className="flex items-center gap-2 flex-wrap mb-2">
                              <Users className="w-4 h-4 text-dark-400" />
                              <span className="text-sm text-dark-500 dark:text-dark-400">
                                Characters: {scene.characters.map((c: any) => c.character?.name || "Unknown").join(", ")}
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="flex flex-col items-end gap-1">
                          <div className="flex items-center gap-1">
                            <Button variant="ghost" size="sm" onClick={() => handleEdit(scene)} className="p-1.5">
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(scene.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>

                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setAddingCharacterSceneId(scene.id)}
                            className="text-xs px-2 py-1"
                          >
                            <Users className="w-3 h-3 mr-1" />
                            Add Character
                          </Button>
                        </div>
                      </div>

                      {addingCharacterSceneId === scene.id && (
                        <div className="mt-3 p-3 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-medium text-dark-900 dark:text-white">Add Character to Scene</span>
                            <Button variant="ghost" size="sm" onClick={() => setAddingCharacterSceneId(null)} className="p-1">
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {characters
                              .filter(c => !scene.characters?.some((sc: any) => sc.character_id === c.id))
                              .map((character) => (
                                <Button
                                  key={character.id}
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleAddCharacter(scene.id, character.id)}
                                  className="gap-1"
                                >
                                  {character.name}
                                </Button>
                              ))}
                            {characters
                              .filter(c => scene.characters?.some((sc: any) => sc.character_id === c.id))
                              .length === characters.length && (
                                <span className="text-sm text-dark-500 dark:text-dark-400">All characters added</span>
                              )}
                          </div>
                        </div>
                      )}
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
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start adding scenes</p>
              
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
                  <CardTitle>{editingScene ? "Edit Scene" : "New Scene"}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Scene Number"
                    type="number"
                    value={formData.scene_number}
                    onChange={(e) => setFormData({ ...formData, scene_number: e.target.value })}
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
                  placeholder="Scene title"
                />
                <Textarea
                  label="Description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="What happens in this scene..."
                  rows={3}
                />
                <Textarea
                  label="Action"
                  value={formData.action}
                  onChange={(e) => setFormData({ ...formData, action: e.target.value })}
                  placeholder="Character movements, blocking, physical actions..."
                  rows={3}
                />
                <Textarea
                  label="Camera Directions"
                  value={formData.camera_directions}
                  onChange={(e) => setFormData({ ...formData, camera_directions: e.target.value })}
                  placeholder="Camera angles, movements, shot types..."
                  rows={2}
                />
                <Select
                  label="Location"
                  value={formData.location_id}
                  onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
                  options={[
                    { value: "", label: "No location selected" },
                    // Locations would need to be fetched - for now using project store
                  ]}
                />
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Estimated Duration (seconds)"
                    type="number"
                    value={formData.estimated_duration}
                    onChange={(e) => setFormData({ ...formData, estimated_duration: e.target.value })}
                    placeholder="60"
                    min={1}
                  />
                </div>
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    {editingScene ? "Update" : "Create"}
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