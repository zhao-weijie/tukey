import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Wrench } from "@phosphor-icons/react";
import { apiClient } from "@/lib/api";
import type { McpServer } from "@/stores/chatStore";

interface Props {
  servers: McpServer[];
  onUpdate: (servers: McpServer[]) => void;
}

export function McpServerSetup({ servers, onUpdate }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [command, setCommand] = useState("");
  const [args, setArgs] = useState("");
  const [envText, setEnvText] = useState("");

  const parseArgs = (s: string): string[] =>
    s.trim() ? s.split(/\s+/) : [];

  const parseEnv = (s: string): Record<string, string> => {
    const env: Record<string, string> = {};
    for (const line of s.split("\n")) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const eq = trimmed.indexOf("=");
      if (eq > 0) {
        env[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1).trim();
      }
    }
    return env;
  };

  const addServer = async () => {
    if (!name.trim() || !command.trim()) return;
    const s = await apiClient.createMcpServer({
      name: name.trim(),
      command: command.trim(),
      args: parseArgs(args),
      env: parseEnv(envText),
    });
    onUpdate([...servers, s]);
    setName("");
    setCommand("");
    setArgs("");
    setEnvText("");
  };

  const removeServer = async (id: string) => {
    await apiClient.deleteMcpServer(id);
    onUpdate(servers.filter((s) => s.id !== id));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger render={<Button size="sm" variant="outline" className="w-full h-7 text-xs gap-1.5" />}>
        <Wrench size={14} />
        MCP Servers ({servers.length})
      </DialogTrigger>

      <DialogContent>
        <DialogHeader>
          <DialogTitle>MCP Tool Servers</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {servers.map((s) => (
            <div key={s.id} className="flex items-center justify-between p-2 border rounded-md text-sm">
              <div className="min-w-0 flex-1">
                <div className="font-medium">{s.name}</div>
                <div className="text-xs text-muted-foreground truncate">
                  {s.command} {s.args.join(" ")}
                </div>
                {Object.keys(s.env).length > 0 && (
                  <div className="text-xs text-muted-foreground">
                    env: {Object.keys(s.env).join(", ")}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <TestMcpButton serverId={s.id} />
                <button onClick={() => removeServer(s.id)}
                  className="text-xs text-muted-foreground hover:text-destructive px-2">
                  Remove
                </button>
              </div>
            </div>
          ))}

          <div className="space-y-2 pt-2 border-t">
            <div>
              <Label className="text-xs">Name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)}
                placeholder="Exa Search" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Command</Label>
              <Input value={command} onChange={(e) => setCommand(e.target.value)}
                placeholder="npx" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Arguments (space-separated)</Label>
              <Input value={args} onChange={(e) => setArgs(e.target.value)}
                placeholder="-y @anthropic/mcp-server-exa" className="h-8 text-sm mt-1" />
            </div>
            <div>
              <Label className="text-xs">Environment Variables (KEY=VALUE, one per line)</Label>
              <Textarea value={envText} onChange={(e) => setEnvText(e.target.value)}
                rows={2} className="text-xs mt-1 font-mono"
                placeholder="EXA_API_KEY=your-key-here" />
            </div>
            <Button size="sm" onClick={addServer} className="w-full h-8">
              Add MCP Server
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function TestMcpButton({ serverId }: { serverId: string }) {
  const [status, setStatus] = useState<"idle" | "testing" | "ok" | "fail">("idle");
  const [info, setInfo] = useState("");

  const test = async () => {
    setStatus("testing");
    setInfo("");
    try {
      const res = await apiClient.testMcpServer(serverId);
      if (res.ok) {
        setStatus("ok");
        setInfo(`${res.tools.length} tool(s): ${res.tools.map((t) => t.name).join(", ")}`);
      } else {
        setStatus("fail");
        setInfo(res.error || "Unknown error");
      }
    } catch (e: any) {
      setStatus("fail");
      setInfo(e.message);
    }
  };

  return (
    <div className="flex items-center gap-1">
      <button onClick={test} disabled={status === "testing"}
        className="text-xs px-2 text-muted-foreground hover:text-foreground"
        title={info || undefined}>
        {status === "idle" && "Test"}
        {status === "testing" && "..."}
        {status === "ok" && "\u2713 OK"}
        {status === "fail" && "\u2717 Fail"}
      </button>
      {info && status === "ok" && (
        <span className="text-[10px] text-muted-foreground max-w-[200px] truncate">{info}</span>
      )}
    </div>
  );
}
