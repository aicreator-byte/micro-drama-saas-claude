"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Select } from "@/components/ui/Select"
import { Plus, Edit, Trash2, GripVertical, Save, X, MapPin } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

export default function LocationsPage() {
  const { currentProject, setCurrentProject, locations, fetchLocations, createLocation, updateLocation, deleteLocation, reorderLocations, isLoading } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingLocation, setEditingLocation] = useState<any>(null)
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    environment: "",
    visual_references: "",
    lighting: "",
    atmosphere: "",
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
      fetchLocations(selectedProjectId)
    }
  }, [selectedProjectId, fetchLocations, setCurrentProject, projects])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProjectId) return

    try {
      if (editingLocation) {
        await updateLocation(selectedProjectId, editingLocation.id, formData)
      } else {
        await createLocation(selectedProjectId, formData)
      }
      setShowCreateModal(false)
      setEditingLocation(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save location:", error)
    }
  }

  const handleEdit = (location: any) => {
    setEditingLocation(location)
    setFormData({
      name: location.name,
      description: location.description || "",
      environment: location.environment || "",
      visual_references: location.visual_references || "",
      lighting: location.lighting || "",
      atmosphere: location.atmosphere || "",
      consistency_instructions: location.consistency_instructions || "",
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this location?")) {
      try {
        await deleteLocation(selectedProjectId, id)
      } catch (error) {
        console.error("Failed to delete location:", error)
      }
    }
  }

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      environment: "",
      visual_references: "",
      lighting: "",
      atmosphere: "",
      consistency_instructions: "",
    })
  }

  const openCreateModal = () => {
    setEditingLocation(null)
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
      const ids = locations.map(l => l.id)
      reorderLocations(selectedProjectId, ids)
    }
    setDragIndex(null)
  }

  if (!user) return null

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Location Studio</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Create and manage location profiles</p>
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
              Add Location
            </Button>
          </div>
        </div>

        {selectedProjectId && (
          <Card>
            <CardHeader>
              <CardTitle>Locations ({locations.length})</CardTitle>
              <CardDescription>Drag to reorder. Define environments, lighting, and atmosphere.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-20 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                  ))}
                </div>
              ) : locations.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                    <MapPin className="w-8 h-8 text-dark-400" />
                  </div>
                  <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No locations yet</h3>
                  <p className="text-dark-500 dark:text-dark-400 mb-6">Create your first location profile</p>
                  <Button onClick={openCreateModal}>
                    <Plus className="w-4 h-4" />
                    Add Location
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {locations.map((location, index) => (
                    <div
                      key={location.id}
                      draggable
                      onDragStart={() => handleDragStart(index)}
                      onDragOver={(e) => handleDragOver(e, index)}
                      onDragEnd={handleDragEnd}
                      className={clsx(
                        "flex items-center gap-4 p-4 rounded-lg border transition-colors",
                        dragIndex === index ? "bg-primary-50 dark:bg-primary-900/20 border-primary-300" : "border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-800/50"
                      )}
                    >
                      <div className="w-10 h-10 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center text-green-600 dark:text-green-400 flex-shrink-0 cursor-grab">
                        <GripVertical className="w-5 h-5" />
                      </div>

                      <div className="w-12 h-12 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0">
                        <MapPin className="w-6 h-6 text-green-700 dark:text-green-300" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-dark-900 dark:text-white truncate">{location.name}</h4>
                        {location.environment && (
                          <p className="text-sm text-dark-500 dark:text-dark-400 truncate mt-1">
                            {location.environment}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEdit(location)} className="p-1.5">
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDelete(location.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
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
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start adding locations</p>
              
<Button onClick={() => window.location.href = "/dashboard/projects"}>
                Create Project
              </Button>
            </CardContent>
          </Card>
        )}

        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowCreateModal(false)}>
            <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{editingLocation ? "Edit Location" : "New Location"}</CardTitle>
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
                  placeholder="Location name"
                  required
                />
                <Textarea
                  label="Description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="General description of the location..."
                  rows={2}
                />
                <Textarea
                  label="Environment"
                  value={formData.environment}
                  onChange={(e) => setFormData({ ...formData, environment: e.target.value })}
                  placeholder="Indoor/outdoor, urban/rural, specific setting details..."
                  rows={2}
                />
                <Textarea
                  label="Visual References (JSON array of URLs)"
                  value={formData.visual_references}
                  onChange={(e) => setFormData({ ...formData, visual_references: e.target.value })}
                  placeholder='["https://example.com/ref1.jpg", "https://example.com/ref2.jpg"]'
                  rows={2}
                />
                <Textarea
                  label="Lighting"
                  value={formData.lighting}
                  onChange={(e) => setFormData({ ...formData, lighting: e.target.value })}
                  placeholder="Natural, artificial, mood lighting, time of day..."
                  rows={2}
                />
                <Textarea
                  label="Atmosphere"
                  value={formData.atmosphere}
                  onChange={(e) => setFormData({ ...formData, atmosphere: e.target.value })}
                  placeholder="Mood, weather, ambiance, sensory details..."
                  rows={2}
                />
                <Textarea
                  label="Consistency Instructions"
                  value={formData.consistency_instructions}
                  onChange={(e) => setFormData({ ...formData, consistency_instructions: e.target.value })}
                  placeholder="Guidelines for maintaining visual consistency..."
                  rows={2}
                />
                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    {editingLocation ? "Update" : "Create"}
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