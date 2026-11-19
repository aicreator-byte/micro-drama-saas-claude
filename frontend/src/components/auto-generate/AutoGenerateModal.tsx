"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import Link from "next/link"
import { autoGenerateApi } from "@/lib/api"
import { useProjectStore } from "@/lib/project-store"
import type { AutoGenerateJobRead, AutoGenerateStepName, ProjectRead } from "@/types/api"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Select } from "@/components/ui/Select"
import { Textarea } from "@/components/ui/Textarea"
import { Card, CardHeader, CardTitle } from "@/components/ui/Card"
import { Sparkles, Loader2, CheckCircle2, XCircle, AlertCircle, RotateCcw, X } from "lucide-react"
import { clsx } from "clsx"

// Fase 2 — Auto-Generate: satu modal untuk form input + progres 5 langkah +
// retry per langkah gagal. Kontrak backend (Fase 1): POST /api/projects/{id}/
// auto-generate menjalankan 5 langkah sinkron dan mengembalikan job yang
// sudah terminal; polling GET hanya berjaga bila status masih "running".
export const STEP_ORDER: AutoGenerateStepName[] = [
  "series_bible",
  "characters",
  "locations",
  "episodes",
  "prompts",
]

export const STEP_LABELS: Record<AutoGenerateStepName, string> = {
  series_bible: "Series Bible",
  characters: "Characters",
  locations: "Locations",
  episodes: "Episodes",
  prompts: "Prompts",
}

