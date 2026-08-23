"use client";

import { useEffect, useState } from "react";

/* Reading depth.
 *
 * One control re-tunes the whole page rather than asking a reader to declare
 * who they are at the door. The same data is on the page at every depth; what
 * changes is how much apparatus is drawn around it.
 *
 *   learn  the translation leads, a couple of commentators set out the
 *          discussion, and the machinery is out of the way
 *   read   every commentator, clause by clause, original beside translation
 *   audit  adds alignment basis, support, the provenance ladder and the trace
 *
 * `read` is the default because it is the honest one: `learn` hides
 * commentators a reader did not ask to have hidden, and `audit` shows
 * machinery most readers never wanted.
 */

export type Depth = "learn" | "read" | "audit";

export const DEPTHS: Depth[] = ["learn", "read", "audit"];

const KEY = "tafahhum.depth";
const DEFAULT: Depth = "read";

function isDepth(value: unknown): value is Depth {
  return value === "learn" || value === "read" || value === "audit";
}

/** Remembered per reader, and never allowed to break the page when it cannot be.
 *
 * Storage throws outright in some contexts (private windows, embedded views,
 * browsers set to block site data), so every read and write is guarded and a
 * failure simply means the default. */
export function useDepth(): [Depth, (next: Depth) => void] {
  // Always start at the default so the server-rendered markup and the first
  // client render agree. The stored value is applied in an effect, after
  // hydration, where a mismatch cannot be a hydration error.
  const [depth, setDepth] = useState<Depth>(DEFAULT);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(KEY);
      if (isDepth(stored)) setDepth(stored);
    } catch {
      // Unreadable storage is not an error worth showing anyone.
    }
  }, []);

  const choose = (next: Depth) => {
    setDepth(next);
    try {
      window.localStorage.setItem(KEY, next);
    } catch {
      // The choice still applies for this visit; it just will not be recalled.
    }
  };

  return [depth, choose];
}
