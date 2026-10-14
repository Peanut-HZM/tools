/**
 * 个人 API Token API 客户端
 * 路径统一定义于此（客户端路径 DRY 规则），页面组件不写 inline URL
 */
import { API_BASE_URL } from '../config/api';
import { authedFetch } from './http';

const TOKENS_API_URL = `${API_BASE_URL}/user-tokens`;

export interface UserToken {
  id: string;
  name: string;
  token_prefix: string;
  created_at: string;
  last_used_at?: string | null;
  expires_at?: string | null;
  revoked: boolean;
}

export interface UserTokenCreated extends UserToken {
  /** 明文 token，仅创建响应返回一次 */
  token: string;
}

export interface CreateUserTokenInput {
  name: string;
  expiresDays?: number;
}

async function parse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const detail = await resp.text();
    throw new Error(`请求失败 (${resp.status}): ${detail}`);
  }
  return resp.json() as Promise<T>;
}

export const userTokenApi = {
  list: (): Promise<UserToken[]> => authedFetch(TOKENS_API_URL).then(parse<UserToken[]>),

  create: ({ name, expiresDays }: CreateUserTokenInput): Promise<UserTokenCreated> =>
    authedFetch(TOKENS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, expires_days: expiresDays ?? null }),
    }).then(parse<UserTokenCreated>),

  revoke: async (id: string): Promise<void> => {
    const resp = await authedFetch(`${TOKENS_API_URL}/${id}`, { method: 'DELETE' });
    if (!resp.ok) throw new Error(`撤销失败 (${resp.status})`);
  },
};
