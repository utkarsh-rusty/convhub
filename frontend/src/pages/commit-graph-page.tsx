import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Network } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { conversationApi } from "@/lib/api";
import { CommitDetailDrawer } from "@/components/conversation/commit-detail-drawer";
import { CommitGraphView } from "@/components/conversation/commit-graph-view";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export function CommitGraphPage() {
  const { conversationId } = useParams();
  const [selectedHash, setSelectedHash] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [author, setAuthor] = useState("");
  const [provider, setProvider] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [searchApplied, setSearchApplied] = useState({
    q: "",
    author: "",
    provider: "",
    date_from: "",
    date_to: "",
  });

  const { data: graph, isLoading, isError } = useQuery({
    queryKey: ["commit-graph", conversationId],
    queryFn: () => conversationApi.getCommitGraph(conversationId!),
    enabled: Boolean(conversationId),
  });

  const { data: searchResults } = useQuery({
    queryKey: ["commit-search", conversationId, searchApplied],
    queryFn: () => conversationApi.searchCommits(conversationId!, searchApplied),
    enabled: Boolean(
      conversationId &&
        (searchApplied.q ||
          searchApplied.author ||
          searchApplied.provider ||
          searchApplied.date_from ||
          searchApplied.date_to),
    ),
  });

  const highlightQuery = useMemo(() => {
    if (searchResults?.results.length) {
      return searchApplied.q || searchApplied.author || searchApplied.provider;
    }
    return query;
  }, [searchResults, searchApplied, query]);

  const filteredGraph = useMemo(() => {
    if (!graph) {
      return graph;
    }
    if (!searchResults?.results.length) {
      return graph;
    }
    const allowed = new Set(searchResults.results.map((item) => item.commit_hash));
    return {
      nodes: graph.nodes.filter((node) => allowed.has(node.commit_hash)),
      edges: graph.edges.filter(
        (edge) => allowed.has(edge.source) && allowed.has(edge.target),
      ),
    };
  }, [graph, searchResults]);

  if (!conversationId) {
    return null;
  }

  return (
    <div className="relative flex min-h-0 flex-1 flex-col px-4 py-4 sm:px-6">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to={`/c/${conversationId}`}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="flex items-center gap-2 text-xl font-semibold">
            <Network className="h-5 w-5" />
            Commit Graph
          </h1>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Git-style history across this conversation family.
          </p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link to={`/c/${conversationId}/branches`}>Branch manager</Link>
        </Button>
      </div>

      <form
        className="mb-4 grid gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-card)] p-3 sm:grid-cols-5"
        onSubmit={(event) => {
          event.preventDefault();
          setSearchApplied({
            q: query.trim(),
            author: author.trim(),
            provider: provider.trim(),
            date_from: dateFrom,
            date_to: dateTo,
          });
        }}
      >
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Title, message text..."
          className="h-8 text-xs"
        />
        <Input
          value={author}
          onChange={(event) => setAuthor(event.target.value)}
          placeholder="Author"
          className="h-8 text-xs"
        />
        <Input
          value={provider}
          onChange={(event) => setProvider(event.target.value)}
          placeholder="Provider"
          className="h-8 text-xs"
        />
        <Input
          type="date"
          value={dateFrom}
          onChange={(event) => setDateFrom(event.target.value)}
          className="h-8 text-xs"
        />
        <div className="flex gap-2">
          <Input
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
            className="h-8 text-xs"
          />
          <Button type="submit" size="sm" className="h-8 shrink-0 text-xs">
            Search
          </Button>
        </div>
      </form>

      {isLoading ? (
        <Skeleton className="h-80 w-full" />
      ) : isError || !filteredGraph ? (
        <p className="text-sm text-[var(--color-muted-foreground)]">Unable to load commit graph.</p>
      ) : (
        <CommitGraphView
          graph={filteredGraph}
          selectedHash={selectedHash}
          searchQuery={highlightQuery}
          onSelectCommit={(hash) => {
            setSelectedHash(hash);
            setDrawerOpen(true);
          }}
        />
      )}

      {drawerOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/20"
          aria-label="Close commit details"
          onClick={() => setDrawerOpen(false)}
        />
      ) : null}
      <CommitDetailDrawer
        commitHash={selectedHash}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}
