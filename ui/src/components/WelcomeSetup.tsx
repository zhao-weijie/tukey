import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api";

const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";

const QUICK_START_MODELS = [
  { model_id: "openai/gpt-4.1-nano", display_name: "GPT-4.1 Nano" },
  { model_id: "stepfun/step-3.5-flash:free", display_name: "Step 3.5 Flash" },
  { model_id: "nvidia/nemotron-3-super-120b-a12b:free", display_name: "Nemotron 3 Super 120B" },
  { model_id: "minimax/minimax-m2.5:free", display_name: "MiniMax M2.5" },
];

const DEMO_PROMPT =
  "Explain the difference between a compiler and an interpreter to someone who has never programmed. Use an analogy.";

interface Props {
  onComplete: (result: {
    chatroomId: string;
    chatId: string;
    providers: any[];
    demoPrompt: string;
  }) => void;
}

type Step = "welcome" | "openrouter" | "custom" | "setting-up";

export function WelcomeSetup({ onComplete }: Props) {
  const [step, setStep] = useState<Step>("welcome");
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState("");

  // Custom provider state
  const [customProvider, setCustomProvider] = useState("openai");
  const [customKey, setCustomKey] = useState("");
  const [customBaseUrl, setCustomBaseUrl] = useState("");
  const [customDisplayName, setCustomDisplayName] = useState("");
  const [customModelId, setCustomModelId] = useState("");

  const handleOpenRouterSetup = async () => {
    if (!apiKey.trim()) return;
    setError("");

    setStep("setting-up");
    try {
      const result = await apiClient.quickSetup({
        api_key: apiKey.trim(),
        provider: "openrouter",
        base_url: OPENROUTER_BASE_URL,
        display_name: "OpenRouter",
        models: QUICK_START_MODELS,
        chatroom_name: "My First Comparison",
      });
      const providers = await apiClient.listProviders();
      onComplete({
        chatroomId: result.chatroom.id,
        chatId: result.chat.id,
        providers,
        demoPrompt: DEMO_PROMPT,
      });
    } catch (e: any) {
      setError(e.message || "Setup failed. Check your API key and try again.");
      setStep("openrouter");

    }
  };

  const handleCustomSetup = async () => {
    if (!customKey.trim() || !customModelId.trim()) return;
    setError("");

    setStep("setting-up");
    try {
      const result = await apiClient.quickSetup({
        api_key: customKey.trim(),
        provider: customProvider.trim(),
        base_url: customBaseUrl.trim() || null,
        display_name: customDisplayName.trim() || null,
        models: [{ model_id: customModelId.trim(), display_name: customModelId.trim() }],
        chatroom_name: "My First Comparison",
      });
      const providers = await apiClient.listProviders();
      onComplete({
        chatroomId: result.chatroom.id,
        chatId: result.chat.id,
        providers,
        demoPrompt: DEMO_PROMPT,
      });
    } catch (e: any) {
      setError(e.message || "Setup failed. Check your credentials and try again.");
      setStep("custom");

    }
  };

  if (step === "setting-up") {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="text-lg font-medium">Setting up your workspace...</div>
          <div className="text-sm text-muted-foreground">Creating provider, chatroom, and models</div>
          <div className="flex justify-center">
            <div className="h-6 w-6 border-2 border-foreground/20 border-t-foreground rounded-full animate-spin" />
          </div>
        </div>
      </div>
    );
  }

  if (step === "openrouter") {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="max-w-md w-full space-y-6">
          <div>
            <button
              onClick={() => setStep("welcome")}
              className="text-sm text-muted-foreground hover:text-foreground mb-4 inline-block"
            >
              &larr; Back
            </button>
            <h2 className="text-xl font-semibold">Connect OpenRouter</h2>
            <p className="text-sm text-muted-foreground mt-1">
              One API key for all major models. Free tier available.
            </p>
          </div>

          <div className="space-y-4">
            <ol className="text-sm space-y-2 text-muted-foreground">
              <li>
                <span className="font-medium text-foreground">1.</span>{" "}
                Go to{" "}
                <a
                  href="https://openrouter.ai/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-500 hover:underline"
                >
                  openrouter.ai/keys
                </a>{" "}
                and create an API key
              </li>
              <li>
                <span className="font-medium text-foreground">2.</span>{" "}
                Paste it below
              </li>
            </ol>

            <div>
              <Label className="text-sm">OpenRouter API Key</Label>
              <Input
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleOpenRouterSetup()}
                type="password"
                placeholder="sk-or-..."
                className="mt-1"
                autoFocus
              />
            </div>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <div className="rounded-md border border-border p-3 space-y-2">
              <p className="text-xs font-medium">Models we'll set up for you:</p>
              <div className="grid grid-cols-2 gap-1">
                {QUICK_START_MODELS.map((m) => (
                  <div key={m.model_id} className="text-xs text-muted-foreground flex items-center gap-1.5">
                    <span className={m.model_id.includes(":free") ? "text-green-500" : "text-amber-500"}>
                      {m.model_id.includes(":free") ? "free" : "paid"}
                    </span>
                    {m.display_name}
                  </div>
                ))}
              </div>
            </div>

            <Button onClick={handleOpenRouterSetup} disabled={!apiKey.trim()} className="w-full">
              Connect & Start Comparing
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (step === "custom") {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="max-w-md w-full space-y-6">
          <div>
            <button
              onClick={() => setStep("welcome")}
              className="text-sm text-muted-foreground hover:text-foreground mb-4 inline-block"
            >
              &larr; Back
            </button>
            <h2 className="text-xl font-semibold">Add Your Provider</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Connect OpenAI, Anthropic, Google, or any OpenAI-compatible API.
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <Label className="text-xs">Provider Type</Label>
              <Input value={customProvider} onChange={(e) => setCustomProvider(e.target.value)}
                placeholder="openai" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">API Key</Label>
              <Input value={customKey} onChange={(e) => setCustomKey(e.target.value)}
                type="password" placeholder="sk-..." className="h-8 text-sm mt-1" autoFocus />
            </div>
            <div>
              <Label className="text-xs">Base URL (optional)</Label>
              <Input value={customBaseUrl} onChange={(e) => setCustomBaseUrl(e.target.value)}
                placeholder="https://api.openai.com/v1" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Display Name (optional)</Label>
              <Input value={customDisplayName} onChange={(e) => setCustomDisplayName(e.target.value)}
                placeholder="My OpenAI" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Model ID</Label>
              <Input value={customModelId} onChange={(e) => setCustomModelId(e.target.value)}
                placeholder="gpt-4o" className="h-8 text-sm mt-1" />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button onClick={handleCustomSetup} disabled={!customKey.trim() || !customModelId.trim()} className="w-full">
              Connect & Start Comparing
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Welcome step
  return (
    <div className="flex-1 flex items-center justify-center p-4">
      <div className="max-w-lg w-full space-y-8 text-center">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold">Compare AI models side-by-side</h1>
          <p className="text-muted-foreground">
            Send one prompt, see how different models respond. All data stays on your machine.
          </p>
        </div>

        <div className="space-y-3 max-w-sm mx-auto">
          <Button
            onClick={() => setStep("openrouter")}
            className="w-full h-12 text-base"
            size="lg"
          >
            Get started with OpenRouter
          </Button>
          <p className="text-xs text-muted-foreground">
            One API key for Claude, GPT, Gemini, and more. Includes free models.
          </p>
        </div>

        <div className="flex items-center gap-3 max-w-sm mx-auto">
          <div className="flex-1 border-t border-border" />
          <span className="text-xs text-muted-foreground">or</span>
          <div className="flex-1 border-t border-border" />
        </div>

        <Button
          variant="outline"
          onClick={() => setStep("custom")}
          className="mx-auto"
        >
          I already have API keys
        </Button>
      </div>
    </div>
  );
}
