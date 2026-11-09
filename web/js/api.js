let csrfToken = null;

export class ApiError extends Error {
  constructor(status, error) {
    super(error.message);
    this.name = "ApiError";
    this.status = status;
    this.code = error.code;
    this.details = error.details;
  }
}

export async function request(path, { method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  const multipart = body instanceof FormData;
  if (body !== undefined && !multipart) headers["Content-Type"] = "application/json";
  if (method !== "GET" && csrfToken) headers["X-CSRF-Token"] = csrfToken;
  const response = await fetch(`/api${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : multipart ? body : JSON.stringify(body),
    credentials: "same-origin",
    signal,
  });
  const payload = await response.json();
  if (!response.ok) throw new ApiError(response.status, payload.error);
  if (payload.data?.csrf_token) csrfToken = payload.data.csrf_token;
  return payload.data;
}

export const authApi = {
  session: (signal) => request("/auth/session", { signal }),
  register: (credentials, signal) => request("/auth/register", { method: "POST", body: credentials, signal }),
  login: (credentials, signal) => request("/auth/login", { method: "POST", body: credentials, signal }),
  logout: () => request("/auth/logout", { method: "POST" }),
};

export const adminApi = {
  users: (offset = 0, signal) => request(`/admin/users?limit=25&offset=${offset}`, { signal }),
  products: (query, signal) => request(`/admin/products?${query}`, { signal }),
  review: (id, body, signal) => request(`/admin/products/${id}/review`, { method: "POST", body, signal }),
  block: (id, body, signal) => request(`/admin/products/${id}/take-down`, { method: "POST", body, signal }),
  reopen: (id, version, signal) => request(`/admin/products/${id}/reopen`, { method: "POST", body: { version }, signal }),
};

export const productApi = {
  options: (signal) => request("/products/options", { signal }),
  search: (query, signal) => request(`/products?${query}`, { signal }),
  mine: (query, signal) => request(`/products/mine?${query}`, { signal }),
  detail: (id, signal) => request(`/products/${id}`, { signal }),
  create: (body, signal) => request("/products", { method: "POST", body, signal }),
  update: (id, body, signal) => request(`/products/${id}`, { method: "PATCH", body, signal }),
  submit: (id, version, signal) => request(`/products/${id}/submit`, { method: "POST", body: { version }, signal }),
  takeDown: (id, version, signal) => request(`/products/${id}/take-down`, { method: "POST", body: { version }, signal }),
  rectify: (id, body, signal) => request(`/products/${id}/rectification`, { method: "POST", body, signal }),
  upload: (file, signal) => {
    const body = new FormData();
    body.append("file", file);
    return request("/files", { method: "POST", body, signal });
  },
};

export const orderApi = {
  place: (body, signal) => request("/orders", { method: "POST", body, signal }),
  list: (query, signal) => request(`/orders?${query}`, { signal }),
  detail: (id, signal) => request(`/orders/${id}`, { signal }),
  action: (id, action, signal) => request(`/orders/${id}/${action}`, { method: "POST", body: {}, signal }),
};

export const socialApi = {
  open: (body, signal) => request("/conversations", { method: "POST", body, signal }),
  conversations: (query, signal) => request(`/conversations?${query}`, { signal }),
  messages: (id, query, signal) => request(`/conversations/${id}/messages?${query}`, { signal }),
  send: (id, body, signal) => request(`/conversations/${id}/messages`, { method: "POST", body, signal }),
  evaluate: (id, body, signal) => request(`/orders/${id}/evaluations`, { method: "POST", body, signal }),
  orderEvaluations: (id, signal) => request(`/orders/${id}/evaluations`, { signal }),
  productEvaluations: (id, query, signal) => request(`/products/${id}/evaluations?${query}`, { signal }),
  userEvaluations: (id, query, signal) => request(`/users/${id}/evaluations?${query}`, { signal }),
  notifications: (query, signal) => request(`/notifications?${query}`, { signal }),
  read: (id, signal) => request(`/notifications/${id}/read`, { method: "POST", body: {}, signal }),
  summary: (query, signal) => request(`/me/summary?${query}`, { signal }),
  logs: (query, admin, signal) => request(`/${admin ? "admin" : "me"}/logs?${query}`, { signal }),
  todos: (signal) => request("/admin/todos", { signal }),
};

export const caseApi = {
  submit: (body, signal) => request("/cases", { method: "POST", body, signal }),
  list: (query, admin, signal) => request(`/${admin ? "admin/" : ""}cases?${query}`, { signal }),
  detail: (id, signal) => request(`/cases/${id}`, { signal }),
  comment: (id, body, signal) => request(`/cases/${id}/comments`, { method: "POST", body, signal }),
  context: (id, query, signal) => request(`/cases/${id}/context?${query}`, { signal }),
  claim: (id, signal) => request(`/admin/cases/${id}/claim`, { method: "POST", body: {}, signal }),
  resolve: (id, body, signal) => request(`/admin/cases/${id}/resolve`, { method: "POST", body, signal }),
};
