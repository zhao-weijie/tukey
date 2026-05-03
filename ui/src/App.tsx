import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { RunChainView } from "@/components/RunChainView";
import { WelcomeSetup } from "@/components/WelcomeSetup";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useTukeyStore } from "@/stores/tukeyStore";
import { apiClient } from "@/lib/api";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(true);
  const [showWelcome, setShowWelcome] = useState(false);
  const [providerDialogOpen, setProviderDialogOpen] = useState(false);
  const [demoPrompt, setDemoPrompt] = useState<string | null>(null);
  const { loadWorkspace, setActiveChainId, loadChainDetail, setProviders } = useTukeyStore();

  useEffect(() => {
    apiClient.listProviders()
      .then(async (providers) => {
        setProviders(providers);
        setShowWelcome(providers.length === 0);
        if (providers.length > 0) {
          await loadWorkspace();
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [loadWorkspace, setProviders]);

  const handleSetupComplete = async (result: {
    chainId: string;
    providers: any[];
    demoPrompt: string;
  }) => {
    setProviders(result.providers);
    await loadWorkspace();
    setActiveChainId(result.chainId);
    await loadChainDetail(result.chainId);
    setDemoPrompt(result.demoPrompt);
    setShowWelcome(false);
  };

  const handleSkipToProviders = () => {
    setShowWelcome(false);
    setProviderDialogOpen(true);
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-foreground/20 border-t-foreground" />
      </div>
    );
  }

  return (
    <TooltipProvider>
      <div className="flex h-screen overflow-hidden bg-background text-foreground">
        <Sidebar
          open={sidebarOpen}
          onToggle={() => setSidebarOpen((o) => !o)}
          providerDialogOpen={providerDialogOpen}
          onProviderDialogOpenChange={setProviderDialogOpen}
        />
        {showWelcome ? (
          <WelcomeSetup onComplete={handleSetupComplete} onSkip={handleSkipToProviders} />
        ) : (
          <RunChainView demoPrompt={demoPrompt} onDemoPromptUsed={() => setDemoPrompt(null)} />
        )}
      </div>
    </TooltipProvider>
  );
}
