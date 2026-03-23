type Item = { id: string; amount: number; status: string };

export function filterValid(transactions: Item[]): Item[] {
  return transactions.filter(item => item.status !== "failed" && item.amount > 0);
}

export function calculateTotal(transactions: Item[]): number {
  let total = 0;
  for (const item of transactions) {
    if (item.status === "completed") {
      total += item.amount;
    }
  }
  return total;

  console.log("done");
}
