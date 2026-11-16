"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Select } from "@/components/ui/Select"
import { Plus, Edit, Trash2, GripVertical, Save, X, Type, Loader2, Mic } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

export default function DialoguesPage() {
  const {
    dialogues, fetchDialogues, createDialogue, updateDialogue, deleteDialogue, reorderDialogues,
    characters, fetchCharacters,
    scenes, fetchScenes,
    episodes, fetchEpisodes,
    isLoading
  } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string>("")
  const [selectedSceneId, setSelectedSceneId] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingDialogue, setEditingDialogue] = useState<any>(null)
  const [formData, setFormData] = useState({
    character_id: "",
    order_index: "0",
    dialogue_text: "",
    parenthetical: "",
    audio_prompt: "",
  })
  const [dragIndex, setDragIndex] = useState<number | null>(null)

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  useEffect(() => {
    if (selectedProjectId) {
      fetchEpisodes(selectedProjectId)
      fetchCharacters(selectedProjectId)
    }
  }, [selectedProjectId, fetchEpisodes, fetchCharacters])

  useEffect(() => {
    if (selectedEpisodeId) {
      fetchScenes(selectedEpisodeId)
    }
  }, [selectedEpisodeId, fetchScenes])

  useEffect(() => {
    if (selectedSceneId) {
      fetchDialogues(selectedSceneId)
    }
  }, [selectedSceneId, fetchDialogues])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedSceneId) return

    try {
      const data = {
        ...formData,
        order_index: parseInt(formData.order_index),
      }

      if (editingDialogue) {
        await updateDialogue(selectedSceneId, editingDialogue.id, data)
      } else {
        await createDialogue(selectedSceneId, data)
      }
      setShowCreateModal(false)
      setEditingDialogue(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save dialogue:", error)
    }
  }

  const handleEdit = (dialogue: any) => {
    setEditingDialogue(dialogue)
    setFormData({
      character_id: dialogue.character_id,
      order_index: dialogue.order_index,
      dialogue_text: dialogue.dialogue_text,
      parenthetical: dialogue.parenthetical || "",
      audio_prompt: dialogue.audio_prompt || "",
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this dialogue line?")) {
      try {
        await deleteDialogue(selectedSceneId, id)
      } catch (error) {
        console.error("Failed to delete dialogue:", error)
      }
    }
  }

  const resetForm = () => {
    const nextIndex = dialogues.length
    setFormData({
      character_id: "",
      order_index: nextIndex.toString(),
      dialogue_text: "",
      parenthetical: "",
      audio_prompt: "",
    })
  }

  const openCreateModal = () => {
    setEditingDialogue(null)
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
      const ids = dialogues.map(d => d.id)
      reorderDialogues(selectedSceneId, ids)
    }
    setDragIndex(null)
  }

  if (!user) return null

  const selectedScene = scenes.find(s => s.id === selectedSceneId)
  const selectedEpisode = episodes.find(e => e.id === selectedEpisodeId)

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Dialogues</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Write and organize dialogue lines for each scene</p>
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
              <select
                value={selectedEpisodeId}
                onChange={(e) => {
                  setSelectedEpisodeId(e.target.value)
                  setSelectedSceneId("")
                }}
                className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-800 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Select Episode</option>
                {episodes.map((ep) => (
                  <option key={ep.id} value={ep.id}>Ep {ep.episode_number}: {ep.title || "Untitled"}</option>
                ))}
              </select>
            )}

            {selectedEpisodeId && (
              <select
                value={selectedSceneId}
                onChange={(e) => setSelectedSceneId(e.target.value)}
                className="px-3 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-800 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Select Scene</option>
                {scenes.map((s) => (
                  <option key={s.id} value={s.id}>Scene {s.scene_number}: {s.title || "Untitled"}</option>
                ))}
              </select>
            )}

            {selectedSceneId && (
              <Button onClick={openCreateModal}>
                <Plus className="w-4 h-4" />
                Add Dialogue
              </Button>
            )}
          </div>
        </div>

        {selectedProjectId && !selectedEpisodeId && (
          <Card variant="outlined">
            <CardContent className="p-8 text-center">
              <Type className="w-12 h-12 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">Select an Episode</h3>
              <p className="text-dark-500 dark:text-dark-400">Choose an episode and scene from the dropdowns above</p>
            </CardContent>
          </Card>
        )}

        {selectedEpisodeId && !selectedSceneId && (
          <Card variant="outlined">
            <CardContent className="p-8 text-center">
              <Type className="w-12 h-12 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">Select a Scene</h3>
              <p className="text-dark-500 dark:text-dark-400">Choose a scene to manage its dialogues</p>
            </CardContent>
          </Card>
        )}

        {selectedSceneId && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>
                    Dialogues - {selectedScene?.title || `Scene ${selectedScene?.scene_number}`}
                    {selectedEpisode && <span className="text-sm font-normal text-dark-500 dark:text-dark-400 ml-2">(Ep {selectedEpisode.episode_number})</span>}
                  </CardTitle>
                  <CardDescription>Drag to reorder. Add character names, parentheticals, and audio prompts for TTS.</CardDescription>
                </div>
                <Button onClick={openCreateModal}>
                  <Plus className="w-4 h-4" />
                  Add Dialogue
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
              ) : dialogues.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                    <Type className="w-8 h-8 text-dark-400" />
                  </div>
                  <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No dialogue lines yet</h3>
                  <p className="text-dark-500 dark:text-dark-400 mb-6">Write your first line of dialogue</p>
                  <Button onClick={openCreateModal}>
                    <Plus className="w-4 h-4" />
                    Add Dialogue
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  {dialogues.map((dialogue, index) => (
                    <div
                      key={dialogue.id}
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
                        <div className="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center text-primary-600 dark:text-primary-400 flex-shrink-0 cursor-grab mt-1">
                          <GripVertical className="w-4 h-4" />
                        </div>

                        <div className="w-8 h-8 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0 mt-1">
                          <span className="text-sm font-bold text-purple-700 dark:text-purple-300">
                            {dialogue.order_index + 1}
                          </span>
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            {dialogue.character && (
                              <span className="font-medium text-dark-900 dark:text-white">
                                {dialogue.character.name}:
                              </span>
                            )}
                            {dialogue.parenthetical && (
                              <span className="text-sm text-dark-500 dark:text-dark-400 italic">
                                ({dialogue.parenthetical})
                              </span>
                            )}
                          </div>
                          <p className="text-dark-700 dark:text-dark-300">
                            {dialogue.dialogue_text}
                          </p>
                          {dialogue.audio_prompt && (
                            <div className="flex items-center gap-1 mt-1 text-xs text-dark-500 dark:text-dark-400">
                              <Mic className="w-3 h-3" />
                              <span>TTS: {dialogue.audio_prompt}</span>
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(dialogue)} className="p-1.5">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(dialogue.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
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
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start writing dialogues</p>
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
                  <CardTitle>{editingDialogue ? "Edit Dialogue" : "New Dialogue Line"}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <Select
                  label="Character"
                  value={formData.character_id}
                  onChange={(e) => setFormData({ ...formData, character_id: e.target.value })}
                  options={[
                    { value: "", label: "Select Character" },
                    ...characters.map(c => ({ value: c.id, label: c.name }))
                  ]}
                  required
                />
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Order Index"
                    type="number"
                    value={formData.order_index}
                    onChange={(e) => setFormData({ ...formData, order_index: e.target.value })}
                    placeholder="0"
                    required
                    min={0}
                  />
                </div>
                <Textarea
                  label="Dialogue Text"
                  value={formData.dialogue_text}
                  onChange={(e) => setFormData({ ...formData, dialogue_text: e.target.value })}
                  placeholder="What the character says..."
                  rows={3}
                  required
                />
                <Input
                  label="Parenthetical (Optional)"
                  value={formData.parenthetical}
                  onChange={(e) => setFormData({ ...formData, parenthetical: e.target.value })}
                  placeholder="(whispering), (angry), (laughing)..."
                />
                <Input
                  label="Audio Prompt (Optional)"
                  value={formData.audio_prompt}
                  onChange={(e) => setFormData({ ...formData, audio_prompt: e.target.value })}
                  placeholder="Voice style instructions for TTS..."
                />
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    {editingDialogue ? "Update" : "Create"}
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