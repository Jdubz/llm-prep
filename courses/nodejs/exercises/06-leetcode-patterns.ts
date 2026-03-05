/**
 * LeetCode-Style Algorithm Exercises
 *
 * Classic data structures & algorithms problems — the kind you'll see on
 * LeetCode, in coding screens, and in whiteboard interviews. TypeScript is
 * just the implementation language here; the focus is on patterns: hash maps,
 * stacks, two pointers, sliding window, BFS/DFS, and dynamic programming.
 *
 * Run:  npx tsx exercises/06-leetcode-patterns.ts
 */


// ============================================================================
// SUPPORTING TYPES
// ============================================================================

class ListNode<T> {
  val: T;
  next: ListNode<T> | null;
  constructor(val: T, next: ListNode<T> | null = null) {
    this.val = val;
    this.next = next;
  }
}

class TreeNode<T> {
  val: T;
  left: TreeNode<T> | null;
  right: TreeNode<T> | null;
  constructor(val: T, left: TreeNode<T> | null = null, right: TreeNode<T> | null = null) {
    this.val = val;
    this.left = left;
    this.right = right;
  }
}

// Helper: build a linked list from an array
function buildList<T>(values: T[]): ListNode<T> | null {
  if (values.length === 0) return null;
  const head = new ListNode(values[0]);
  let current = head;
  for (let i = 1; i < values.length; i++) {
    current.next = new ListNode(values[i]);
    current = current.next;
  }
  return head;
}

// Helper: convert linked list to array
function listToArray<T>(head: ListNode<T> | null): T[] {
  const result: T[] = [];
  while (head) {
    result.push(head.val);
    head = head.next;
  }
  return result;
}


// ============================================================================
// EXERCISE 1: Two Sum (IMPLEMENTED)
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//   - ../10-interview-prep/02-system-design-and-code-review.md
//
// Given an array of numbers and a target, return the indices of the two
// numbers that add up to the target. Each input has exactly one solution,
// and you may not use the same element twice.
//
// Requirements:
//   - Return [i, j] where nums[i] + nums[j] === target
//   - i !== j (can't use the same element twice)
//   - O(n) time complexity
//   - Exactly one valid answer exists
//
// Hints:
//   - Use a hash map to store {value -> index} as you iterate
//   - For each number, check if (target - num) is already in the map
//   - If yes, return [map.get(complement), currentIndex]
//
//   Pattern — hash map for complement lookup:
//     const seen = new Map<number, number>();
//     for (let i = 0; i < nums.length; i++) {
//       const complement = target - nums[i];
//       if (seen.has(complement)) return [seen.get(complement)!, i];
//       seen.set(nums[i], i);
//     }
//
// Expected behavior:
//   twoSum([2, 7, 11, 15], 9)  → [0, 1]
//   twoSum([3, 2, 4], 6)       → [1, 2]
//   twoSum([3, 3], 6)          → [0, 1]

function twoSum(nums: number[], target: number): [number, number] {
  const seen = new Map<number, number>();
  for (let i = 0; i < nums.length; i++) {
    const complement = target - nums[i];
    if (seen.has(complement)) {
      return [seen.get(complement)!, i];
    }
    seen.set(nums[i], i);
  }
  throw new Error("No solution found");
}


// ============================================================================
// EXERCISE 2: Valid Parentheses
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//
// Given a string containing only the characters '(', ')', '{', '}', '[', ']',
// determine if the input string is valid. A string is valid if:
//   - Open brackets are closed by the same type of brackets
//   - Open brackets are closed in the correct order
//   - Every close bracket has a corresponding open bracket
//
// Requirements:
//   - Return true if the string is valid, false otherwise
//   - Empty string is valid
//   - O(n) time complexity
//
// Hints:
//   - Use a stack (array) — push opening brackets, pop for closing
//   - Map each closing bracket to its matching opening bracket
//   - When you see a closing bracket, check that the top of the stack matches
//   - At the end, the stack should be empty
//
//   Pattern — stack-based matching:
//     const pairs: Record<string, string> = { ')': '(', ']': '[', '}': '{' };
//     const stack: string[] = [];
//     for (const ch of s) {
//       if (ch in pairs) { /* check top of stack */ }
//       else { stack.push(ch); }
//     }
//     return stack.length === 0;
//
// Expected behavior:
//   isValid("()")      → true
//   isValid("()[]{}")   → true
//   isValid("(]")       → false
//   isValid("([)]")     → false
//   isValid("{[]}")     → true
//   isValid("")         → true

