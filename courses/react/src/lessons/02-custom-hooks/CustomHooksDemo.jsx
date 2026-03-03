import { useState } from 'react';
import { usePrevious } from '../../hooks/usePrevious';
import { useFetch } from '../../hooks/useFetch';

/**
 * LESSON 2: Custom Hooks
 *
 * Test your hook implementations here.
 * Run the dev server: npm run dev
 *
 * LESSON MATERIAL (read these for theory and patterns):
 *   - src/lessons/02-custom-hooks/01-custom-hooks-fundamentals.md
 *       Covers: when to extract hooks, composition, return value contracts, real-world examples
 *   - src/lessons/02-custom-hooks/02-custom-hooks-testing-and-advanced.md
 *       Covers: testing with renderHook, TanStack Query internals, TypeScript generics, anti-patterns
 *
 * HOOK SOURCE FILES (implement these, then test here):
 *   - src/hooks/usePrevious.js — tracks the previous value of a variable (Demo 1 below)
 *   - src/hooks/useFetch.js   — data fetching with race condition handling (Demos 2 & 3 below)
 */

// Demo 1: usePrevious
function PreviousValueDemo() {
  const [count, setCount] = useState(0);
  const prevCount = usePrevious(count);

  return (
    <div className="demo-section">
      <h3>usePrevious Demo</h3>
      <p>Current count: <strong>{count}</strong></p>
      <p>Previous count: <strong>{prevCount ?? 'undefined'}</strong></p>
      <button onClick={() => setCount(c => c + 1)}>Increment</button>
      <button onClick={() => setCount(c => c - 1)}>Decrement</button>
      <button onClick={() => setCount(Math.floor(Math.random() * 100))}>Random</button>

      <div className="expected">
        <h4>Expected behavior:</h4>
        <ul>
          <li>First render: previous = undefined</li>
          <li>After click: previous = old value, current = new value</li>
        </ul>
      </div>
    </div>
  );
}

// Demo 2: useFetch
function FetchDemo() {
  const [userId, setUserId] = useState(1);
  const { data, error, isLoading, refetch } = useFetch(
    `https://jsonplaceholder.typicode.com/users/${userId}`
  );

  return (
    <div className="demo-section">
      <h3>useFetch Demo</h3>

      <div className="controls">
        <label>
          User ID:
          <select value={userId} onChange={e => setUserId(Number(e.target.value))}>
            {[1, 2, 3, 4, 5].map(id => (
              <option key={id} value={id}>User {id}</option>
            ))}
          </select>
        </label>
        <button onClick={refetch}>Refetch</button>
      </div>

      <div className="status">
        <p>Loading: <strong>{isLoading ? 'Yes' : 'No'}</strong></p>
        <p>Error: <strong>{error ?? 'None'}</strong></p>
      </div>

      {data && (
        <div className="data">
          <h4>User Data:</h4>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      )}

      <div className="expected">
        <h4>Expected behavior:</h4>
        <ul>
          <li>Shows loading state while fetching</li>
          <li>Displays user data when complete</li>
          <li>Changing user ID cancels previous request</li>
          <li>Refetch button triggers new request</li>
          <li>Rapid switching should not show stale data</li>
        </ul>
      </div>
    </div>
  );
}

// Race condition tester - rapidly switch to verify no stale data
function RaceConditionTester() {
  const [userId, setUserId] = useState(1);
  const { data, isLoading } = useFetch(
    `https://jsonplaceholder.typicode.com/users/${userId}`
  );

  const rapidSwitch = () => {
    // Rapidly cycle through users
    for (let i = 1; i <= 5; i++) {
      setTimeout(() => setUserId(i), i * 100);
    }
  };

  return (
    <div className="demo-section">
      <h3>Race Condition Tester</h3>
      <p>Click to rapidly switch users. Final result should be User 5.</p>
      <button onClick={rapidSwitch}>Rapid Switch (1 → 5)</button>
      <p>Current request: User {userId}</p>
      <p>Loading: {isLoading ? 'Yes' : 'No'}</p>
      {data && <p>Showing data for: <strong>{data.name}</strong> (ID: {data.id})</p>}

      <div className="expected">
        <h4>If your hook handles races correctly:</h4>
        <p>After rapid switch completes, should show User 5's data, not an earlier user.</p>
      </div>
    </div>
  );
}

export default function CustomHooksDemo() {
  return (
    <div className="lesson">
      <h1>Lesson 2: Custom Hooks</h1>
      <p>Implement the hooks in <code>src/hooks/</code> and test them here.</p>

      <PreviousValueDemo />
      <hr />
      <FetchDemo />
      <hr />
      <RaceConditionTester />
    </div>
  );
}
