// DRILL 1 — Rename & Restructure
// Transform this into target_01.ts using hotkeys.
//
// Tasks:
//   1. Rename "data" to "transactions" everywhere (F2)
//   2. Rename "calc" to "calculateTotal" everywhere (F2)
//   3. Move the return statement to be right after the for loop (Alt+↑)
//   4. Swap the order of the two functions (select + move block)
//   5. Add "export" before both functions (Ctrl+D to select both "function", type "export function")

type Item = { id: string; amount: number; status: string };

function calc(data: Item[]): number {
  let total = 0;
  for (const item of data) {
    if (item.status === "completed") {
      total += item.amount;
    }
  }

  console.log("done");

  return total;
}

function filterValid(data: Item[]): Item[] {
  return data.filter(item => item.status !== "failed" && item.amount > 0);
}
