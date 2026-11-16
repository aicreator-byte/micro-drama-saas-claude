"use client"

import { HTMLAttributes, forwardRef } from "react"
import { clsx } from "clsx"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "outlined" | "elevated"
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = "default", children, ...props }, ref) => {
    const variants = {
      default: "bg-white dark:bg-dark-800 border border-dark-200 dark:border-dark-700",
      outlined: "bg-transparent border-2 border-dark-200 dark:border-dark-700",
      elevated: "bg-white dark:bg-dark-800 shadow-lg border-none",
    }

    return (
      <div
        ref={ref}
        className={clsx("rounded-xl", variants[variant], className)}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = "Card"

export const CardHeader = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={clsx("px-6 py-4 border-b border-dark-200 dark:border-dark-700", className)} {...props}>
      {children}
    </div>
  )
)

CardHeader.displayName = "CardHeader"

export const CardTitle = forwardRef<HTMLHeadingElement, HTMLAttributes<HTMLHeadingElement>>(
  ({ className, children, ...props }, ref) => (
    <h3 ref={ref} className={clsx("text-lg font-semibold text-dark-900 dark:text-white", className)} {...props}>
      {children}
    </h3>
  )
)

CardTitle.displayName = "CardTitle"

export const CardDescription = forwardRef<HTMLParagraphElement, HTMLAttributes<HTMLParagraphElement>>(
  ({ className, children, ...props }, ref) => (
    <p ref={ref} className={clsx("text-sm text-dark-500 dark:text-dark-400 mt-1", className)} {...props}>
      {children}
    </p>
  )
)

CardDescription.displayName = "CardDescription"

export const CardContent = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={clsx("px-6 py-4", className)} {...props}>
      {children}
    </div>
  )
)

CardContent.displayName = "CardContent"

export const CardFooter = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={clsx("px-6 py-4 border-t border-dark-200 dark:border-dark-700 flex items-center gap-2", className)} {...props}>
      {children}
    </div>
  )
)

CardFooter.displayName = "CardFooter"