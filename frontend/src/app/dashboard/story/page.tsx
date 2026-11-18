"use client"

import { useEffect, useState } from "react"
import { useProjectStore } from "@/lib/project-store"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Textarea } from "@/components/ui/Textarea"
import { Select } from "@/components/ui/Select"
import { Sparkles, Trash2, Loader2, AlertCircle } from "lucide-react"
import { clsx } from "clsx"
import { useAuthStore } from "@/lib/auth-store"

// Audit ronde 2 P1-15 (F-L7): the story engine had API + store actions but
// no UI at all. This page wires them: pick a project + generation type,
// write a prompt, generate (real LLM via /api/story-engine/generate),
// and browse history with status / error / output.
const GENERATION_TYPES = [
  { value: "story_idea", label: "Story Idea" },
  { value: "episode_outline", label: "Episode Outline" },
  { value: "full_series", label: "Full Series (20 episodes)" },
  { value: "scene_breakdown", label: "Scene Breakdown" },
  { value: "dialogue_generation", label: "Dialogue Generation" },
  { value: "character_development", label: "Character Development" },
  { value: "conflict_development", label: "Conflict Development" },
  { value: "cliffhanger", label: "Cliffhanger" },
]

export default function StoryPage() {
  const {
    projects, fetchProjects,
    storyGenerations, fetchStoryGenerations, generateStory, deleteStoryGeneration,
    isLoading, error,
  } = useProjectStore()
  const { user } = useAuthStore()

  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [generationType, setGenerationType] = useState<string>("story_idea")
  const [prompt, setPrompt] = useState("")
  const [generating, setGenerating] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  useEffect(() => {
    if (projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id)
    }
  }, [projects, selectedProjectId])

  useEffect(() => {
    if (selectedProjectId) fetchStoryGenerations(selectedProjectId)
  }, [selectedProjectId, fetchStoryGenerations])

  if (!user) return null

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedProjectId || !prompt.trim()) return
    setGenerating(true)
    setLocalError(null)
    try {
      await generateStory({
        project_id: selectedProjectId,
        generation_type: generationType,
        context: { prompt: prompt.trim() },
      })
    } catch (err: any) {
      setLocalError(err.response?.data?.detail || "Story generation failed")
    } finally {
      setGenerating(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!selectedProjectId) return
    if (confirm("Delete this generation?")) {
      try {
        await deleteStoryGeneration(selectedProjectId, id)
      } catch (err) {
        console.error("Failed to delete generation:", err)
      }
    }
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-white">Story Engine</h1>
          <p className="text-dark-600 dark:text-dark-400 mt-1">
            Generate story ideas, outlines, and breakdowns with the configured AI provider.
            Failures are recorded with status “failed” and an error message — nothing is silently dropped.
          </p>
        </div>

        <Card variant="outlined">
          <CardHeader>
            <CardTitle>Generate</CardTitle>
            <CardDescription>Pick a project and a generation type, then describe what you want.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleGenerate} className="space-y-4">
              <Select
                label="Project"
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                options={projects.map((p) => ({ value: p.id, label: p.title }))}
              />
              <Select
                label="Generation type"
                value={generationType}
                onChange={(e) => setGenerationType(e.target.value)}
                options={GENERATION_TYPES}
              />
              <Textarea
                label="Prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g. A widowed baker in Bandung discovers her late husband left a second family…"
                rows={4}
                required
              />
              {(localError || error) && (
                <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{localError || error}</span>
                </div>
              )}
              <Button type="submit" loading={generating} disabled={!selectedProjectId || !prompt.trim()}>
                <Sparkles className="w-4 h-4" />
                {generating ? "Generating…" : "Generate"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>History ({storyGenerations.length})</CardTitle>
            <CardDescription>Past generations for the selected project, newest first.</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center gap-2 text-dark-500 py-4">
                <Loader2 className="w-4 h-4 animate-spin" /> Loading…
              </div>
            ) : storyGenerations.length === 0 ? (
              <p className="text-dark-500 dark:text-dark-400 py-6 text-center">No generations yet for this project.</p>
            ) : (
              <div className="space-y-3">
                {storyGenerations.map((gen) => (
                  <div key={gen.id} className="p-4 rounded-lg border border-dark-200 dark:border-dark-700">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-dark-900 dark:text-white">{gen.generation_type}</span>
                        <span className={clsx(
                          "text-xs font-medium px-2 py-1 rounded-full",
                          gen.status === "completed" && "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
                          gen.status === "failed" && "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
                          (gen.status === "pending" || gen.status === "generating") && "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
                        )}>
                          {gen.status}
                        </span>
                        {gen.model_used && <span className="text-xs text-dark-500">{gen.model_used}</span>}
                        {gen.tokens_used != null && <span className="text-xs text-dark-500">{gen.tokens_used} tokens</span>}
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(gen.id)} className="p-1.5 text-red-600 hover:text-red-700">
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                    {gen.input_prompt && (
                      <p className="text-sm text-dark-500 dark:text-dark-400 mt-2">Prompt: {gen.input_prompt}</p>
                    )}
                    {gen.error_message && (
                      <p className="text-sm text-red-600 dark:text-red-400 mt-2">Error: {gen.error_message}</p>
                    )}
                    {gen.generated_output && (
                      <pre className="text-sm text-dark-700 dark:text-dark-300 mt-2 whitespace-pre-wrap break-words bg-dark-50 dark:bg-dark-800/50 rounded p-3 max-h-96 overflow-y-auto">
                        {gen.generated_output}
                      </pre>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