const GENRE_OPTIONS = [
  { value: "", label: "Auto (from title)" },
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

const RESULT_LINKS = [
  { name: "Series Bible", href: "/dashboard/series-bible" },
  { name: "Characters", href: "/dashboard/characters" },
  { name: "Locations", href: "/dashboard/locations" },
  { name: "Episodes", href: "/dashboard/episodes" },
  { name: "Prompts", href: "/dashboard/prompts" },
]

function stepStatusIcon(status: string) {
  if (status === "completed") return <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
  if (status === "failed") return <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
  if (status === "running") return <Loader2 className="w-5 h-5 text-yellow-600 dark:text-yellow-400 animate-spin" />
  return <span className="w-5 h-5 rounded-full border-2 border-dark-300 dark:border-dark-600 inline-block" />
}

function stepStatusBadge(status: string) {
  return (
    <span
      className={clsx(
        "text-xs font-medium px-2 py-1 rounded-full capitalize",
        status === "completed" && "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
        status === "failed" && "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
        (status === "pending" || status === "running") && "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
      )}
    >
      {status}
    </span>
  )
}

export function AutoGenerateModal({
  project,
  onClose,
}: {
  project: ProjectRead
  onClose: () => void
}) {
  const {
    setCurrentProject,
    fetchSeriesBible,
    fetchCharacters,
    fetchLocations,
    fetchEpisodes,
    fetchPrompts,
  } = useProjectStore()

  const [title, setTitle] = useState(project.title)
  const [genre, setGenre] = useState(project.genre || "")
  const [totalEpisodes, setTotalEpisodes] = useState(30)
  const [premise, setPremise] = useState(project.description || "")
  const [job, setJob] = useState<AutoGenerateJobRead | null>(null)
  const [starting, setStarting] = useState(false)
  const [retryingStep, setRetryingStep] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const refreshedJobId = useRef<string | null>(null)

  // Poll while the job is still running (backend Fase 1 runs synchronously,
  // so this normally never fires — it only guards a future async change).
  useEffect(() => {
    if (!job || job.status !== "running") return
    const timer = setInterval(async () => {
      try {
        const res = await autoGenerateApi.get(project.id, job.id)
        setJob(res.data)
      } catch (err) {
        console.error("Failed to poll auto-generate job:", err)
      }
    }, 2000)
    return () => clearInterval(timer)
  }, [job?.id, job?.status, project.id])

  // Job completed → refresh store data so the result pages show the new
  // rows without a manual refresh.
  const refreshResults = useCallback(
    (jobId: string) => {
      if (refreshedJobId.current === jobId) return
      refreshedJobId.current = jobId
      setCurrentProject(project)
      void fetchSeriesBible(project.id)
      void fetchCharacters(project.id)
      void fetchLocations(project.id)
      void fetchEpisodes(project.id)
      void fetchPrompts(project.id)
    },
    [project, setCurrentProject, fetchSeriesBible, fetchCharacters, fetchLocations, fetchEpisodes, fetchPrompts]
  )

  useEffect(() => {
    if (job && job.status === "completed") refreshResults(job.id)
  }, [job, refreshResults])

  const extractDetail = (err: any) =>
    err.response?.data?.detail || err.message || "Auto-generate failed"

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setStarting(true)
    setError(null)
    try {
      const res = await autoGenerateApi.create(project.id, {
        title: title.trim(),
        genre: genre || undefined,
        total_episodes: totalEpisodes,
        premise: premise.trim() || undefined,
      })
      setJob(res.data)
    } catch (err: any) {
      setError(extractDetail(err))
    } finally {
      setStarting(false)
    }
  }

  const handleRetry = async (step: AutoGenerateStepName) => {
    if (!job) return
    setRetryingStep(step)
    setError(null)
    try {
      const res = await autoGenerateApi.retry(project.id, job.id, step)
      setJob(res.data)
    } catch (err: any) {
      setError(extractDetail(err))
    } finally {
      setRetryingStep(null)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
    >
      <Card
        className="w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              Auto-Generate
            </span>
            <button
              onClick={onClose}
              className="text-dark-400 hover:text-dark-600 dark:hover:text-dark-300"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </CardTitle>
          <p className="text-sm text-dark-500 dark:text-dark-400">
            Project: <span className="font-medium text-dark-900 dark:text-white">{project.title}</span>
          </p>
        </CardHeader>

        {!job ? (
          <form onSubmit={handleStart} className="p-6 pt-0 space-y-4">
            <p className="text-sm text-dark-500 dark:text-dark-400">
              AI fills in everything — series bible, characters, locations, episodes,
              and video prompts — in 5 steps. Existing content is kept, never duplicated.
            </p>
            <Input
              label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter series title"
              required
            />
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Genre"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                options={GENRE_OPTIONS}
              />
              <Input
                label="Episodes"
                type="number"
                min={1}
                max={100}
                value={totalEpisodes}
                onChange={(e) => setTotalEpisodes(Number(e.target.value))}
                required
              />
            </div>
            <Textarea
              label="Premise (optional)"
              value={premise}
              onChange={(e) => setPremise(e.target.value)}
              placeholder="One or two sentences about the story…"
              rows={3}
            />
            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" loading={starting} disabled={!title.trim()}>
                <Sparkles className="w-4 h-4" />
                {starting ? "Generating…" : "Start Auto-Generate"}
              </Button>
            </div>
          </form>
        ) : (
          <div className="p-6 pt-0 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-dark-900 dark:text-white">
                Job: {job.title} ({job.total_episodes} episodes)
              </p>
              {stepStatusBadge(job.status)}
            </div>

            {job.error_message && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{job.error_message}</span>
              </div>
            )}

            <ol className="space-y-3">
              {STEP_ORDER.map((stepKey, idx) => {
                const step = job.steps.find((s) => s.step === stepKey)
                const status = step?.status || "pending"
                return (
                  <li
                    key={stepKey}
                    className="flex items-start gap-3 p-3 rounded-lg border border-dark-200 dark:border-dark-700"
                  >
                    <span className="text-sm font-bold text-primary-600 dark:text-primary-400 bg-primary-100 dark:bg-primary-900/30 w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0">
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-dark-900 dark:text-white">
                          {STEP_LABELS[stepKey]}
                        </span>
                        <span className="flex items-center gap-2">
                          {stepStatusBadge(status)}
                          {status === "failed" && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleRetry(stepKey)}
                              loading={retryingStep === stepKey}
                              disabled={job.status === "running"}
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                              Retry
                            </Button>
                          )}
                        </span>
                      </div>
                      {step?.error_message && (
                        <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                          Error: {step.error_message}
                        </p>
                      )}
                    </div>
                    <span className="flex-shrink-0 mt-0.5">{stepStatusIcon(status)}</span>
                  </li>
                )
              })}
            </ol>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {job.status === "completed" && (
              <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                <p className="text-sm font-medium text-green-700 dark:text-green-300 mb-2">
                  All 5 steps completed. Results are ready:
                </p>
                <div className="flex flex-wrap gap-2">
                  {RESULT_LINKS.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      className="text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 underline"
                    >
                      {link.name}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              {job.status === "completed" ? (
                <Button onClick={onClose}>Done</Button>
              ) : (
                <Button
                  variant="outline"
                  onClick={onClose}
                  disabled={job.status === "running"}
                >
                  Close
                </Button>
              )}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
