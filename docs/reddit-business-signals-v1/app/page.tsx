"use client"
import { Button } from "@/components/ui/button"
import { Search } from "lucide-react"
import ProductInputForm from "@/components/product-input-form"
import AnalysisProgress from "@/components/analysis-progress"
import InsightsReport from "@/components/insights-report"
import NavigationBreadcrumb from "@/components/navigation-breadcrumb"
import AuthDialog from "@/components/auth-dialog"
import { useAppState } from "@/hooks/use-app-state"
import { useState } from "react"

export default function HomePage() {
  const [state, actions] = useAppState()
  const [showAuthDialog, setShowAuthDialog] = useState(false)
  const [authDialogMode, setAuthDialogMode] = useState<"login" | "signup">("signup")

  const handleStartAnalysis = (description: string) => {
    actions.setProductDescription(description)
    actions.setCurrentStep("analysis")
  }

  const handleAnalysisComplete = (id: string) => {
    actions.setAnalysisId(id)
    actions.setCurrentStep("report")
  }

  const handleAnalysisCancel = () => {
    actions.resetAnalysis()
  }

  const handleNavigate = (step: "input" | "analysis" | "report") => {
    // Only allow navigation back to completed steps or current step
    const currentStepIndex = ["input", "analysis", "report"].indexOf(state.currentStep)
    const targetStepIndex = ["input", "analysis", "report"].indexOf(step)

    if (targetStepIndex <= currentStepIndex) {
      actions.setCurrentStep(step)
    }
  }

  const handleLogin = (email: string, password: string) => {
    // Mock login - in real app, this would call an API
    actions.login({ id: "1", name: email.split("@")[0], email })
    setShowAuthDialog(false)
  }

  const handleSignup = (email: string, password: string) => {
    // Mock signup - in real app, this would call an API
    actions.login({ id: "1", name: email.split("@")[0], email })
    setShowAuthDialog(false)
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-primary-foreground" />
            </div>
            <h1 className="text-xl font-bold text-foreground">Reddit 商业信号扫描器</h1>
          </div>
          <div className="flex items-center space-x-4">
            {state.isAuthenticated && state.user ? (
              <>
                <span className="text-sm text-muted-foreground">欢迎，{state.user.name}</span>
                <Button variant="outline" size="sm" onClick={actions.logout}>
                  退出登录
                </Button>
              </>
            ) : (
              <div className="flex items-center space-x-2">
                <AuthDialog
                  onLogin={handleLogin}
                  onSignup={handleSignup}
                  open={showAuthDialog && authDialogMode === "login"}
                  onOpenChange={(open) => {
                    setShowAuthDialog(open)
                    if (open) setAuthDialogMode("login")
                  }}
                >
                  <Button variant="outline" size="sm">
                    登录
                  </Button>
                </AuthDialog>
                <AuthDialog
                  onLogin={handleLogin}
                  onSignup={handleSignup}
                  open={showAuthDialog && authDialogMode === "signup"}
                  onOpenChange={(open) => {
                    setShowAuthDialog(open)
                    if (open) setAuthDialogMode("signup")
                  }}
                >
                  <Button size="sm">注册</Button>
                </AuthDialog>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <NavigationBreadcrumb
          currentStep={state.currentStep}
          onNavigate={handleNavigate}
          canNavigateBack={state.currentStep !== "analysis"}
        />

        {state.currentStep === "input" && <ProductInputForm onStartAnalysis={handleStartAnalysis} />}

        {state.currentStep === "analysis" && (
          <AnalysisProgress
            productDescription={state.productDescription}
            onComplete={handleAnalysisComplete}
            onCancel={handleAnalysisCancel}
          />
        )}

        {state.currentStep === "report" && (
          <InsightsReport
            analysisId={state.analysisId}
            productDescription={state.productDescription}
            onNewAnalysis={actions.resetAnalysis}
          />
        )}
      </main>
    </div>
  )
}