function isValid(_s: string): boolean {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 3: Merge Two Sorted Lists
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//
// Merge two sorted singly-linked lists into one sorted list. The merged list
// should be made by splicing together the nodes of the two input lists.
//
// Requirements:
//   - Return the head of the merged sorted linked list
//   - If either list is null, return the other
//   - Do not create new nodes — reuse existing ones
//   - O(n + m) time where n, m are the list lengths
//
// Hints:
//   - Create a dummy head node to simplify edge cases
//   - Use a pointer that always appends the smaller of the two current nodes
//   - When one list is exhausted, append the remainder of the other
//
//   Pattern — dummy head with iterative merge:
//     const dummy = new ListNode(0 as any);
//     let tail = dummy;
//     while (l1 && l2) {
//       if (l1.val <= l2.val) { tail.next = l1; l1 = l1.next; }
//       else { tail.next = l2; l2 = l2.next; }
//       tail = tail.next;
//     }
//     tail.next = l1 ?? l2;
//     return dummy.next;
//
// Expected behavior:
//   merge([1,2,4], [1,3,4]) → [1,1,2,3,4,4]
//   merge([], [])           → []
//   merge([], [0])          → [0]

function mergeTwoLists<T>(
  _l1: ListNode<T> | null,
  _l2: ListNode<T> | null,
): ListNode<T> | null {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 4: Binary Search Variants
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//
// Implement classic binary search and a variant that finds the first
// occurrence of a target in a sorted array (which may contain duplicates).
//
// Requirements:
//   - binarySearch(nums, target): return the index of target, or -1
//   - findFirstOccurrence(nums, target): return the index of the FIRST
//     occurrence of target, or -1 if not found
//   - O(log n) time for both
//   - nums is sorted in ascending order
//
// Hints:
//   - Classic binary search: lo=0, hi=len-1, while lo<=hi, check mid
//   - For first occurrence: when you find target, don't return immediately —
//     record the answer and keep searching left (hi = mid - 1)
//
//   Pattern — binary search template:
//     let lo = 0, hi = nums.length - 1;
//     while (lo <= hi) {
//       const mid = lo + Math.floor((hi - lo) / 2);
//       if (nums[mid] === target) return mid;  // or record and keep going
//       if (nums[mid] < target) lo = mid + 1;
//       else hi = mid - 1;
//     }
//     return -1;
//
// Expected behavior:
//   binarySearch([1, 3, 5, 7, 9], 5)           → 2
//   binarySearch([1, 3, 5, 7, 9], 4)           → -1
//   findFirstOccurrence([1, 2, 2, 2, 3], 2)    → 1
//   findFirstOccurrence([1, 1, 1, 1], 1)       → 0
//   findFirstOccurrence([1, 2, 3], 4)           → -1

function binarySearch(_nums: number[], _target: number): number {
  throw new Error("Not implemented");
}

function findFirstOccurrence(_nums: number[], _target: number): number {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 5: Max Depth of Binary Tree
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//
// Given a binary tree, find its maximum depth. The maximum depth is the
// number of nodes along the longest path from the root down to the
// farthest leaf node.
//
// Requirements:
//   - Return 0 for null (empty tree)
//   - A single-node tree has depth 1
//   - O(n) time — visit each node once
//
// Hints:
//   - Classic recursive DFS
//   - Base case: null → 0
//   - Recursive case: 1 + max(depth(left), depth(right))
//
//   Pattern — recursive DFS:
//     function maxDepth(root: TreeNode<T> | null): number {
//       if (!root) return 0;
//       return 1 + Math.max(maxDepth(root.left), maxDepth(root.right));
//     }
//
// Expected behavior:
//   maxDepth(null)           → 0
//   maxDepth(TreeNode(1))    → 1
//   maxDepth(tree [3,9,20,null,null,15,7]) → 3

function maxDepth<T>(_root: TreeNode<T> | null): number {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 6: Level Order Traversal (BFS)
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//   - ../10-interview-prep/02-system-design-and-code-review.md
//
// Given a binary tree, return its level order traversal as a 2D array —
// each inner array contains the values at that depth level.
//
// Requirements:
//   - Return T[][] where each inner array is one level
//   - Root is level 0
//   - Return [] for an empty tree
//   - O(n) time
//
// Hints:
//   - Use a queue (array) for BFS
//   - Process one level at a time by tracking the queue size at each level
//   - For each level, drain exactly `size` nodes and push their children
//
//   Pattern — BFS with level grouping:
//     const result: T[][] = [];
//     const queue: TreeNode<T>[] = [root];
//     while (queue.length > 0) {
//       const levelSize = queue.length;
//       const level: T[] = [];
//       for (let i = 0; i < levelSize; i++) {
//         const node = queue.shift()!;
//         level.push(node.val);
//         if (node.left) queue.push(node.left);
//         if (node.right) queue.push(node.right);
//       }
//       result.push(level);
//     }
//
// Expected behavior:
//   levelOrder(tree [3,9,20,null,null,15,7]) → [[3], [9, 20], [15, 7]]
//   levelOrder(tree [1])                      → [[1]]
//   levelOrder(null)                           → []

function levelOrder<T>(_root: TreeNode<T> | null): T[][] {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 7: Number of Islands
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//
// Given a 2D grid of '1's (land) and '0's (water), count the number of
// islands. An island is surrounded by water and is formed by connecting
// adjacent land cells horizontally or vertically.
//
// Requirements:
//   - Return the number of distinct islands
//   - Grid edges are all water
//   - Modify the grid in-place (mark visited cells) or use a visited set
//   - O(rows * cols) time
//
// Hints:
//   - Iterate every cell; when you find a '1', increment count and flood-fill
//   - DFS/BFS flood fill: mark the current '1' as '0' (visited), then
//     recurse/enqueue all 4 neighbors that are '1'
//
//   Pattern — DFS flood fill:
//     function dfs(grid: string[][], r: number, c: number): void {
//       if (r < 0 || r >= grid.length || c < 0 || c >= grid[0].length) return;
//       if (grid[r][c] !== '1') return;
//       grid[r][c] = '0';  // mark visited
//       dfs(grid, r+1, c); dfs(grid, r-1, c);
//       dfs(grid, r, c+1); dfs(grid, r, c-1);
//     }
//
// Expected behavior:
//   numIslands([
//     ['1','1','0','0','0'],
//     ['1','1','0','0','0'],
//     ['0','0','1','0','0'],
//     ['0','0','0','1','1']
//   ]) → 3
//
//   numIslands([
//     ['1','1','1'],
//     ['0','1','0'],
//     ['1','1','1']
//   ]) → 1

function numIslands(_grid: string[][]): number {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 8: Longest Substring Without Repeating Characters
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//
// Given a string, find the length of the longest substring without repeating
// characters.
//
// Requirements:
//   - Return the length (not the substring itself)
//   - O(n) time complexity
//   - Handle empty string (return 0)
//
// Hints:
//   - Sliding window with a Set
//   - Expand the window (right pointer) adding characters to the set
//   - When a duplicate is found, shrink from the left until the duplicate
//     is removed
//   - Track the maximum window size
//
//   Pattern — sliding window:
//     let left = 0, maxLen = 0;
//     const seen = new Set<string>();
//     for (let right = 0; right < s.length; right++) {
//       while (seen.has(s[right])) {
//         seen.delete(s[left]);
//         left++;
//       }
//       seen.add(s[right]);
//       maxLen = Math.max(maxLen, right - left + 1);
//     }
//
// Expected behavior:
//   lengthOfLongestSubstring("abcabcbb") → 3  ("abc")
//   lengthOfLongestSubstring("bbbbb")    → 1  ("b")
//   lengthOfLongestSubstring("pwwkew")   → 3  ("wke")
//   lengthOfLongestSubstring("")          → 0

function lengthOfLongestSubstring(_s: string): number {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 9: 3Sum
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//
// Given an array of integers, find all unique triplets [a, b, c] such that
// a + b + c = 0. The solution set must not contain duplicate triplets.
//
// Requirements:
//   - Return an array of triplets (each sorted ascending)
//   - No duplicate triplets in the result
//   - O(n^2) time complexity
//
// Hints:
//   - Sort the array first
//   - Fix one element (i), then use two pointers (lo, hi) on the remainder
//   - Skip duplicate values for i, lo, and hi to avoid duplicate triplets
//   - If nums[i] > 0, break early (sorted, so no way to sum to 0)
//
//   Pattern — sort + two pointers:
//     nums.sort((a, b) => a - b);
//     for (let i = 0; i < nums.length - 2; i++) {
//       if (i > 0 && nums[i] === nums[i-1]) continue;  // skip dupes
//       let lo = i + 1, hi = nums.length - 1;
//       while (lo < hi) {
//         const sum = nums[i] + nums[lo] + nums[hi];
//         if (sum === 0) { result.push([...]); /* skip dupes, move both */ }
//         else if (sum < 0) lo++;
//         else hi--;
//       }
//     }
//
// Expected behavior:
//   threeSum([-1, 0, 1, 2, -1, -4]) → [[-1, -1, 2], [-1, 0, 1]]
//   threeSum([0, 1, 1])              → []
//   threeSum([0, 0, 0])              → [[0, 0, 0]]

function threeSum(_nums: number[]): number[][] {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 10: Coin Change (DP)
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//   - ../10-interview-prep/02-system-design-and-code-review.md
//
// Given an array of coin denominations and a target amount, return the fewest
// number of coins needed to make that amount. If it's not possible, return -1.
//
// Requirements:
//   - Return the minimum number of coins, or -1 if impossible
//   - You have an infinite supply of each coin denomination
//   - O(amount * coins.length) time
//   - O(amount) space
//
// Hints:
//   - Bottom-up DP: dp[i] = minimum coins to make amount i
//   - Initialize dp[0] = 0, all others to Infinity
//   - For each amount from 1 to target, try each coin
//   - dp[i] = min(dp[i], dp[i - coin] + 1) for each valid coin
//
//   Pattern — bottom-up DP:
//     const dp = new Array(amount + 1).fill(Infinity);
//     dp[0] = 0;
//     for (let i = 1; i <= amount; i++) {
//       for (const coin of coins) {
//         if (coin <= i) dp[i] = Math.min(dp[i], dp[i - coin] + 1);
//       }
//     }
//     return dp[amount] === Infinity ? -1 : dp[amount];
//
// Expected behavior:
//   coinChange([1, 5, 10, 25], 30) → 2  (25 + 5)
//   coinChange([2], 3)              → -1
//   coinChange([1], 0)              → 0
//   coinChange([1, 2, 5], 11)       → 3  (5 + 5 + 1)

function coinChange(_coins: number[], _amount: number): number {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 11: Merge Intervals
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//
// Given an array of intervals where intervals[i] = [start, end], merge all
// overlapping intervals and return the resulting non-overlapping intervals.
//
// Requirements:
//   - Return merged intervals sorted by start time
//   - Two intervals overlap if one starts before the other ends
//   - O(n log n) time (dominated by sorting)
//
// Hints:
//   - Sort intervals by start time
//   - Iterate through sorted intervals, maintaining a "current" merged interval
//   - If the next interval overlaps with current (next.start <= current.end),
//     extend current's end to max(current.end, next.end)
//   - Otherwise, push current to result and start a new current
//
//   Pattern — sort + single pass merge:
//     intervals.sort((a, b) => a[0] - b[0]);
//     const merged: number[][] = [intervals[0]];
//     for (let i = 1; i < intervals.length; i++) {
//       const last = merged[merged.length - 1];
//       if (intervals[i][0] <= last[1]) {
//         last[1] = Math.max(last[1], intervals[i][1]);
//       } else {
//         merged.push(intervals[i]);
//       }
//     }
//
// Expected behavior:
//   mergeIntervals([[1,3],[2,6],[8,10],[15,18]]) → [[1,6],[8,10],[15,18]]
//   mergeIntervals([[1,4],[4,5]])                 → [[1,5]]
//   mergeIntervals([[1,4],[0,4]])                 → [[0,4]]

function mergeIntervals(_intervals: number[][]): number[][] {
  throw new Error("Not implemented");
}


// ============================================================================
// EXERCISE 12: Top K Frequent Elements
// ============================================================================
//
// RELATED READING:
//   - ../10-interview-prep/01-interview-fundamentals.md
//   - ../10-interview-prep/02-system-design-and-code-review.md
//
// Given an integer array and an integer k, return the k most frequent
// elements. You may return the answer in any order.
//
// Requirements:
//   - Return exactly k elements
//   - If multiple elements have the same frequency, any valid answer is accepted
//   - O(n) time complexity (use bucket sort, not heap)
//
// Hints:
//   - Step 1: Count frequencies with a Map
//   - Step 2: Bucket sort — create an array of buckets where index = frequency
//     (bucket[i] holds all elements that appear i times)
//   - Step 3: Iterate buckets from highest frequency down, collecting elements
//     until you have k
//
//   Pattern — frequency counting + bucket sort:
//     const freq = new Map<number, number>();
//     for (const n of nums) freq.set(n, (freq.get(n) ?? 0) + 1);
//
//     const buckets: number[][] = Array.from({ length: nums.length + 1 }, () => []);
//     for (const [num, count] of freq) buckets[count].push(num);
//
//     const result: number[] = [];
//     for (let i = buckets.length - 1; i >= 0 && result.length < k; i--) {
//       result.push(...buckets[i]);
//     }
//     return result.slice(0, k);
//
// Expected behavior:
//   topKFrequent([1,1,1,2,2,3], 2) → [1, 2] (in any order)
//   topKFrequent([1], 1)            → [1]
//   topKFrequent([4,4,4,2,2,3,3,3], 2) → [4, 3] (in any order)

function topKFrequent(_nums: number[], _k: number): number[] {
  throw new Error("Not implemented");
}


// ============================================================================
// TESTS
// ============================================================================

function test_two_sum(): void {
  console.log("\n=== EXERCISE 1: Two Sum ===");

  const r1 = twoSum([2, 7, 11, 15], 9);
  console.assert(r1[0] === 0 && r1[1] === 1, "twoSum([2,7,11,15], 9) → [0,1]");

  const r2 = twoSum([3, 2, 4], 6);
  console.assert(r2[0] === 1 && r2[1] === 2, "twoSum([3,2,4], 6) → [1,2]");

  const r3 = twoSum([3, 3], 6);
  console.assert(r3[0] === 0 && r3[1] === 1, "twoSum([3,3], 6) → [0,1]");

  // Negative numbers
  const r4 = twoSum([-1, -2, -3, -4, -5], -8);
  console.assert(r4[0] === 2 && r4[1] === 4, "Negative numbers work");

  console.log("EXERCISE 1: PASSED");
}

function test_valid_parentheses(): void {
  console.log("\n=== EXERCISE 2: Valid Parentheses ===");

  console.assert(isValid("()") === true, '"()" is valid');
  console.assert(isValid("()[]{}") === true, '"()[]{}" is valid');
  console.assert(isValid("(]") === false, '"(]" is invalid');
  console.assert(isValid("([)]") === false, '"([)]" is invalid');
  console.assert(isValid("{[]}") === true, '"{[]}" is valid');
  console.assert(isValid("") === true, 'empty string is valid');
  console.assert(isValid("((") === false, '"((" is invalid');
  console.assert(isValid(")") === false, '")" is invalid');

  console.log("EXERCISE 2: PASSED");
}

function test_merge_two_lists(): void {
  console.log("\n=== EXERCISE 3: Merge Two Sorted Lists ===");

  const r1 = listToArray(mergeTwoLists(buildList([1, 2, 4]), buildList([1, 3, 4])));
  console.assert(
    JSON.stringify(r1) === JSON.stringify([1, 1, 2, 3, 4, 4]),
    "merge [1,2,4] + [1,3,4] → [1,1,2,3,4,4]",
  );

  const r2 = listToArray(mergeTwoLists(buildList<number>([]), buildList<number>([])));
  console.assert(JSON.stringify(r2) === "[]", "merge [] + [] → []");

  const r3 = listToArray(mergeTwoLists(buildList<number>([]), buildList([0])));
  console.assert(JSON.stringify(r3) === JSON.stringify([0]), "merge [] + [0] → [0]");

  const r4 = listToArray(mergeTwoLists(buildList([5]), buildList([1, 2, 3])));
  console.assert(
    JSON.stringify(r4) === JSON.stringify([1, 2, 3, 5]),
    "merge [5] + [1,2,3] → [1,2,3,5]",
  );

  console.log("EXERCISE 3: PASSED");
}

function test_binary_search(): void {
  console.log("\n=== EXERCISE 4: Binary Search Variants ===");

  console.assert(binarySearch([1, 3, 5, 7, 9], 5) === 2, "find 5 at index 2");
  console.assert(binarySearch([1, 3, 5, 7, 9], 4) === -1, "4 not found");
  console.assert(binarySearch([1], 1) === 0, "single element found");
  console.assert(binarySearch([], 1) === -1, "empty array");

  console.assert(findFirstOccurrence([1, 2, 2, 2, 3], 2) === 1, "first 2 at index 1");
  console.assert(findFirstOccurrence([1, 1, 1, 1], 1) === 0, "first 1 at index 0");
  console.assert(findFirstOccurrence([1, 2, 3], 4) === -1, "4 not found");
  console.assert(findFirstOccurrence([2, 2, 2], 2) === 0, "all same, first at 0");

  console.log("EXERCISE 4: PASSED");
}

function test_max_depth(): void {
  console.log("\n=== EXERCISE 5: Max Depth of Binary Tree ===");

  console.assert(maxDepth(null) === 0, "null tree has depth 0");
  console.assert(maxDepth(new TreeNode(1)) === 1, "single node has depth 1");

  //     3
  //    / \
  //   9  20
  //     /  \
  //    15   7
  const tree = new TreeNode(
    3,
    new TreeNode(9),
    new TreeNode(20, new TreeNode(15), new TreeNode(7)),
  );
  console.assert(maxDepth(tree) === 3, "depth of [3,9,20,null,null,15,7] is 3");

  // Left-skewed
  const skewed = new TreeNode(1, new TreeNode(2, new TreeNode(3)));
  console.assert(maxDepth(skewed) === 3, "left-skewed tree depth 3");

  console.log("EXERCISE 5: PASSED");
}

function test_level_order(): void {
  console.log("\n=== EXERCISE 6: Level Order Traversal ===");

  console.assert(
    JSON.stringify(levelOrder(null)) === "[]",
    "null tree → []",
  );

  console.assert(
    JSON.stringify(levelOrder(new TreeNode(1))) === "[[1]]",
    "single node → [[1]]",
  );

  const tree = new TreeNode(
    3,
    new TreeNode(9),
    new TreeNode(20, new TreeNode(15), new TreeNode(7)),
  );
  console.assert(
    JSON.stringify(levelOrder(tree)) === "[[3],[9,20],[15,7]]",
    "level order of [3,9,20,null,null,15,7]",
  );

  console.log("EXERCISE 6: PASSED");
}

function test_num_islands(): void {
  console.log("\n=== EXERCISE 7: Number of Islands ===");

  const grid1 = [
    ["1", "1", "0", "0", "0"],
    ["1", "1", "0", "0", "0"],
    ["0", "0", "1", "0", "0"],
    ["0", "0", "0", "1", "1"],
  ];
  console.assert(numIslands(grid1) === 3, "3 islands");

  const grid2 = [
    ["1", "1", "1"],
    ["0", "1", "0"],
    ["1", "1", "1"],
  ];
  console.assert(numIslands(grid2) === 1, "1 island (connected)");

  const grid3 = [["0", "0"], ["0", "0"]];
  console.assert(numIslands(grid3) === 0, "no islands");

  console.log("EXERCISE 7: PASSED");
}

function test_longest_substring(): void {
  console.log("\n=== EXERCISE 8: Longest Substring Without Repeating ===");

  console.assert(lengthOfLongestSubstring("abcabcbb") === 3, '"abcabcbb" → 3');
  console.assert(lengthOfLongestSubstring("bbbbb") === 1, '"bbbbb" → 1');
  console.assert(lengthOfLongestSubstring("pwwkew") === 3, '"pwwkew" → 3');
  console.assert(lengthOfLongestSubstring("") === 0, 'empty → 0');
  console.assert(lengthOfLongestSubstring("abcdef") === 6, '"abcdef" → 6');

  console.log("EXERCISE 8: PASSED");
}

function test_three_sum(): void {
  console.log("\n=== EXERCISE 9: 3Sum ===");

  const r1 = threeSum([-1, 0, 1, 2, -1, -4]);
  console.assert(
    JSON.stringify(r1) === JSON.stringify([[-1, -1, 2], [-1, 0, 1]]),
    "[-1,0,1,2,-1,-4] → [[-1,-1,2],[-1,0,1]]",
  );

  const r2 = threeSum([0, 1, 1]);
  console.assert(JSON.stringify(r2) === "[]", "[0,1,1] → []");

  const r3 = threeSum([0, 0, 0]);
  console.assert(
    JSON.stringify(r3) === JSON.stringify([[0, 0, 0]]),
    "[0,0,0] → [[0,0,0]]",
  );

  console.log("EXERCISE 9: PASSED");
}

function test_coin_change(): void {
  console.log("\n=== EXERCISE 10: Coin Change ===");

  console.assert(coinChange([1, 5, 10, 25], 30) === 2, "30 cents → 2 coins (25+5)");
  console.assert(coinChange([2], 3) === -1, "3 with only 2s → -1");
  console.assert(coinChange([1], 0) === 0, "amount 0 → 0 coins");
  console.assert(coinChange([1, 2, 5], 11) === 3, "11 → 3 coins (5+5+1)");

  console.log("EXERCISE 10: PASSED");
}

function test_merge_intervals(): void {
  console.log("\n=== EXERCISE 11: Merge Intervals ===");

  console.assert(
    JSON.stringify(mergeIntervals([[1, 3], [2, 6], [8, 10], [15, 18]])) ===
      JSON.stringify([[1, 6], [8, 10], [15, 18]]),
    "merge overlapping intervals",
  );

  console.assert(
    JSON.stringify(mergeIntervals([[1, 4], [4, 5]])) ===
      JSON.stringify([[1, 5]]),
    "touching intervals merge",
  );

  console.assert(
    JSON.stringify(mergeIntervals([[1, 4], [0, 4]])) ===
      JSON.stringify([[0, 4]]),
    "unsorted intervals",
  );

  console.assert(
    JSON.stringify(mergeIntervals([[1, 4]])) ===
      JSON.stringify([[1, 4]]),
    "single interval",
  );

  console.log("EXERCISE 11: PASSED");
}

function test_top_k_frequent(): void {
  console.log("\n=== EXERCISE 12: Top K Frequent Elements ===");

  const r1 = topKFrequent([1, 1, 1, 2, 2, 3], 2).sort((a, b) => a - b);
  console.assert(JSON.stringify(r1) === JSON.stringify([1, 2]), "top 2 of [1,1,1,2,2,3]");

  const r2 = topKFrequent([1], 1);
  console.assert(JSON.stringify(r2) === JSON.stringify([1]), "single element");

  const r3 = topKFrequent([4, 4, 4, 2, 2, 3, 3, 3], 2).sort((a, b) => a - b);
  console.assert(JSON.stringify(r3) === JSON.stringify([3, 4]), "top 2 of [4,4,4,2,2,3,3,3]");

  console.log("EXERCISE 12: PASSED");
}


if (require.main === module) {
  console.log("LeetCode-Style Algorithm Exercises");
  console.log("=".repeat(60));

  const tests: [string, () => void][] = [
    ["Exercise 1: Two Sum", test_two_sum],
    ["Exercise 2: Valid Parentheses", test_valid_parentheses],
    ["Exercise 3: Merge Two Sorted Lists", test_merge_two_lists],
    ["Exercise 4: Binary Search Variants", test_binary_search],
    ["Exercise 5: Max Depth of Binary Tree", test_max_depth],
    ["Exercise 6: Level Order Traversal", test_level_order],
    ["Exercise 7: Number of Islands", test_num_islands],
    ["Exercise 8: Longest Substring Without Repeating", test_longest_substring],
    ["Exercise 9: 3Sum", test_three_sum],
    ["Exercise 10: Coin Change", test_coin_change],
    ["Exercise 11: Merge Intervals", test_merge_intervals],
    ["Exercise 12: Top K Frequent Elements", test_top_k_frequent],
  ];

  let passed = 0;
  let failed = 0;

  for (const [name, testFn] of tests) {
    try {
      testFn();
      passed++;
    } catch (e) {
      if (e instanceof Error && e.message === "Not implemented") {
        console.log(`  ${name}: NOT IMPLEMENTED`);
      } else if (e instanceof Error) {
        console.log(`  ${name}: FAILED -- ${e.message}`);
      } else {
        console.log(`  ${name}: ERROR -- ${e}`);
      }
      failed++;
    }
  }

  console.log();
  console.log("=".repeat(60));
  console.log(`Results: ${passed} passed, ${failed} failed out of ${tests.length}`);
  console.log("=".repeat(60));
}
