import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { ChatRoom } from "@/components/ChatRoom";

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen((o) => !o)} />
      <ChatRoom />
    </div>
  );
}
