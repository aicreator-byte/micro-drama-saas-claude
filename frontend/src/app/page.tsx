"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuthStore } from "@/lib/auth-store"
import Link from "next/link"

export default function HomePage() {
  const router = useRouter()
  const { isAuthenticated, checkAuth } = useAuthStore()

  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard")
    }
  }, [isAuthenticated, router])

  if (isAuthenticated === undefined) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-dark-200 dark:border-dark-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Link href="/" className="text-xl font-bold text-primary-600 dark:text-primary-400">
                Micro Drama SaaS
              </Link>
            </div>
            <nav className="flex items-center space-x-4">
              <Link
                href="/login"
                className="text-dark-600 dark:text-dark-300 hover:text-primary-600 dark:hover:text-primary-400"
              >
                Sign In
              </Link>
              <Link
                href="/register"
                className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors"
              >
                Get Started
              </Link>
            </nav>
          </div>
        </div>
      </header>

      <main className="flex-1">
        <section className="relative overflow-hidden bg-gradient-to-b from-primary-50 to-white dark:from-dark-900 dark:to-dark-950 py-20 sm:py-32">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-dark-900 dark:text-white mb-6">
                Create Micro Dramas with{" "}
                <span className="text-primary-600 dark:text-primary-400">AI</span>
              </h1>
              <p className="text-lg sm:text-xl text-dark-600 dark:text-dark-300 max-w-3xl mx-auto mb-10">
                From story concept to final video — AI-powered tools for every step of micro drama production.
                Series bible, characters, locations, scenes, prompts, and post-production in one platform.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  href="/register"
                  className="bg-primary-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-primary-700 transition-colors w-full sm:w-auto"
                >
                  Start Free
                </Link>
                <Link
                  href="/login"
                  className="border-2 border-dark-300 dark:border-dark-600 text-dark-700 dark:text-dark-200 px-8 py-3 rounded-lg text-lg font-medium hover:bg-dark-100 dark:hover:bg-dark-800 transition-colors w-full sm:w-auto"
                >
                  Sign In
                </Link>
              </div>
            </div>
          </div>
        </section>

        <section className="py-20 bg-white dark:bg-dark-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-3xl font-bold text-center text-dark-900 dark:text-white mb-12">
              Production Pipeline
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { icon: "BookOpen", title: "Series Bible", desc: "Premise, plot, characters, world" },
                { icon: "Users", title: "Character Studio", desc: "Profiles, appearance, consistency" },
                { icon: "MapPin", title: "Location Studio", desc: "Environments, lighting, atmosphere" },
                { icon: "Clapperboard", title: "Story Engine", desc: "20-episode outlines, conflicts" },
                { icon: "Film", title: "Scene Engine", desc: "Breakdowns, shots, dialogues" },
                { icon: "Type", title: "Prompt Studio", desc: "Image, video, audio prompts" },
                { icon: "LayoutGrid", title: "Episode Manager", desc: "Progress, assets, costs" },
                { icon: "Puzzle", title: "Flow Bridge", desc: "Google Flow integration" },
              ].map((feature) => (
                <div key={feature.title} className="p-6 rounded-xl border border-dark-200 dark:border-dark-700 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
                  <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center mb-4">
                    <span className="text-primary-600 dark:text-primary-400 text-2xl">{feature.icon}</span>
                  </div>
                  <h3 className="text-lg font-semibold text-dark-900 dark:text-white mb-2">{feature.title}</h3>
                  <p className="text-dark-600 dark:text-dark-400">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-dark-200 dark:border-dark-700 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-dark-500 dark:text-dark-400">
          <p>Micro Drama SaaS — AI-powered Micro Drama Production Platform</p>
        </div>
      </footer>
    </div>
  )
}