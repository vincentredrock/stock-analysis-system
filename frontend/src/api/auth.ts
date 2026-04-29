import { apiClient } from "./client";
import type {
  LoginRequest,
  RegisterRequest,
  TokenPair,
  User,
  MessageResponse,
} from "@/types";

export async function login(data: LoginRequest): Promise<TokenPair> {
  const res = await apiClient.post<TokenPair>("/auth/login", data);
  return res.data;
}

export async function register(data: RegisterRequest): Promise<MessageResponse> {
  const res = await apiClient.post<MessageResponse>("/auth/register", data);
  return res.data;
}

export async function logout(token: string): Promise<MessageResponse> {
  const res = await apiClient.post<MessageResponse>("/auth/logout", null, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return res.data;
}

export async function getMe(): Promise<User> {
  const res = await apiClient.get<User>("/auth/me");
  return res.data;
}
