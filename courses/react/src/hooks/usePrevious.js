// READ FIRST: Understand the design patterns and alternative approaches for this hook:
//   - src/lessons/02-custom-hooks/01-custom-hooks-fundamentals.md
//       Section: "usePrevious" — compares the useRef+useEffect approach vs the derived state approach used here
//   - src/lessons/01-hooks-deep-dive/01-hooks-and-state-management.md
//       Sections: "useRef", "useEffect" — understand the primitives this hook builds on
//
// ALSO SEE:
//   - src/lessons/02-custom-hooks/CustomHooksDemo.jsx — run this to test your implementation interactively
//   - src/hooks/useFetch.js — a more complex custom hook exercise to try next
//
// KEY CONCEPTS:
//   - This implementation uses a derived-state pattern: useState with [prev, curr] tuple
//   - The if(curr !== value) check triggers a synchronous re-render (setState during render)
//   - Alternative approach: useRef + useEffect (ref updates after render, effect runs after commit)
//   - Both approaches are valid; this one avoids the one-render-behind issue of useRef+useEffect

import { useState } from 'react';

/**
 * EXERCISE: Implement usePrevious
 *
 * This hook should return the previous value of whatever is passed to it.
 *
 * Example usage:
 *   const [count, setCount] = useState(0);
 *   const prevCount = usePrevious(count);
 *   // First render: prevCount = undefined
 *   // After setCount(1): prevCount = 0
 *   // After setCount(5): prevCount = 1
 *
 * Hint: Think about when useRef updates vs when useEffect runs
 */

export function usePrevious(value) {
  // TODO: Implement this hook
  //
  // Questions to consider:
  // 1. Where should you store the previous value?
  // 2. When should you update the stored value?
  // 3. What should you return?
  const [[prev, curr], setState] = useState([undefined, value]);

  if(curr !== value) {
    setState([curr, value])
  }

  return prev;
}
