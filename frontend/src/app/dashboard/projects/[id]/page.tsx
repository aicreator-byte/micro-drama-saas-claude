"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useParams } from "next/navigation"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { ArrowLeft, Loader2, Sparkles } from "lucide-react"
import { clsx } from "clsx"
import { projectApi } from "@/lib/api"
import { useProjectStore } from "@/lib/project-store"
import { AutoGenerateModal } from "@/components/auto-generate/AutoGenerateModal"
import type { ProjectRead } from "@/types/api"

// Project detail page (audit ronde 2 fix: the "Open Project" links in
// the dashboard and the projects list pointed here, but this route did
// not exist, so every click landed on a 404).
// Sections link to the existing per-project pages, which read the
// project from the store (set as currentProject on load).
const SECTIONS = [
  { href: "series-bible", title: "Series Bible", desc: "Premise, plot, world and tone" },
  { href: "characters", title: "Characters", desc: "Cast, appearance and personality" },
  { href: "locations", title: "Locations", desc: "Sets and places" },
  { href: "episodes", title: "Episodes", desc: "Episode list and status" },
  { href: "scenes", title: "Scenes", desc: "Scenes per episode" },
  { href: "dialogues", title: "Dialogues", desc: "Lines per scene" },
  { href: "prompts", title: "Prompts", desc: "Image and video prompts" },
  { href: "story", title: "Story Engine", desc: "LLM story generation" },
  { href: "flow", title: "Flow Bridge", desc: "Google Flow tasks" },
  { href: "assets", title: "Assets", desc: "Uploaded files" },
  { href: "google-accounts", title: "Google Accounts", desc: "Linked Google accounts" },
  { href: "settings", title: "Settings", desc: "Project settings" },
]

export default function ProjectDetailPage() {
  const params = useParams()
  const projectId = params.id as string
  const { setCurrentProject } = useProjectStore()
  const [project, setProject] = useState<ProjectRead | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [showAutoGenerate, setShowAutoGenerate] = useState(false)

  useEffect(() => {
    let cancelled = false
    projectApi
      .get(projectId)
      .then((response) => {
        if (cancelled) return
        setProject(response.data)
        setCurrentProject(response.data)
      })
      .catch(() => {
        if (!cancelled) setNotFound(true)
      })
    return () => {
      cancelled = true
    }
  }, [projectId, setCurrentProject])

  if (notFound) {
    return (
      <DashboardLayout>
        <div className="max-w-3xl mx-auto text-center py-16">
          <h1 className="text-xl font-semibold text-dark-900 dark:text-white mb-2">Project not found</h1>
          <p className="text-dark-500 dark:text-dark-400 mb-6">
            This project does not exist or you do not have access to it.
          </p>
          <Link href="/dashboard/projects">
            <Button>
              <ArrowLeft className="w-4 h-4 mr-2" /> Back to Projects
            </Button>
          </Link>
        </div>
      </DashboardLayout>
    )
  }

  if (!project) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-dark-400" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="max-w-5xl mx-auto space-y-6">
        <Link
          href="/dashboard/projects"
          className="inline-flex items-center text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Projects
        </Link>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div>
                <CardTitle>{project.title}</CardTitle>
                {project.description && <CardDescription>{project.description}</CardDescription>}
              </div>
              <span
                className={clsx(
                  "text-xs px-2 py-1 rounded shrink-0",
                  project.status === "draft" && "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
                  project.status === "in_production" && "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
                  project.status === "completed" && "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
                  project.status === "archived" && "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
                )}
              >
                {project.status.replace("_", " ")}
              </span>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-3">
              {project.genre && (
                <span className="text-xs px-2 py-1 bg-dark-100 dark:bg-dark-800 rounded text-dark-600 dark:text-dark-400">
                  {project.genre}
                </span>
              )}
              {project.themes && (
                <span className="text-xs text-dark-500 dark:text-dark-400">{project.themes}</span>
              )}
              <span className="flex-1" />
              <Button onClick={() => setShowAutoGenerate(true)}>
                <Sparkles className="w-4 h-4 mr-2" /> Auto-Generate
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {SECTIONS.map((section) => (
            <Link key={section.href} href={`/dashboard/${section.href}`}>
              <Card className="h-full hover:border-primary-300 dark:hover:border-primary-700 transition-colors cursor-pointer">
                <CardHeader>
                  <CardTitle className="text-base">{section.title}</CardTitle>
                  <CardDescription>{section.desc}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {showAutoGenerate && (
        <AutoGenerateModal project={project} onClose={() => setShowAutoGenerate(false)} />
      )}
    </DashboardLayout>
  )
}
