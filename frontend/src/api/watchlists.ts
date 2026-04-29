import { apiClient } from "./client";
import type {
  Watchlist,
  WatchlistCreate,
  WatchlistWithQuotes,
  WatchlistItemCreate,
  MessageResponse,
} from "@/types";

export async function listWatchlists(): Promise<Watchlist[]> {
  const res = await apiClient.get<Watchlist[]>("/watchlists");
  return res.data;
}

export async function createWatchlist(data: WatchlistCreate): Promise<Watchlist> {
  const res = await apiClient.post<Watchlist>("/watchlists", data);
  return res.data;
}

export async function getWatchlist(id: number): Promise<Watchlist> {
  const res = await apiClient.get<Watchlist>(`/watchlists/${id}`);
  return res.data;
}

export async function deleteWatchlist(id: number): Promise<MessageResponse> {
  const res = await apiClient.delete<MessageResponse>(`/watchlists/${id}`);
  return res.data;
}

export async function addWatchlistItem(
  watchlistId: number,
  data: WatchlistItemCreate
): Promise<Watchlist> {
  const res = await apiClient.post<Watchlist>(`/watchlists/${watchlistId}/items`, data);
  return res.data;
}

export async function removeWatchlistItem(
  watchlistId: number,
  symbol: string
): Promise<Watchlist> {
  const res = await apiClient.delete<Watchlist>(`/watchlists/${watchlistId}/items/${symbol}`);
  return res.data;
}

export async function getWatchlistQuotes(watchlistId: number): Promise<WatchlistWithQuotes> {
  const res = await apiClient.get<WatchlistWithQuotes>(`/watchlists/${watchlistId}/quotes`);
  return res.data;
}
