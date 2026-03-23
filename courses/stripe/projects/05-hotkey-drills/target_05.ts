function processPayment(charge: any, config: any): any {
  if (!charge) return { error: "Missing charge" };
  if (charge.amount <= 0) return { error: "Invalid amount" };
  if (!config) return { error: "Missing config" };
  if (!config.currency) return { error: "Missing currency" };

  const fee = Math.ceil(charge.amount * config.rate / 100);
  const net = charge.amount - fee;
  return {
    id: charge.id,
    fee,
    net,
    currency: config.currency,
    status: "processed",
  };
}

function validateUser(user: any): any {
  if (!user) return { valid: false, error: "Missing user" };
  if (!user.name) return { valid: false, error: "Missing name" };
  if (!user.email) return { valid: false, error: "Missing email" };
  if (!user.email.includes("@")) return { valid: false, error: "Invalid email" };

  return { valid: true, user };
}
