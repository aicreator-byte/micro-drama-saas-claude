"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Select } from "@/components/ui/Select"
import { Plus, Edit, Trash2, Save, X, Type, Loader2, Copy, Download, Sparkles } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

const PROMPT_TYPES = [
  { value: "character_image", label: "Character Image" },
  { value: "location_image", label: "Location Image" },
  { value: "scene_image", label: "Scene Image" },
  { value: "video_generation", label: "Video Generation" },
  { value: "camera_movement", label: "Camera Movement" },
  { value: "character_action", label: "Character Action" },
  { value: "dialogue_audio", label: "Dialogue Audio" },
  { value: "background_music", label: "Background Music" },
  { value: "sound_effect", label: "Sound Effect" },
  { value: "subtitle", label: "Subtitle" },
]

export default function PromptsPage() {
  const {
    prompts, fetchPrompts, createPrompt, updatePrompt, deletePrompt, generatePrompt,
    characters, fetchCharacters,
    locations, fetchLocations,
    episodes, fetchEpisodes,
    scenes, fetchScenes,
    isLoading
  } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string>("")
  const [selectedSceneId, setSelectedSceneId] = useState<string>("")
  const [promptTypeFilter, setPromptTypeFilter] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingPrompt, setEditingPrompt] = useState<any>(null)
  const [formData, setFormData] = useState({
    prompt_type: "character_image",
    prompt_text: "",
    negative_prompt: "",
    parameters: "",
    character_id: "",
    location_id: "",
    episode_id: "",
    scene_id: "",
  })
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  useEffect(() => {
    if (selectedProjectId) {
      fetchPrompts(selectedProjectId, { prompt_type: promptTypeFilter || undefined, episode_id: selectedEpisodeId || undefined, scene_id: selectedSceneId || undefined })
      fetchEpisodes(selectedProjectId)
      fetchCharacters(selectedProjectId)
      fetchLocations(selectedProjectId)
    }
  }, [selectedProjectId, promptTypeFilter, selectedEpisodeId, selectedSceneId, fetchPrompts, fetchEpisodes, fetchCharacters, fetchLocations])

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
        episode_id: formData.episode_id || undefined,
        scene_id: formData.scene_id || undefined,
        character_id: formData.character_id || undefined,
        location_id: formData.location_id || undefined,
      }

      if (editingPrompt) {
        await updatePrompt(selectedProjectId, editingPrompt.id, data)
      } else {
        await createPrompt(data)
      }
      setShowCreateModal(false)
      setEditingPrompt(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save prompt:", error)
    }
  }

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProjectId) return

    setGenerating(true)
    try {
      const data = {
        ...formData,
        project_id: selectedProjectId,
        episode_id: formData.episode_id || undefined,
        scene_id: formData.scene_id || undefined,
        character_id: formData.character_id || undefined,
        location_id: formData.location_id || undefined,
        context: formData.prompt_text,
      }
      await generatePrompt(data)
      setShowCreateModal(false)
      resetForm()
    } catch (error) {
      console.error("Failed to generate prompt:", error)
    } finally {
      setGenerating(false)
    }
  }

  const handleEdit = (prompt: any) => {
    setEditingPrompt(prompt)
    setFormData({
      prompt_type: prompt.prompt_type,
      prompt_text: prompt.prompt_text,
      negative_prompt: prompt.negative_prompt || "",
      parameters: prompt.parameters || "",
      character_id: prompt.character_id || "",
      location_id: prompt.location_id || "",
      episode_id: prompt.episode_id || "",
      scene_id: prompt.scene_id || "",
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this prompt?")) {
      try {
        await deletePrompt(selectedProjectId, id)
      } catch (error) {
        console.error("Failed to delete prompt:", error)
      }
    }
  }

  const resetForm = () => {
    setFormData({
      prompt_type: "character_image",
      prompt_text: "",
      negative_prompt: "",
      parameters: "",
      character_id: "",
      location_id: "",
      episode_id: "",
      scene_id: "",
    })
  }

  const openCreateModal = () => {
    setEditingPrompt(null)
    resetForm()
    setShowCreateModal(true)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const downloadPrompt = (prompt: any) => {
    const content = `Prompt Type: ${prompt.prompt_type}\n\nPrompt:\n${prompt.prompt_text}\n\n${prompt.negative_prompt ? `Negative Prompt:\n${prompt.negative_prompt}\n\n` : ""}${prompt.parameters ? `Parameters:\n${prompt.parameters}` : ""}`
    const blob = new Blob([content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `prompt-${prompt.prompt_type}-${prompt.id.slice(0, 8)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const getPromptTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      character_image: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
      location_image: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
      scene_image: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
      video_generation: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300",
      camera_movement: "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300",
      character_action: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300",
      dialogue_audio: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
      background_music: "bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300",
      sound_effect: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
      subtitle: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
    }
    return colors[type] || colors.character_image
  }

  if (!user) return null

  const filteredPrompts = prompts.filter(p =>
    !promptTypeFilter || p.prompt_type === promptTypeFilter
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Prompt Studio</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Create and manage AI prompts for images, video, audio</p>
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
                  value={promptTypeFilter}
                  onChange={(e) => setPromptTypeFilter(e.target.value)}
                  options={[{ value: "", label: "All Types" }, ...PROMPT_TYPES]}
                  className="w-48"
                />
                <Button onClick={openCreateModal}>
                  <Plus className="w-4 h-4" />
                  Add Prompt
                </Button>
              </>
            )}
          </div>
        </div>

        {selectedProjectId && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Prompts ({filteredPrompts.length})</CardTitle>
                  <CardDescription>Edit prompts, copy to clipboard, or download. Use AI generation for templates.</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" onClick={openCreateModal}>
                    <Plus className="w-4 h-4" />
                    Manual
                  </Button>
                  <Button onClick={openCreateModal} className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700">
                    <Sparkles className="w-4 h-4" />
                    AI Generate
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-24 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                  ))}
                </div>
              ) : filteredPrompts.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                    <Type className="w-8 h-8 text-dark-400" />
                  </div>
                  <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No prompts yet</h3>
                  <p className="text-dark-500 dark:text-dark-400 mb-6">Create prompts manually or use AI generation</p>
                  <div className="flex flex-wrap gap-2 justify-center">
                    <Button variant="outline" onClick={openCreateModal}>
                      <Plus className="w-4 h-4" />
                      Manual Entry
                    </Button>
                    <Button onClick={openCreateModal} className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700">
                      <Sparkles className="w-4 h-4" />
                      AI Generate
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredPrompts.map((prompt) => (
                    <div key={prompt.id} className="p-4 rounded-lg border border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={clsx("text-xs font-medium px-2 py-1 rounded-full", getPromptTypeColor(prompt.prompt_type))}>
                              {PROMPT_TYPES.find(t => t.value === prompt.prompt_type)?.label || prompt.prompt_type}
                            </span>
                            {prompt.character_id && (
                              <span className="text-xs px-2 py-1 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full">
                                Character: {prompt.character_id.slice(0, 8)}
                              </span>
                            )}
                            {prompt.location_id && (
                              <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-full">
                                Location: {prompt.location_id.slice(0, 8)}
                              </span>
                            )}
                            <span className="text-xs px-2 py-1 bg-dark-100 dark:bg-dark-800 text-dark-600 dark:text-dark-400 rounded-full">
                              {prompt.status}
                            </span>
                          </div>
                          <p className="text-dark-700 dark:text-dark-300 font-mono text-sm whitespace-pre-wrap break-words max-h-32 overflow-hidden">
                            {prompt.prompt_text}
                          </p>
                          {prompt.negative_prompt && (
                            <p className="text-dark-500 dark:text-dark-400 text-sm mt-1 line-clamp-1">
                              Negative: {prompt.negative_prompt}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <Button variant="ghost" size="sm" onClick={() => copyToClipboard(prompt.prompt_text)} className="p-1.5" title="Copy prompt">
                            <Copy className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => downloadPrompt(prompt)} className="p-1.5" title="Download">
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(prompt)} className="p-1.5">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(prompt.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
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
        )}

        {!selectedProjectId && projects.length === 0 && (
          <Card variant="outlined">
            <CardContent className="p-12 text-center">
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No projects yet</h3>
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start generating prompts</p>
              
<Button onClick={() => window.location.href = "/dashboard/projects"}>
                Create Project
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Create/Edit Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowCreateModal(false)}>
            <Card className="w-full max-w-3xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{editingPrompt ? "Edit Prompt" : "New Prompt"}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={editingPrompt ? handleSubmit : handleGenerate} className="p-6 space-y-4">
                <Select
                  label="Prompt Type"
                  value={formData.prompt_type}
                  onChange={(e) => setFormData({ ...formData, prompt_type: e.target.value })}
                  options={PROMPT_TYPES}
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

                <div className="grid grid-cols-2 gap-4">
                  <Select
                    label="Character (Optional)"
                    value={formData.character_id}
                    onChange={(e) => setFormData({ ...formData, character_id: e.target.value })}
                    options={[
                      { value: "", label: "None" },
                      ...characters.map(c => ({ value: c.id, label: c.name }))
                    ]}
                  />
                  <Select
                    label="Location (Optional)"
                    value={formData.location_id}
                    onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
                    options={[
                      { value: "", label: "None" },
                      ...locations.map(l => ({ value: l.id, label: l.name }))
                    ]}
                  />
                </div>

                <Textarea
                  label="Prompt Text"
                  value={formData.prompt_text}
                  onChange={(e) => setFormData({ ...formData, prompt_text: e.target.value })}
                  placeholder="Enter your prompt or describe what you want to generate..."
                  rows={4}
                  required
                />

                <Textarea
                  label="Negative Prompt (Optional)"
                  value={formData.negative_prompt}
                  onChange={(e) => setFormData({ ...formData, negative_prompt: e.target.value })}
                  placeholder="What to avoid in generation..."
                  rows={2}
                />

                <Textarea
                  label="Parameters (JSON, Optional)"
                  value={formData.parameters}
                  onChange={(e) => setFormData({ ...formData, parameters: e.target.value })}
                  placeholder='{"model": "gpt-4o", "steps": 30, "cfg": 7.5}'
                  rows={2}
                />

                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  {editingPrompt ? (
                    <Button type="submit" loading={isLoading}>
                      <Save className="w-4 h-4" />
                      Update
                    </Button>
                  ) : (
                    <Button type="submit" loading={generating} className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700">
                      <Sparkles className="w-4 h-4" />
                      {generating ? "Generating..." : "Generate with AI"}
                    </Button>
                  )}
                </div>
              </form>
            </Card>
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}