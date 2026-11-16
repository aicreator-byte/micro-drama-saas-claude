"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Textarea } from "@/components/ui/Textarea"
import { Select } from "@/components/ui/Select"
import { Plus, Edit, Trash2, Save, X, Puzzle, Loader2, ExternalLink, Download, Upload, FileText } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

const FLOW_TASK_TYPES = [
  { value: "image_generation", label: "Image Generation" },
  { value: "video_generation", label: "Video Generation" },
  { value: "prompt_preparation", label: "Prompt Preparation" },
  { value: "asset_organization", label: "Asset Organization" },
]

const FLOW_STATUSES = [
  { value: "pending", label: "Pending" },
  { value: "ready_for_flow", label: "Ready for Flow" },
  { value: "in_progress", label: "In Progress" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "imported", label: "Imported" },
]

export default function FlowBridgePage() {
  const {
    flowTasks, fetchFlowTasks, createFlowTask, updateFlowTask, deleteFlowTask,
    exportForFlow, importFromFlow, getFlowDeeplink,
    googleAccounts, fetchGoogleAccounts,
    episodes, fetchEpisodes,
    scenes, fetchScenes,
    isLoading
  } = useProjectStore()
  const { projects } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [selectedEpisodeId, setSelectedEpisodeId] = useState<string>("")
  const [selectedSceneId, setSelectedSceneId] = useState<string>("")
  const [statusFilter, setStatusFilter] = useState<string>("")
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingTask, setEditingTask] = useState<any>(null)
  const [formData, setFormData] = useState({
    task_type: "image_generation",
    title: "",
    description: "",
    input_prompts: "",
    reference_assets: "",
    status: "pending",
    google_account_id: "",
    episode_id: "",
    scene_id: "",
  })
  const [exportData, setExportData] = useState<any>(null)
  const [importData, setImportData] = useState({
    flow_task_id: "",
    output_assets: "",
    notes: "",
  })
  const [importingTaskId, setImportingTaskId] = useState<string | null>(null)

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  useEffect(() => {
    if (selectedProjectId) {
      fetchFlowTasks(selectedProjectId, {
        status: statusFilter || undefined,
        episode_id: selectedEpisodeId || undefined,
        scene_id: selectedSceneId || undefined,
      })
      fetchEpisodes(selectedProjectId)
      fetchGoogleAccounts()
    }
  }, [selectedProjectId, statusFilter, selectedEpisodeId, selectedSceneId, fetchFlowTasks, fetchEpisodes, fetchGoogleAccounts])

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
        google_account_id: formData.google_account_id || undefined,
        input_prompts: formData.input_prompts ? JSON.parse(formData.input_prompts) : undefined,
        reference_assets: formData.reference_assets ? JSON.parse(formData.reference_assets) : undefined,
      }

      if (editingTask) {
        await updateFlowTask(selectedProjectId, editingTask.id, data)
      } else {
        await createFlowTask(data)
      }
      setShowCreateModal(false)
      setEditingTask(null)
      resetForm()
    } catch (error) {
      console.error("Failed to save flow task:", error)
    }
  }

  const handleEdit = (task: any) => {
    setEditingTask(task)
    setFormData({
      task_type: task.task_type,
      title: task.title,
      description: task.description || "",
      input_prompts: task.input_prompts || "",
      reference_assets: task.reference_assets || "",
      status: task.status,
      google_account_id: task.google_account_id || "",
      episode_id: task.episode_id || "",
      scene_id: task.scene_id || "",
    })
    setShowCreateModal(true)
  }

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this flow task?")) {
      try {
        await deleteFlowTask(selectedProjectId, id)
      } catch (error) {
        console.error("Failed to delete flow task:", error)
      }
    }
  }

  const handleExport = async (task: any) => {
    try {
      const result = await exportForFlow({
        project_id: selectedProjectId,
        episode_id: task.episode_id,
        scene_id: task.scene_id,
        task_type: task.task_type,
        prompts: task.input_prompts ? JSON.parse(task.input_prompts) : [],
        reference_assets: task.reference_assets ? JSON.parse(task.reference_assets) : [],
        metadata: { title: task.title, description: task.description },
      })
      setExportData(result)
    } catch (error) {
      console.error("Failed to export:", error)
    }
  }

  const handleImport = async (taskId: string) => {
    setImportingTaskId(taskId)
    try {
      await importFromFlow({
        flow_task_id: taskId,
        output_assets: JSON.parse(importData.output_assets),
        notes: importData.notes,
      })
      setImportData({ flow_task_id: "", output_assets: "", notes: "" })
      setImportingTaskId(null)
    } catch (error) {
      console.error("Failed to import:", error)
      setImportingTaskId(null)
    }
  }

  const handleGetDeeplink = async (taskId: string) => {
    try {
      const result = await getFlowDeeplink(selectedProjectId, taskId)
      window.open(result.deeplink, "_blank")
    } catch (error) {
      console.error("Failed to get deeplink:", error)
    }
  }

  const resetForm = () => {
    setFormData({
      task_type: "image_generation",
      title: "",
      description: "",
      input_prompts: "",
      reference_assets: "",
      status: "pending",
      google_account_id: "",
      episode_id: "",
      scene_id: "",
    })
  }

  const openCreateModal = () => {
    setEditingTask(null)
    resetForm()
    setShowCreateModal(true)
  }

  const downloadExport = () => {
    if (!exportData) return
    const content = JSON.stringify(exportData, null, 2)
    const blob = new Blob([content], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `flow-export-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      pending: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
      ready_for_flow: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
      in_progress: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
      completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
      failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
      imported: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300",
    }
    return colors[status] || colors.pending
  }

  if (!user) return null

  const filteredTasks = flowTasks.filter(t =>
    !statusFilter || t.status === statusFilter
  )

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Flow Bridge</h1>
            <p className="text-dark-600 dark:text-dark-400 mt-1">Manage Google Flow integration tasks</p>
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
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  options={[{ value: "", label: "All Status" }, ...FLOW_STATUSES]}
                  className="w-48"
                />
                <Button onClick={openCreateModal}>
                  <Plus className="w-4 h-4" />
                  Add Task
                </Button>
              </>
            )}
          </div>
        </div>

        {selectedProjectId && (
          <Card>
            <CardHeader>
              <CardTitle>Flow Tasks ({filteredTasks.length})</CardTitle>
              <CardDescription>Prepare prompts and assets for Google Flow. Export for manual processing, import results.</CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-20 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                  ))}
                </div>
              ) : filteredTasks.length === 0 ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 rounded-full bg-dark-100 dark:bg-dark-800 flex items-center justify-center mx-auto mb-4">
                    <Puzzle className="w-8 h-8 text-dark-400" />
                  </div>
                  <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No flow tasks yet</h3>
                  <p className="text-dark-500 dark:text-dark-400 mb-6">Create a task to organize your Flow workflow</p>
                  <Button onClick={openCreateModal}>
                    <Plus className="w-4 h-4" />
                    Add Task
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {filteredTasks.map((task) => (
                    <div key={task.id} className="p-4 rounded-lg border border-dark-200 dark:border-dark-700 hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-medium text-dark-900 dark:text-white truncate">{task.title}</h4>
                            <span className={clsx("text-xs font-medium px-2 py-1 rounded-full", getStatusColor(task.status))}>
                              {FLOW_STATUSES.find(s => s.value === task.status)?.label || task.status}
                            </span>
                            <span className="text-xs px-2 py-1 bg-dark-100 dark:bg-dark-800 text-dark-600 dark:text-dark-400 rounded-full">
                              {FLOW_TASK_TYPES.find(t => t.value === task.task_type)?.label || task.task_type}
                            </span>
                          </div>
                          {task.description && (
                            <p className="text-sm text-dark-500 dark:text-dark-400 mb-2">{task.description}</p>
                          )}
                          {task.google_account_id && googleAccounts.length > 0 && (
                            <p className="text-xs text-dark-500 dark:text-dark-400">
                              Google Account: {googleAccounts.find(a => a.id === task.google_account_id)?.email || "Unknown"}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0 flex-wrap">
                          {task.status === "ready_for_flow" && (
                            <Button variant="outline" size="sm" onClick={() => handleExport(task)} className="gap-1">
                              <FileText className="w-3 h-3" />
                              Export
                            </Button>
                          )}
                          {task.status !== "completed" && task.status !== "imported" && (
                            <Button variant="outline" size="sm" onClick={() => handleGetDeeplink(task.id)} className="gap-1">
                              <ExternalLink className="w-3 h-3" />
                              Open Flow
                            </Button>
                          )}
                          {(task.status === "completed" || task.status === "ready_for_flow") && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setImportData({ ...importData, flow_task_id: task.id })
                                setImportingTaskId(task.id)
                              }}
                              className="gap-1"
                            >
                              <Upload className="w-3 h-3" />
                              Import
                            </Button>
                          )}
                          <Button variant="ghost" size="sm" onClick={() => handleEdit(task)} className="p-1.5">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDelete(task.id)} className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300">
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>

                      {importingTaskId === task.id && (
                        <div className="mt-3 p-3 bg-dark-50 dark:bg-dark-800/50 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-dark-900 dark:text-white">Import Results from Flow</span>
                            <Button variant="ghost" size="sm" onClick={() => setImportingTaskId(null)} className="p-1">
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                          <Textarea
                            label="Output Assets (JSON array)"
                            value={importData.output_assets}
                            onChange={(e) => setImportData({ ...importData, output_assets: e.target.value })}
                            placeholder='["asset_id_1", "asset_id_2", ...]'
                            rows={2}
                          />
                          <Input
                            label="Notes (Optional)"
                            value={importData.notes}
                            onChange={(e) => setImportData({ ...importData, notes: e.target.value })}
                            placeholder="Any notes about the generated results..."
                          />
                          <div className="flex justify-end gap-2 mt-3">
                            <Button variant="outline" onClick={() => setImportingTaskId(null)}>Cancel</Button>
                            <Button onClick={() => handleImport(task.id)} loading={isLoading}>
                              Import Results
                            </Button>
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

        {/* Export Data Modal */}
        {exportData && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => setExportData(null)}>
            <Card className="w-full max-w-2xl max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Export for Google Flow</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setExportData(null)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-6">
                <div className="mb-4">
                  <h4 className="font-medium text-dark-900 dark:text-white mb-2">Instructions</h4>
                  <p className="text-sm text-dark-600 dark:text-dark-400 mb-4">
                    {exportData.instructions}
                  </p>
                </div>
                <div className="mb-4">
                  <h4 className="font-medium text-dark-900 dark:text-white mb-2">Export Data</h4>
                  <div className="bg-dark-100 dark:bg-dark-800 p-4 rounded-lg max-h-64 overflow-auto">
                    <pre className="text-sm text-dark-700 dark:text-dark-300 font-mono whitespace-pre-wrap">
                      {JSON.stringify(exportData, null, 2)}
                    </pre>
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setExportData(null)}>Close</Button>
                  <Button onClick={downloadExport}>
                    <Download className="w-4 h-4" />
                    Download JSON
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {!selectedProjectId && projects.length === 0 && (
          <Card variant="outlined">
            <CardContent className="p-12 text-center">
              <h3 className="text-lg font-medium text-dark-900 dark:text-white mb-2">No projects yet</h3>
              <p className="text-dark-500 dark:text-dark-400 mb-4">Create a project first to start using Flow Bridge</p>
              
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
                  <CardTitle>{editingTask ? "Edit Flow Task" : "New Flow Task"}</CardTitle>
                  <Button variant="ghost" size="sm" onClick={() => setShowCreateModal(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </CardHeader>
              <form onSubmit={handleSubmit} className="p-6 space-y-4">
                <Select
                  label="Task Type"
                  value={formData.task_type}
                  onChange={(e) => setFormData({ ...formData, task_type: e.target.value })}
                  options={FLOW_TASK_TYPES}
                  required
                />

                <Input
                  label="Title"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="e.g., Generate character portraits for Ep 1"
                  required
                />

                <Textarea
                  label="Description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Describe what this task involves..."
                  rows={2}
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

                <Select
                  label="Google Account (Optional)"
                  value={formData.google_account_id}
                  onChange={(e) => setFormData({ ...formData, google_account_id: e.target.value })}
                  options={[
                    { value: "", label: "None" },
                    ...googleAccounts.map(a => ({ value: a.id, label: a.email }))
                  ]}
                />

                <Textarea
                  label="Input Prompts (JSON array)"
                  value={formData.input_prompts}
                  onChange={(e) => setFormData({ ...formData, input_prompts: e.target.value })}
                  placeholder='["prompt 1", "prompt 2", ...]'
                  rows={3}
                />

                <Textarea
                  label="Reference Assets (JSON array of asset IDs)"
                  value={formData.reference_assets}
                  onChange={(e) => setFormData({ ...formData, reference_assets: e.target.value })}
                  placeholder='["asset_id_1", "asset_id_2", ...]'
                  rows={2}
                />

                <Select
                  label="Status"
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  options={FLOW_STATUSES}
                />

                <div className="flex justify-end gap-3 pt-4">
                  <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" loading={isLoading}>
                    <Save className="w-4 h-4" />
                    {editingTask ? "Update" : "Create"}
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