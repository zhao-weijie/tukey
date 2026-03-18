import { Sidebar } from "@/components/Sidebar";
import { ChatRoom } from "@/components/ChatRoom";

export default function App() {
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <ChatRoom />
    </div>
  );
}
