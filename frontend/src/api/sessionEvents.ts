// Lets plain API modules (outside React) notify AuthContext that the
// session is no longer valid, without each call site doing its own
// localStorage cleanup + hard page reload.
let handler: (() => void) | null = null

export function registerSessionExpiredHandler(fn: () => void) {
  handler = fn
}

export function triggerSessionExpired() {
  handler?.()
}
