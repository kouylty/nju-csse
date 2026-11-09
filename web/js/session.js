import { authApi } from "./api.js";

let value = { user: null, expires_at: null };
const subscribers = new Set();

function update(next) {
  value = next;
  for (const subscriber of subscribers) subscriber(value);
  return value;
}

export const session = {
  get current() { return value; },
  async refresh(signal) { return update(await authApi.session(signal)); },
  async login(credentials, signal) { return update(await authApi.login(credentials, signal)); },
  async register(credentials, signal) {
    await authApi.register(credentials, signal);
    return this.login(credentials, signal);
  },
  async logout() { return update(await authApi.logout()); },
  subscribe(callback) {
    subscribers.add(callback);
    return () => subscribers.delete(callback);
  },
};
