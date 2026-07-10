import type { Adapter, AdapterUser, VerificationToken } from "next-auth/adapters";
import * as fs from "fs";

const STORE_PATH = "/tmp/agentworthy-nextauth-store.json";

type Store = {
  users: AdapterUser[];
  verificationTokens: VerificationToken[];
};

function loadStore(): Store {
  try {
    return JSON.parse(fs.readFileSync(STORE_PATH, "utf8")) as Store;
  } catch {
    return { users: [], verificationTokens: [] };
  }
}

function saveStore(store: Store): void {
  fs.writeFileSync(STORE_PATH, JSON.stringify(store));
}

/** Minimal adapter for Email magic links in dev (JWT sessions, no persistent users). */
export function createDevAuthAdapter(): Adapter {
  return {
    async createUser(user) {
      const store = loadStore();
      const id = crypto.randomUUID();
      const created: AdapterUser = { ...user, id, emailVerified: user.emailVerified ?? null };
      store.users.push(created);
      saveStore(store);
      return created;
    },
    async getUser(id) {
      return loadStore().users.find((u) => u.id === id) ?? null;
    },
    async getUserByEmail(email) {
      return loadStore().users.find((u) => u.email === email) ?? null;
    },
    async getUserByAccount() {
      return null;
    },
    async updateUser(user) {
      const store = loadStore();
      const idx = store.users.findIndex((u) => u.id === user.id);
      if (idx === -1) throw new Error("User not found");
      store.users[idx] = { ...store.users[idx], ...user };
      saveStore(store);
      return store.users[idx];
    },
    async deleteUser() {},
    async linkAccount() {
      return undefined;
    },
    async unlinkAccount() {},
    async createSession() {
      throw new Error("Sessions use JWT strategy");
    },
    async getSessionAndUser() {
      return null;
    },
    async updateSession() {
      throw new Error("Sessions use JWT strategy");
    },
    async deleteSession() {},
    async createVerificationToken(token) {
      const store = loadStore();
      store.verificationTokens.push(token);
      saveStore(store);
      if (process.env.NODE_ENV !== "production") {
        const base = process.env.NEXTAUTH_URL || "http://localhost:3000";
        const url = `${base}/api/auth/callback/email?callbackUrl=${encodeURIComponent(`${base}/dashboard`)}&token=${token.token}&email=${encodeURIComponent(token.identifier)}`;
        try {
          fs.writeFileSync("/tmp/agentworthy-magic-link.txt", url);
        } catch {
          // ignore
        }
      }
      return token;
    },
    async useVerificationToken({ identifier, token }) {
      const store = loadStore();
      const idx = store.verificationTokens.findIndex(
        (t) => t.identifier === identifier && t.token === token
      );
      if (idx === -1) return null;
      const [found] = store.verificationTokens.splice(idx, 1);
      saveStore(store);
      return found;
    },
  };
}
