/// <reference types="vitest/globals" />

/**
 * Tests for NavSectionBlock active-detection logic (commit e040629).
 *
 * Tests the real `isItemActive` function exported from index.tsx,
 * not a re-implementation. This ensures the test breaks if the
 * source logic changes.
 */
import { isItemActive } from '../index'

// ── NAV items replicated from AppShell/index.tsx ─────────────────────────
const NAV_ITEMS = {
  dashboard: { to: '/dashboard', end: true },
  scanResults: { to: '/scan-results' },
  changelog: { to: '/changelog' },
  schools: { to: '/schools' },
  gapClosure: { to: '/gap-closure' },
  gapCreation: { to: '/gap-creation' },
  proposals: { to: '/proposals' },
  courses: { to: '/courses' },
  import: { to: '/import' },
  archives: { to: '/archives' },
}

describe('isItemActive – matchPath active detection', () => {
  // ── 1. Exact match (end: true) ──────────────────────────────────────────
  describe('exact match (end: true)', () => {
    it('matches when currentPath equals the item path', () => {
      expect(isItemActive(NAV_ITEMS.dashboard, '/dashboard')).toBe(true)
    })

    it('does NOT match when currentPath is a different top-level path', () => {
      expect(isItemActive(NAV_ITEMS.dashboard, '/scan-results')).toBe(false)
    })

    it('does NOT match when currentPath is a sub-path of a similar name', () => {
      expect(isItemActive(NAV_ITEMS.dashboard, '/dashboard-edit')).toBe(false)
    })
  })

  // ── 2. Prefix match (sub-route /*) ──────────────────────────────────────
  describe('prefix match (/* wildcard)', () => {
    it('matches the exact path (no trailing slash)', () => {
      expect(isItemActive(NAV_ITEMS.scanResults, '/scan-results')).toBe(true)
    })

    it('matches a sub-route under the item path', () => {
      expect(isItemActive(NAV_ITEMS.gapClosure, '/gap-closure/42')).toBe(true)
      expect(isItemActive(NAV_ITEMS.courses, '/courses/new')).toBe(true)
    })

    it('matches deeply nested sub-routes', () => {
      expect(isItemActive(NAV_ITEMS.archives, '/archives/2026/01')).toBe(true)
    })
  })

  // ── 3. Edge cases – the startsWith bug ─────────────────────────────────
  describe('edge cases (startsWith anti-pattern)', () => {
    it('does NOT match a path that merely starts with the target prefix', () => {
      // startsWith('/gap-closure') would falsely match '/gap-closure-extra'
      expect(isItemActive(NAV_ITEMS.gapClosure, '/gap-closure-extra')).toBe(false)
    })

    it('does NOT match a path that starts with a substring collision', () => {
      // startsWith('/import') would falsely match '/import-export'
      expect(isItemActive(NAV_ITEMS.import, '/import-export')).toBe(false)
    })

    it('does NOT match an unrelated path', () => {
      expect(isItemActive(NAV_ITEMS.schools, '/dashboard')).toBe(false)
    })

    it('does NOT match empty string when item has a path', () => {
      expect(isItemActive(NAV_ITEMS.schools, '')).toBe(false)
    })
  })
})

