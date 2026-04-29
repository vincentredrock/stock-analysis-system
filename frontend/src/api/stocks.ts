import { apiClient } from "./client";
import type {
  Stock,
  StockSearchResult,
  StockPrice,
  StockQuote,
  StockSyncResult,
  StockSyncStatus,
} from "@/types";

export async function searchStocks(q: string): Promise<StockSearchResult[]> {
  const res = await apiClient.get<StockSearchResult[]>("/stocks/search", {
    params: { q },
  });
  return res.data;
}

export async function listStocks(skip = 0, limit = 100): Promise<Stock[]> {
  const res = await apiClient.get<Stock[]>("/stocks", { params: { skip, limit } });
  return res.data;
}

export async function getStockQuote(symbol: string): Promise<StockQuote> {
  const res = await apiClient.get<StockQuote>(`/stocks/${symbol}/quote`);
  return res.data;
}

export async function getStockHistory(
  symbol: string,
  start?: string,
  end?: string
): Promise<StockPrice[]> {
  const res = await apiClient.get<StockPrice[]>(`/stocks/${symbol}/history`, {
    params: { start, end },
  });
  return res.data;
}

export async function getStockSyncStatus(symbol: string): Promise<StockSyncStatus> {
  const res = await apiClient.get<StockSyncStatus>(`/stocks/${symbol}/sync-status`);
  return res.data;
}

export async function syncStockPrices(
  symbol: string,
  start?: string,
  end?: string
): Promise<StockSyncResult> {
  const res = await apiClient.post<StockSyncResult>(`/stocks/${symbol}/sync`, null, {
    params: { start, end },
  });
  return res.data;
}
