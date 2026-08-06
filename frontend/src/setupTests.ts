import '@testing-library/jest-dom/vitest'

// jsdom doesn't implement ResizeObserver, which @reactflow/core requires at mount
// time — without this polyfill, any test that renders ProcessMapView (directly or
// via App) throws "ResizeObserver is not defined" from inside the library, not
// from anything this project's own code does.
class ResizeObserverPolyfill {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// Cast rather than @ts-expect-error: whether this global is "already declared"
// depends on which tsconfig (app vs. build) is doing the checking, so a fixed
// expect-error directive is unreliable — the cast works under both.
;(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverPolyfill
