"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Select } from "@/components/ui/Select"
import { Textarea } from "@/components/ui/Textarea"
import { Plus, Search, Edit, Trash2, MoreVertical, Loader2, Sparkles } from "lucide-react"
import { clsx } from "clsx"
import { AutoGenerateModal } from "@/components/auto-generate/AutoGenerateModal"
import type { ProjectRead } from "@/types/api"

export default function ProjectsPage() {
  const { projects, fetchProjects, createProject, deleteProject, updateProject, isLoading } = useProjectStore()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingProject, setEditingProject] = useState<any>(null)
  const [autoGenerateProject, setAutoGenerateProject] = useState<ProjectRead | null>(null)
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    genre: "",
    themes: "",
    status: "draft",
  })
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState("")

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingProject) {
        await updateProject(editingProject.id, formData)
      } else {
        await createProject(formData)
      }
      setShowCreateModal(false)
      setEditingProject(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save project:", error)
    }
  }

  const handleEdit = (project: any) => {
    setEditingProject(project)
    setFormData({
      title: project.title,
      description: project.description || "",
      genre: project.genre || "",
      themes: project.themes || "",
      status: project.status,
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this project?")) {
      try {
        await deleteProject(id)
      } catch (error) {
        console.error("Failed to delete project:", error)
      }
    }
  }

  const resetForm = () => {
    setFormData({
      title: "",
      description: "",
      genre: "",
      themes: "",
      status: "draft",
    })
  }

  const openCreateModal = () => {
    setEditingProject(null)
    resetForm()
    setShowCreateModal(true)
  }

  const filteredProjects = projects.filter((project) => {
    const matchesSearch = project.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.description?.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = !statusFilter || project.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const statusOptions = [
    { value: "", label: "All Statuses" },
    { value: "draft", label: "Draft" },
    { value: "in_production", label: "In Production" },
    { value: "completed", label: "Completed" },
    { value: "archived", label: "Archived" },
  ]

  const genreOptions = [
    { value: "", label: "Select Genre" },
    { value: "drama", label: "Drama" },
    { value: "romance", label: "Romance" },
    { value: "thriller", label: "Thriller" },
    { value: "comedy", label: "Comedy" },
    { value: "horror", label: "Horror" },
    { value: "sci-fi", label: "Sci-Fi" },
    { value: "fantasy", label: "Fantasy" },
    { value: "action", label: "Action" },
    { value: "mystery", label: "Mystery" },
  ]

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Projects</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Manage your micro drama projects</p>
          </div>
          <Button onClick={openCreateModal}>
            <Plus className="w-4 h-4" />
            New Project
          </Button>
        </div>

        {/* Search and filters */}
        <Card variant="outlined">
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-400" />
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 rounded-lg border border-dark-300 dark:border-dark-600 bg-white dark:bg-dark-800 text-dark-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                options={statusOptions}
                className="w-full sm:w-48"
              />
            </div>
          </CardContent>
        </Card>

        {/* Projects grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {isLoading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="p-6 space-y-4">
                  <div className="h-6 bg-dark-200 dark:bg-dark-700 rounded w-3/4" />
                  <div className="h-4 bg-dark-200 dark:bg-dark-700 rounded w-1/2" />
                  <div className="h-4 bg-dark-200 dark:bg-dark-700 rounded w-1/3" />
                </CardContent>
              </Card>
            ))
          ) : filteredProjects.length === 0 ? (
            <div className="col-span-full text-center py-16">
              <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                <Plus className="w-8 h-8 text-dark-400" />
              </div>
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">
                {searchQuery || statusFilter ? "No projects found" : "No projects yet"}
              </h3>
              <p className="text-dark-500 dark:text-dark-400 mb-6">
                {searchQuery || statusFilter
                  ? "Try adjusting your search or filters"
                  : "Create your first micro drama project to get started"}
              </p>
              {!searchQuery && !statusFilter && (
                <Button onClick={openCreateModal}>
                  <Plus className="w-4 h-4" />
                  Create Project
                </Button>
              )}
            </div>
          ) : (
            filteredProjects.map((project) => (
              <Card key={project.id} className="flex flex-col">
                <CardContent className="p-5 flex-1 flex flex-col">
                  <div className="flex items-start justify-between mb-3">
                    <div className="w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center flex-shrink-0">
                      <BookOpen className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                    </div>
                    <span className={clsx(
                      "text-xs font-medium px-2 py-1 rounded-full",
                      project.status === "draft" && "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
                      project.status === "in_production" && "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
                      project.status === "completed" && "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
                      project.status === "archived" && "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
                    )}>
                      {project.status.replace("_", " ")}
                    </span>
                  </div>

                  <h3 className="font-semibold text-dark-900 dark:text-white mb-2 line-clamp-1">{project.title}</h3>

                  {project.description && (
                    <p className="text-sm text-dark-500 dark:text-dark-400 line-clamp-2 mb-3 flex-1">
                      {project.description}
                    </p>
                  )}

                  {project.genre && (
                    <span className="text-xs px-2 py-1 bg-dark-100 dark:bg-dark-800 rounded text-dark-600 dark:text-dark-400 mb-3 inline-block">
                      {project.genre}
                    </span>
                  )}

                  <div className="flex items-center justify-between pt-3 border-t border-dark-100 dark:border-dark-800">
                    <Link
                      href={`/dashboard/projects/${project.id}`}
                      className="text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                    >
                      Open Project
                    </Link>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setAutoGenerateProject(project)}
                        className="p-1.5"
                        title="Auto-Generate"
                      >
                        <Sparkles className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(project)}
                        className="p-1.5"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(project.id)}
                        className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Auto-Generate Modal */}
      {autoGenerateProject && (
        <AutoGenerateModal
          project={autoGenerateProject}
          onClose={() => setAutoGenerateProject(null)}
        />
      )}

      {/* Create/Edit Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setShowCreateModal(false)}>
          <Card className="w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <CardHeader>
              <CardTitle>{editingProject ? "Edit Project" : "New Project"}</CardTitle>
            </CardHeader>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <Input
                label="Title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Enter project title"
                required
              />
              <Textarea
                label="Description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Brief description of your micro drama"
                rows={3}
              />
              <div className="grid grid-cols-2 gap-4">
                <Select
                  label="Genre"
                  value={formData.genre}
                  onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
                  options={genreOptions}
                />
                <Select
                  label="Status"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  options={[
                    { value: "draft", label: "Draft" },
                    { value: "in_production", label: "In Production" },
                    { value: "completed", label: "Completed" },
                    { value: "archived", label: "Archived" },
                  ]}
                />
              </div>
              <Input
                label="Themes (comma-separated)"
                value={formData.themes}
                onChange={(e) => setFormData({ ...formData, themes: e.target.value })}
                placeholder="e.g., redemption, identity, sacrifice"
              />
              <div className="flex justify-end gap-3 pt-4">
                <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" loading={isLoading}>
                  {editingProject ? "Update" : "Create"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}
    </DashboardLayout>
  )
}

import { BookOpen } from "lucide-react"