"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Select } from "@/components/ui/Select"
import { Plus, Edit, Trash2, GripVertical, Loader2, Save, X } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

export default function CharactersPage() {
  const { currentProject, setCurrentProject, characters, fetchCharacters, createCharacter, updateCharacter, deleteCharacter, reorderCharacters, isLoading } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingCharacter, setEditingCharacter] = useState<any>(null)
  const [formData, setFormData] = useState({
    name: "",
    role: "",
    physical_appearance: "",
    personality: "",
    background: "",
    costume: "",
    reference_images: "",
    consistency_instructions: "",
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
      fetchCharacters(selectedProjectId)
    }
  }, [selectedProjectId, fetchCharacters, setCurrentProject, projects])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProjectId) return

    try {
      if (editingCharacter) {
        await updateCharacter(selectedProjectId, editingCharacter.id, formData)
      } else {
        await createCharacter(selectedProjectId, formData)
      }
      setShowCreateModal(false)
      setEditingCharacter(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save character:", error)
    }
  }

  const handleEdit = (character: any) => {
    setEditingCharacter(character)
    setFormData({
      name: character.name,
      role: character.role || "",
      physical_appearance: character.physical_appearance || "",
      personality: character.personality || "",
      background: character.background || "",
      costume: character.costume || "",
      reference_images: character.reference_images || "",
      consistency_instructions: character.consistency_instructions || "",
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this character?")) {
      try {
        await deleteCharacter(selectedProjectId, id)
      } catch (error) {
        console.error("Failed to delete character:", error)
      }
    }
  }

  const resetForm = () => {
    setFormData({
      name: "",
      role: "",
      physical_appearance: "",
      personality: "",
      background: "",
      costume: "",
      reference_images: "",
      consistency_instructions: "",
    })
  }

  const openCreateModal = () => {
    setEditingCharacter(null)
    resetForm()
    setShowCreateModal(true)
  }

  const handleDragStart = (index: number) => {
    setDragIndex(index)
  }

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault()
    if (dragIndex !== null && dragIndex !== index) {
      const newCharacters = [...characters]
      const [removed] = newCharacters.splice(dragIndex, 1)
      newCharacters.splice(index, 0, removed)
      // Update display_order locally for visual feedback
      setDragIndex(index)
    }
  }

  const handleDragEnd = () => {
    if (dragIndex !== null) {
      const ids = characters.map(c => c.id)
      reorderCharacters(selectedProjectId, ids)
    }
    setDragIndex(null)
  }

  if (!user) return null

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Character Studio</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Create and manage character profiles</p>
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
              Add Character
            </Button>
          </div>
        </div>

        {selectedProjectId && (
          <Card>
            <CardHeader>
              <CardTitle>Characters ({characters.length})</CardTitle>
              <CardDescription>Drag to reorder. Support for 6+ characters per project.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-20 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                  ))}
                </div>
              ) : characters.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                    <Plus className="w-8 h-8 text-dark-400" />
                  </div>
                  <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No characters yet</h3>
                  <p className="text-dark-500 dark:text-dark-400 mb-6">Create your first character profile</p>
                  <Button onClick={openCreateModal}>
                    <Plus className="w-4 h-4" />
                    Add Character
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {characters.map((character, index) => (
                    <div
                      key={character.id}
                      draggable
                      onDragStart={() => handleDragStart(index)}
                      onDragOver={(e) => handleDragOver(e, index)}
                      onDragEnd={handleDragEnd}
                      className={clsx(
                        "flex items-center gap-4 p-4 rounded-lg border transition-colors",
                        dragIndex === index ? "bg-primary-50 dark:bg-primary-900/20 border-primary-300" : "border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-800/50"
                      )}
                    >
                      <div className="w-10 h-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center text-purple-600 dark:text-purple-400 flex-shrink-0 cursor-grab">
                        <GripVertical className="w-5 h-5" />
                      </div>

                      <div className="w-12 h-12 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
                        <span className="text-lg font-bold text-purple-700 dark:text-purple-300">
                          {character.name.charAt(0).toUpperCase()}
                        </span>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-dark-900 dark:text-white truncate">{character.name}</h4>
                          {character.role && (
                            <span className="text-xs px-2 py-1 bg-dark-100 dark:bg-dark-800 rounded text-dark-600 dark:text-dark-400">
                              {character.role}
                            </span>
                          )}
                        </div>
                        {character.physical_appearance && (
                          <p className="text-sm text-dark-500 dark:text-dark-400 truncate mt-1">
                            {character.physical_appearance}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(character)} className="p-1.5">
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(character.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
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
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start adding characters</p>
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
                  <CardTitle>{editingCharacter ? "Edit Character" : "New Character"}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <Input
                  label="Name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Character name"
                  required
                />
                <Select
                  label="Role"
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                  options={[
                    { value: "", label: "Select Role" },
                    { value: "protagonist", label: "Protagonist" },
                    { value: "antagonist", label: "Antagonist" },
                    { value: "supporting", label: "Supporting" },
                    { value: "cameo", label: "Cameo" },
                  ]}
                />
                <Textarea
                  label="Physical Appearance"
                  value={formData.physical_appearance}
                  onChange={(e) => setFormData({ ...formData, physical_appearance: e.target.value })}
                  placeholder="Height, build, hair, eyes, distinguishing features..."
                  rows={3}
                />
                <Textarea
                  label="Personality"
                  value={formData.personality}
                  onChange={(e) => setFormData({ ...formData, personality: e.target.value })}
                  placeholder="Traits, quirks, motivations, fears..."
                  rows={3}
                />
                <Textarea
                  label="Background"
                  value={formData.background}
                  onChange={(e) => setFormData({ ...formData, background: e.target.value })}
                  placeholder="History, upbringing, key life events..."
                  rows={3}
                />
                <Textarea
                  label="Costume"
                  value={formData.costume}
                  onChange={(e) => setFormData({ ...formData, costume: e.target.value })}
                  placeholder="Typical clothing, accessories, style..."
                  rows={2}
                />
                <Textarea
                  label="Reference Images (JSON array of URLs)"
                  value={formData.reference_images}
                  onChange={(e) => setFormData({ ...formData, reference_images: e.target.value })}
                  placeholder='["https://example.com/ref1.jpg", "https://example.com/ref2.jpg"]'
                  rows={2}
                />
                <Textarea
                  label="Consistency Instructions"
                  value={formData.consistency_instructions}
                  onChange={(e) => setFormData({ ...formData, consistency_instructions: e.target.value })}
                  placeholder="Guidelines for maintaining visual consistency across generations..."
                  rows={2}
                />
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    {editingCharacter ? "Update" : "Create"}
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