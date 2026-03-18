import { useEffect, useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { ProviderSetup } from "./ProviderSetup";

export function Sidebar() {
  const { rooms, setRooms, activeRoomId, setActiveRoom, providers, setProviders } = useChatStore();
  const [newName, setNewName] = useState("");

  useEffect(() => {
    apiClient.listRooms().then(setRooms).catch(console.error);
    apiClient.listProviders().then(setProviders).catch(console.error);
  }, [setRooms, setProviders]);

  const createRoom = async () => {
    const name = newName.trim() || "New Chat";
    const room = await apiClient.createRoom(name);
    setRooms([...rooms, room]);
    setActiveRoom(room.id);
    setNewName("");
  };

  const deleteRoom = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await apiClient.deleteRoom(id);
    setRooms(rooms.filter((r) => r.id !== id));
    if (activeRoomId === id) setActiveRoom(null);
  };

  return (
    <div className="w-64 border-r border-border flex flex-col h-full bg-sidebar">
      <div className="p-3 font-semibold text-lg text-sidebar-foreground">
        Tukey
      </div>
      <Separator />
      <div className="p-2 flex gap-1">
        <Input
          placeholder="Room name..."
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && createRoom()}
          className="text-sm h-8"
        />
        <Button size="sm" onClick={createRoom} className="h-8 px-3 shrink-0">
          +
        </Button>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-1 space-y-0.5">
          {rooms.map((room) => (
            <div
              key={room.id}
              onClick={() => setActiveRoom(room.id)}
              className={`group flex items-center justify-between px-2 py-1.5 rounded-md cursor-pointer text-sm ${
                activeRoomId === room.id
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/50"
              }`}
            >
              <span className="truncate">{room.name}</span>
              <button
                onClick={(e) => deleteRoom(room.id, e)}
                className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive text-xs px-1"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </ScrollArea>
      <Separator />
      <div className="p-2">
        <ProviderSetup providers={providers} onUpdate={setProviders} />
      </div>
    </div>
  );
}
