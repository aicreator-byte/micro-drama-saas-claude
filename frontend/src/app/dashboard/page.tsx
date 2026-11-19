"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useProjectStore } from "@/lib/project-store"
import { useAuthStore } from "@/lib/auth-store"
import { dashboardApi } from "@/lib/api"
import type { DashboardStats } from "@/types/api"
import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Plus, BookOpen, Users, MapPin, Clapperboard, Film, Type, Image, Puzzle, ArrowRight } from "lucide-react"

export default function DashboardPage() {
  const { user } = useAuthStore()
  const { projects, fetchProjects, isLoading: projectsLoading } = useProjectStore()
  const [stats, setStats] = useState<DashboardStats | null>(null)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  // Real counts from the DB (future-dev 2f) — no more hardcoded 0.
  useEffect(() => {
    dashboardApi
      .getStats()
      .then((res) => setStats(res.data))
      .catch(() => {})
  }, [])

  const statCards = [
    { name: "Projects", count: stats?.projects ?? projects.length, icon: BookOpen, href: "/dashboard/projects", color: "text-blue-600 bg-blue-100 dark:text-blue-400 dark:bg-blue-900/30" },
    { name: "Characters", count: stats?.characters ?? 0, icon: Users, href: "/dashboard/characters", color: "text-purple-600 bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30" },
    { name: "Locations", count: stats?.locations ?? 0, icon: MapPin, href: "/dashboard/locations", color: "text-green-600 bg-green-100 dark:text-green-400 dark:bg-green-900/30" },
    { name: "Episodes", count: stats?.episodes ?? 0, icon: Clapperboard, href: "/dashboard/episodes", color: "text-orange-600 bg-orange-100 dark:text-orange-400 dark:bg-orange-900/30" },
  ]

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Welcome header */}
        <div>
          <h1 className="text-3xl font-bold text-dark-900 dark:text-white">
            Welcome back, {user?.username || "User"}!
          </h1>
          <p className="text-dark-600 dark:text-dark-400 mt-1">
            Continue building your micro drama series
          </p>
        </div>

        {/* Stats cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((stat) => (
            <Link key={stat.name} href={stat.href} className="block">
              <Card className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-dark-500 dark:text-dark-400">{stat.name}</p>
                      <p className="text-3xl font-bold text-dark-900 dark:text-white mt-1">{stat.count}</p>
                    </div>
                    <div className={clsx("p-3 rounded-xl", stat.color)}>
                      <stat.icon className="w-6 h-6" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>

        {/* Quick actions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Your Projects
                <Link href="/dashboard/projects" className="text-sm font-normal text-primary-600 hover:text-primary-700 flex items-center gap-1">
                  View all <ArrowRight className="w-4 h-4" />
                </Link>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {projectsLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 animate-pulse bg-dark-100 dark:bg-dark-800 rounded-lg" />
                  ))}
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-8">
                  <BookOpen className="w-12 h-12 text-dark-300 dark:text-dark-600 mx-auto mb-4" />
                  <p className="text-dark-500 dark:text-dark-400 mb-4">No projects yet</p>
                  <Button onClick={() => window.location.href = "/dashboard/projects"}>
                    Create Project
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {projects.slice(0, 5).map((project) => (
                    <Link
                      key={project.id}
                      href={`/dashboard/projects/${project.id}`}
                      className="flex items-center justify-between p-3 rounded-lg hover:bg-dark-100 dark:hover:bg-dark-800 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                          <BookOpen className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                        </div>
                        <div>
                          <p className="font-medium text-dark-900 dark:text-white">{project.title}</p>
                          <p className="text-sm text-dark-500 dark:text-dark-400 capitalize">{project.status}</p>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-dark-400" />
                    </Link>
                  ))}
                  {projects.length > 5 && (
                    <Link
                      href="/dashboard/projects"
                      className="text-center text-sm text-primary-600 hover:text-primary-700 block py-2"
                    >
                      View all {projects.length} projects
                    </Link>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { name: "New Project", icon: Plus, href: "/dashboard/projects", desc: "Create drama project" },
                  { name: "Series Bible", icon: BookOpen, href: "/dashboard/series-bible", desc: "Story premise & plot" },
                  { name: "Characters", icon: Users, href: "/dashboard/characters", desc: "Character profiles" },
                  { name: "Locations", icon: MapPin, href: "/dashboard/locations", desc: "Environment settings" },
                  { name: "Episodes", icon: Clapperboard, href: "/dashboard/episodes", desc: "20-episode structure" },
                  { name: "Scenes", icon: Film, href: "/dashboard/scenes", desc: "Scene breakdowns" },
                  { name: "Prompts", icon: Type, href: "/dashboard/prompts", desc: "AI prompt generation" },
                  { name: "Flow Bridge", icon: Puzzle, href: "/dashboard/flow", desc: "Google Flow tasks" },
                ].map((action) => (
                  <Link
                    key={action.name}
                    href={action.href}
                    className="p-4 rounded-lg border border-dark-200 dark:border-dark-700 hover:border-primary-300 dark:hover:border-primary-700 hover:bg-dark-50 dark:hover:bg-dark-800/50 transition-colors text-left"
                  >
                    <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mb-2">
                      <action.icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                    </div>
                    <p className="font-medium text-dark-900 dark:text-white">{action.name}</p>
                    <p className="text-xs text-dark-500 dark:text-dark-400 mt-1">{action.desc}</p>
                  </Link>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Production pipeline overview */}
        <Card>
          <CardHeader>
            <CardTitle>Production Pipeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {[
                { step: 1, name: "Series Bible", desc: "Premise, plot, characters, world", icon: BookOpen },
                { step: 2, name: "Characters", desc: "Profiles, appearance, consistency", icon: Users },
                { step: 3, name: "Locations", desc: "Environments, lighting, atmosphere", icon: MapPin },
                { step: 4, name: "Story Engine", desc: "20 episodes, conflicts, cliffhangers", icon: Clapperboard },
                { step: 5, name: "Scenes", desc: "Breakdown, shots, dialogues", icon: Film },
                { step: 6, name: "Prompts", desc: "Image, video, audio generation", icon: Type },
                { step: 7, name: "Assets", desc: "Generated media management", icon: Image },
                { step: 8, name: "Post-Production", desc: "Assembly, audio, subtitles, export", icon: Puzzle },
              ].map((stage) => (
                <div key={stage.name} className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                    <stage.icon className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-primary-600 dark:text-primary-400 bg-primary-100 dark:bg-primary-900/30 w-6 h-6 rounded-full flex items-center justify-center">
                        {stage.step}
                      </span>
                      <h4 className="font-semibold text-dark-900 dark:text-white">{stage.name}</h4>
                    </div>
                    <p className="text-sm text-dark-500 dark:text-dark-400 mt-1">{stage.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

import { clsx } from "clsx"