import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatRoom } from "@/components/ChatRoom";
import { WelcomeSetup } from "@/components/WelcomeSetup";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useChatStore } from "@/stores/chatStore";
import { apiClient } from "@/lib/api";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(true);
  const [showWelcome, setShowWelcome] = useState(false);
  const { setProviders, setChatrooms, setActiveChatroom, setChats, setActiveChat } = useChatStore();
  const [demoPrompt, setDemoPrompt] = useState<string | null>(null);

  // Check if this is a first-run (no providers configured)
  useEffect(() => {
    apiClient.listProviders()
      .then((p) => {
        setProviders(p);
        setShowWelcome(p.length === 0);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [setProviders]);

  const handleSetupComplete = async (result: {
    chatroomId: string;
    chatId: string;
    providers: any[];
    demoPrompt: string;
  }) => {
    setProviders(result.providers);
    // Refresh chatrooms and navigate to the new one
    const chatrooms = await apiClient.listChatrooms();
    setChatrooms(chatrooms);
    setActiveChatroom(result.chatroomId);
    const chats = await apiClient.listChats(result.chatroomId);
    setChats(chats);
    setActiveChat(result.chatId);
    setDemoPrompt(result.demoPrompt);
    setShowWelcome(false);
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        <div className="h-6 w-6 border-2 border-foreground/20 border-t-foreground rounded-full animate-spin" />
      </div>
    );
  }

  if (showWelcome) {
    return (
      <TooltipProvider>
        <div className="flex h-screen overflow-hidden bg-background text-foreground">
          <WelcomeSetup onComplete={handleSetupComplete} />
        </div>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <div className="flex h-screen overflow-hidden bg-background text-foreground">
        <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen((o) => !o)} />
        <ChatRoom demoPrompt={demoPrompt} onDemoPromptUsed={() => setDemoPrompt(null)} />
      </div>
    </TooltipProvider>
  );
}
