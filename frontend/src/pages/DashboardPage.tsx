import { Link } from "react-router-dom";
import { TrendingUp, Search, List } from "lucide-react";

export function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="text-center py-12">
        <h1 className="text-3xl font-bold text-primary mb-3">Taiwan Stock Market Platform</h1>
        <p className="text-muted-foreground max-w-xl mx-auto">
          Search stocks, view real-time quotes, analyze historical prices with candlestick charts, and manage your personal watchlists.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link
          to="/stocks"
          className="group bg-card border border-border rounded-xl p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-50 rounded-lg group-hover:bg-blue-100 transition-colors">
              <Search className="w-5 h-5 text-accent" />
            </div>
            <h2 className="text-lg font-semibold text-primary">Search Stocks</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Find Taiwan stocks by symbol or company name and view real-time quotes.
          </p>
        </Link>

        <Link
          to="/watchlists"
          className="group bg-card border border-border rounded-xl p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-50 rounded-lg group-hover:bg-blue-100 transition-colors">
              <List className="w-5 h-5 text-accent" />
            </div>
            <h2 className="text-lg font-semibold text-primary">Your Watchlists</h2>
          </div>
          <p className="text-sm text-muted-foreground">
            Organize your favorite stocks and monitor live price changes in one place.
          </p>
        </Link>
      </div>

      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-semibold text-primary">Market Overview</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Use the navigation above to explore TWSE and TPEx listed stocks. All prices are delayed data sourced from twstock.
        </p>
      </div>
    </div>
  );
}
