import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Download, FolderOpen, Plus, Trash } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { ProviderSetup } from "@/components/ProviderSetup";
import { McpServerSetup } from "@/components/McpServerSetup";
import { SearchDialog } from "@/components/SearchDialog";
import { DataDirDialog } from "@/components/DataDirDialog";
import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useTukeyStore, type RunChain } from "@/stores/tukeyStore";

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window !== "undefined" ? window.matchMedia(query).matches : false,
  );
  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [query]);
  return matches;
}

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
  providerDialogOpen?: boolean;
  onProviderDialogOpenChange?: (open: boolean) => void;
}

function downloadJson(data: any, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function Sidebar({ open, onToggle, providerDialogOpen, onProviderDialogOpenChange }: SidebarProps) {
  const isSmallScreen = useMediaQuery("(max-width: 767px)");
  const {
    tasks,
    configSets,
    runChains,
    activeChainId,
    setActiveChainId,
    loadWorkspace,
    loadChainDetail,
    providers,
    setProviders,
    mcpServers,
    setMcpServers,
    resetActive,
  } = useTukeyStore();
  const [newName, setNewName] = useState("");
  const [dataDir, setDataDir] = useState("");
  const [dataDirDialogOpen, setDataDirDialogOpen] = useState(false);

  useEffect(() => {
    apiClient.getHealth().then((h) => setDataDir(h.data_dir)).catch(console.error);
  }, []);

  async function createChain() {
    const configSet = configSets[0] || await apiClient.createConfigSet({ name: "Default Config Set" });
    const name = newName.trim() || "New Run Chain";
    const chain = await apiClient.createRunChain({
      name,
      default_config_set_id: configSet.id,
    });
    setNewName("");
    await loadWorkspace();
    setActiveChainId(chain.id);
    await loadChainDetail(chain.id);
  }

  async function selectChain(chainId: string) {
    setActiveChainId(chainId);
    await loadChainDetail(chainId);
    if (isSmallScreen) onToggle();
  }

  async function archiveChain(chain: RunChain, e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm("Archive this run chain? Runs remain on disk.")) return;
    await apiClient.updateRunChain(chain.id, { archived: true });
    if (activeChainId === chain.id) resetActive();
    await loadWorkspace();
  }

  async function exportChain(chain: RunChain, e: React.MouseEvent) {
    e.stopPropagation();
    const data = await apiClient.exportRunChain(chain.id);
    const name = chain.name.replace(/\s+/g, "_").toLowerCase() || chain.id.slice(0, 8);
    downloadJson(data, `tukey-run-chain-${name}.json`);
  }

  return (
    <>
      {isSmallScreen && open && (
        <div className="fixed inset-0 z-30 bg-black/40" onClick={onToggle} />
      )}
      <div
        className={cn(
          "border-r border-border flex h-full flex-col bg-sidebar transition-all duration-200",
          isSmallScreen
            ? cn("fixed inset-y-0 left-0 z-40 w-72", open ? "translate-x-0" : "-translate-x-full")
            : cn("relative", open ? "w-72" : "w-12"),
        )}
      >
        <button
          onClick={onToggle}
          className={cn(
            "absolute top-4 z-20 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-sidebar text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground",
            isSmallScreen ? "-right-6" : "-right-2.5",
          )}
          title={open ? "Collapse sidebar" : "Expand sidebar"}
        >
          {open ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>

        {!open && !isSmallScreen && (
          <div className="flex items-center justify-center p-3">
            <img src="/logos/tukey-light-none.svg" alt="Tukey" className="h-6 w-6" />
          </div>
        )}

        {(open || isSmallScreen) && (
          <>
            <div className="flex items-center justify-between p-3">
              <img src="/logos/tukey-light-right.svg" alt="Tukey" className="h-8 w-auto" />
              <SearchDialog />
            </div>
            <Separator />
            <div className="space-y-2 p-2">
              <div className="flex gap-1">
                <Input
                  placeholder="Run chain name..."
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && createChain()}
                  className="h-8 text-sm"
                />
                <Button size="icon" onClick={createChain} className="h-8 w-8 shrink-0" title="New run chain">
                  <Plus size={16} />
                </Button>
              </div>
            </div>
            <ScrollArea className="flex-1 min-h-0">
              <div className="space-y-4 p-2">
                {tasks.length > 0 && (
                  <div>
                    <div className="px-2 pb-1 text-[11px] font-medium uppercase text-muted-foreground">Tasks</div>
                    {tasks.map((task) => (
                      <div key={task.id} className="rounded-md px-2 py-1.5 text-xs text-sidebar-foreground">
                        <div className="truncate font-medium">{task.name}</div>
                        {task.description && <div className="truncate text-muted-foreground">{task.description}</div>}
                      </div>
                    ))}
                  </div>
                )}
                <div>
                  <div className="px-2 pb-1 text-[11px] font-medium uppercase text-muted-foreground">Run Chains</div>
                  <div className="space-y-0.5">
                    {runChains.map((chain) => (
                      <button
                        key={chain.id}
                        onClick={() => selectChain(chain.id)}
                        className={cn(
                          "group flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm",
                          activeChainId === chain.id
                            ? "bg-sidebar-accent text-sidebar-accent-foreground"
                            : "text-sidebar-foreground hover:bg-sidebar-accent/50",
                        )}
                      >
                        <span className="min-w-0 truncate">{chain.name}</span>
                        <span className="flex shrink-0 items-center gap-0.5 opacity-0 group-hover:opacity-100">
                          <span className="rounded p-1 text-muted-foreground hover:text-foreground" onClick={(e) => exportChain(chain, e)} title="Export">
                            <Download size={13} />
                          </span>
                          <span className="rounded p-1 text-muted-foreground hover:text-destructive" onClick={(e) => archiveChain(chain, e)} title="Archive">
                            <Trash size={13} />
                          </span>
                        </span>
                      </button>
                    ))}
                    {runChains.length === 0 && (
                      <div className="px-2 py-3 text-xs text-muted-foreground">No run chains yet</div>
                    )}
                  </div>
                </div>
              </div>
            </ScrollArea>
            <Separator />
            <div className="space-y-1.5 p-2">
              <ProviderSetup
                providers={providers}
                onUpdate={setProviders}
                externalOpen={providerDialogOpen}
                onExternalOpenChange={onProviderDialogOpenChange}
              />
              <McpServerSetup servers={mcpServers} onUpdate={setMcpServers} />
              {dataDir && (
                <button
                  className="flex w-full items-center gap-1.5 rounded-md px-1 py-0.5 text-left text-[10px] text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                  title={dataDir}
                  onClick={() => setDataDirDialogOpen(true)}
                >
                  <FolderOpen size={12} className="shrink-0" />
                  <span className="truncate">{dataDir}</span>
                </button>
              )}
            </div>
          </>
        )}
      </div>
      <DataDirDialog
        open={dataDirDialogOpen}
        onOpenChange={setDataDirDialogOpen}
        currentDir={dataDir}
        onSwitch={async (newDir) => {
          setDataDir(newDir);
          resetActive();
          await loadWorkspace();
        }}
      />
    </>
  );
}
