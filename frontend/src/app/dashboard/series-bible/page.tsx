"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { useAuthStore } from "@/lib/auth-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Save, Edit, Loader2 } from "lucide-react"
import { clsx } from "clsx"

export default function SeriesBiblePage() {
  const { currentProject, setCurrentProject, seriesBible, fetchSeriesBible, createSeriesBible, updateSeriesBible, isLoading } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [formData, setFormData] = useState({
    premise: "",
    main_plot: "",
    subplots: "",
    character_relationships: "",
    world_settings: "",
    tone_and_style: "",
    visual_style: "",
    ending_direction: "",
    episode_structure: "",
  })
  const [editing, setEditing] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  useEffect(() => {
    if (selectedProjectId) {
      setCurrentProject(projects.find(p => p.id === selectedProjectId) || null)
      fetchSeriesBible(selectedProjectId)
    }
  }, [selectedProjectId, fetchSeriesBible, setCurrentProject, projects])

  useEffect(() => {
    if (seriesBible) {
      setFormData({
        premise: seriesBible.premise || "",
        main_plot: seriesBible.main_plot || "",
        subplots: seriesBible.subplots || "",
        character_relationships: seriesBible.character_relationships || "",
        world_settings: seriesBible.world_settings || "",
        tone_and_style: seriesBible.tone_and_style || "",
        visual_style: seriesBible.visual_style || "",
        ending_direction: seriesBible.ending_direction || "",
        episode_structure: seriesBible.episode_structure || "",
      })
      setEditing(false)
    }
  }, [seriesBible])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProjectId) return

    try {
      if (seriesBible) {
        await updateSeriesBible(selectedProjectId, formData)
      } else {
        await createSeriesBible(selectedProjectId, formData)
      }
      setEditing(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (error) {
      console.error("Failed to save series bible:", error)
    }
  }

  const fields = [
    { key: "premise", label: "Story Premise", placeholder: "One-sentence logline of your story...", rows: 2 },
    { key: "main_plot", label: "Main Plot", placeholder: "Describe the main storyline...", rows: 4 },
    { key: "subplots", label: "Subplots", placeholder: "Secondary storylines (JSON array or text)...", rows: 3 },
    { key: "character_relationships", label: "Character Relationships", placeholder: "Describe relationships between characters...", rows: 3 },
    { key: "world_settings", label: "World Settings", placeholder: "Setting, time period, rules of the world...", rows: 3 },
    { key: "tone_and_style", label: "Tone & Style", placeholder: "Dark, comedic, romantic, gritty, whimsical...", rows: 2 },
    { key: "visual_style", label: "Visual Style", placeholder: "Cinematography, color palette, aesthetic...", rows: 2 },
    { key: "ending_direction", label: "Ending Direction", placeholder: "How does the series conclude?...", rows: 2 },
    { key: "episode_structure", label: "Episode Structure", placeholder: "Act structure, episode format (JSON)...", rows: 3 },
  ]

  if (!user) return null

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Series Bible</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Define the foundation of your micro drama series</p>
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
          </div>
        </div>

        {selectedProjectId && (
          <Card>
            <CardHeader>
              <CardTitle>Series Bible</CardTitle>
              <CardDescription>All fields are optional. Fill in what you have and expand as your story develops.</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {fields.map((field) => (
                  <Textarea
                    key={field.key}
                    label={field.label}
                    value={formData[field.key as keyof typeof formData]}
                    onChange={(e) => setFormData({ ...formData, [field.key]: e.target.value })}
                    placeholder={field.placeholder}
                    rows={field.rows}
                    disabled={!editing}
                  />
                ))}

                <div className="flex justify-end gap-3 pt-4 border-t border-dark-200 dark:border-dark-700">
                  {!editing ? (
                    <Button type="button" onClick={() => setEditing(true)}>
                      <Edit className="w-4 h-4" />
                      Edit
                    </Button>
                  ) : (
                    <>
                      <Button type="button" variant="outline" onClick={() => setEditing(false)}>
                        Cancel
                      </Button>
                      <Button type="submit" loading={isLoading}>
                        <Save className="w-4 h-4" />
                        {saved ? "Saved!" : "Save Changes"}
                      </Button>
                    </>
                  )}
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {!selectedProjectId && projects.length === 0 && (
          <Card variant="outlined">
            <CardContent className="p-12 text-center">
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No projects yet</h3>
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start building your Series Bible</p>
              <Button onClick={() => window.location.href = "/dashboard/projects"}>
                Create Project
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}