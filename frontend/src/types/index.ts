export interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface Stock {
  id: number;
  symbol: string;
  name: string;
  market: "TWSE" | "TPEx";
  industry?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StockSearchResult {
  symbol: string;
  name: string;
  market: string;
  industry?: string | null;
}

export interface StockPrice {
  date: string;
  open_price: string;
  high_price: string;
  low_price: string;
  close_price: string;
  volume: number;
  change?: string | null;
  change_percent?: string | null;
}

export interface StockQuote {
  symbol: string;
  name: string;
  price: string;
  open: string;
  high: string;
  low: string;
  close?: string | null;
  volume: number;
  change?: string | null;
  change_percent?: string | null;
  last_updated: string;
}

export interface StockSyncStatus {
  symbol: string;
  status: string;
  synced_from?: string | null;
  synced_to?: string | null;
  last_attempt_at?: string | null;
  last_success_at?: string | null;
  last_error?: string | null;
  records_upserted: number;
}

export interface StockSyncResult {
  message: string;
  symbol: string;
  start: string;
  end: string;
  records_upserted: number;
  records_skipped: number;
  months_requested: number;
}

export interface Watchlist {
  id: number;
  name: string;
  user_id: number;
  items: Stock[];
  created_at: string;
  updated_at: string;
}

export interface WatchlistCreate {
  name: string;
}

export interface WatchlistWithQuotes {
  id: number;
  name: string;
  quotes: StockQuote[];
}

export interface WatchlistItemCreate {
  symbol: string;
}

export interface MessageResponse {
  message: string;
}
