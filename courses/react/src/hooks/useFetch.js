// READ FIRST: Understand the patterns and design decisions behind this hook:
//   - src/lessons/02-custom-hooks/01-custom-hooks-fundamentals.md
//       Sections: "Return Value Contracts", "Real-World Custom Hook Implementations"
//   - src/lessons/02-custom-hooks/02-custom-hooks-testing-and-advanced.md
//       Sections: "Building a Mini Data-Fetching Library", "Testing Custom Hooks"
//
// ALSO SEE:
//   - src/lessons/02-custom-hooks/CustomHooksDemo.jsx — run this to test your implementation interactively
//   - src/hooks/usePrevious.js — a simpler custom hook exercise to try first
//
// KEY CONCEPTS:
//   - AbortController for race condition handling (what happens when url changes mid-fetch?)
//   - The "cancelled" boolean flag as a second safety net alongside abort
//   - useCallback for a stable refetch identity so consumers can safely list it in deps
//   - Return shape { data, error, isLoading, refetch } follows the tuple-or-object contract
//     described in 01-custom-hooks-fundamentals.md

import { useState, useEffect, useCallback } from 'react';

/**
 * EXERCISE: Implement useFetch
 *
 * A reusable data fetching hook with proper race condition handling.
 *
 * Requirements:
 * 1. Fetch data when URL changes
 * 2. Return { data, error, isLoading, refetch }
 * 3. Handle race conditions (if URL changes mid-fetch, ignore stale response)
 * 4. Clean up properly on unmount
 * 5. Don't set error state for aborted requests
 *
 * Example usage:
 *   const { data, error, isLoading, refetch } = useFetch('/api/users/1');
 */

export function useFetch(url) {
  const [fetchIndex, setFetchIndex] = useState(0);
  const [state, setState] = useState({
    data: null,
    error: null,
    status: 'loading', // 'loading' | 'success' | 'error'
  });

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    fetch(url, { signal: controller.signal })
      .then(res => res.json())
      .then(data => {
        if (!cancelled) {
          setState({ data, error: null, status: 'success' });
        }
      })
      .catch(err => {
        if (!cancelled && err.name !== 'AbortError') {
          setState({ data: null, error: err.message, status: 'error' });
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [url, fetchIndex]);

  // Reset to loading when url or fetchIndex changes
  const isLoading = state.status === 'loading';

  const refetch = useCallback(() => {
    setState({ data: null, error: null, status: 'loading' });
    setFetchIndex(i => i + 1);
  }, []);

  return {
    data: state.data,
    error: state.error,
    isLoading,
    refetch,
  };
}
