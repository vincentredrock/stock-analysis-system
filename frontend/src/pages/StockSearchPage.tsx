import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { searchStocks, listStocks } from "@/api/stocks";
import { Search, ArrowRight } from "lucide-react";

export function StockSearchPage() {
  const [query, setQuery] = useState("");

  const searchQuery = useQuery({
    queryKey: ["stock-search", query],
    queryFn: () => searchStocks(query),
    enabled: query.length > 0,
  });

  const allQuery = useQuery({
    queryKey: ["stocks", 0, 50],
    queryFn: () => listStocks(0, 50),
    enabled: query.length === 0,
  });

  const results = query.length > 0 ? searchQuery.data : allQuery.data;
  const isLoading = query.length > 0 ? searchQuery.isLoading : allQuery.isLoading;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-primary">Stocks</h1>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search by symbol or name..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-card focus:outline-none focus:ring-2 focus:ring-accent"
        />
      </div>

      {isLoading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent" />
        </div>
      )}

      {!isLoading && results && results.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No stocks found.</p>
        </div>
      )}

      {!isLoading && results && results.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {results.map((stock) => (
            <Link
              key={stock.symbol}
              to={`/stocks/${stock.symbol}`}
              className="bg-card border border-border rounded-xl p-4 hover:shadow-md transition-shadow group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-primary">{stock.symbol}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground font-medium">
                      {stock.market}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{stock.name}</p>
                  {stock.industry && (
                    <p className="text-xs text-muted-foreground mt-1">{stock.industry}</p>
                  )}
                </div>
                <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-accent transition-colors" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
