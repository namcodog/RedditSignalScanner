"use client"

import { useState, useCallback } from "react"

export interface AppState {
  isAuthenticated: boolean
  currentStep: "input" | "analysis" | "report"
  productDescription: string
  analysisId: string
  user: {
    name: string
    email: string
  } | null
}

export interface AppActions {
  login: (user: { id: string; name: string; email: string }) => void
  logout: () => void
  setCurrentStep: (step: "input" | "analysis" | "report") => void
  setProductDescription: (description: string) => void
  setAnalysisId: (id: string) => void
  resetAnalysis: () => void
}

const initialState: AppState = {
  isAuthenticated: false,
  currentStep: "input",
  productDescription: "",
  analysisId: "",
  user: null,
}

export function useAppState(): [AppState, AppActions] {
  const [state, setState] = useState<AppState>(initialState)

  const actions: AppActions = {
    login: useCallback((user: { id: string; name: string; email: string }) => {
      console.log("[v0] Login:", user)
      setState((prev) => ({
        ...prev,
        isAuthenticated: true,
        user: { email: user.email, name: user.name },
      }))
    }, []),

    logout: useCallback(() => {
      console.log("[v0] Logout")
      setState(initialState)
    }, []),

    setCurrentStep: useCallback((step: "input" | "analysis" | "report") => {
      console.log("[v0] Step change:", step)
      setState((prev) => ({ ...prev, currentStep: step }))
    }, []),

    setProductDescription: useCallback((description: string) => {
      console.log("[v0] Product description set:", description.substring(0, 50) + "...")
      setState((prev) => ({ ...prev, productDescription: description }))
    }, []),

    setAnalysisId: useCallback((id: string) => {
      console.log("[v0] Analysis ID set:", id)
      setState((prev) => ({ ...prev, analysisId: id }))
    }, []),

    resetAnalysis: useCallback(() => {
      console.log("[v0] Analysis reset")
      setState((prev) => ({
        ...prev,
        currentStep: "input",
        productDescription: "",
        analysisId: "",
      }))
    }, []),
  }

  return [state, actions]
}
