import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { logout as apiLogout } from "@/api/auth";
import { clearTokens, getAccessToken } from "@/api/client";
import { toast } from "sonner";
import {
  Search,
  List,
  LogOut,
  TrendingUp,
  User,
} from "lucide-react";

export function Navbar() {
  const { user, logout: storeLogout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    try {
      const token = getAccessToken();
      if (token) await apiLogout(token);
    } catch {
      // ignore
    } finally {
      clearTokens();
      storeLogout();
      toast.success("Logged out successfully");
      navigate("/login");
    }
  };

  const navLinkClass = (path: string) =>
    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      location.pathname === path || location.pathname.startsWith(path + "/")
        ? "bg-accent text-accent-foreground"
        : "text-muted-foreground hover:text-primary hover:bg-muted"
    }`;

  return (
    <nav className="bg-card border-b border-border sticky top-0 z-50">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2 text-primary font-bold text-lg">
            <TrendingUp className="w-5 h-5 text-accent" />
            <span>TW Stock</span>
          </Link>

          <div className="flex items-center gap-1">
            <Link to="/stocks" className={navLinkClass("/stocks")}>
              <Search className="w-4 h-4" />
              <span className="hidden sm:inline">Stocks</span>
            </Link>
            <Link to="/watchlists" className={navLinkClass("/watchlists")}>
              <List className="w-4 h-4" />
              <span className="hidden sm:inline">Watchlists</span>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <User className="w-4 h-4" />
              <span className="hidden sm:inline">{user?.username}</span>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 text-sm text-danger hover:bg-red-50 px-3 py-2 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
