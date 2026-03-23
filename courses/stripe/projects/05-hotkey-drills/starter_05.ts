// DRILL 5 — Refactor to Guard Clauses
// Transform this into target_05.ts using hotkeys.
//
// Tasks:
//   Convert deeply nested if/else into early-return guard clauses.
//   1. Select the inner "return" + its condition → move to top of function
//   2. Invert the condition (=== → !==, etc.)
//   3. Delete the now-empty else branches and extra braces
//   4. Outdent the remaining code
//
// Key hotkeys: Ctrl+L (select line), Alt+↑ (move up), Ctrl+Shift+K
// (delete line), Ctrl+] / Ctrl+[ (indent/outdent), Ctrl+/ (toggle comment)

function processPayment(charge: any, config: any): any {
  if (charge) {
    if (charge.amount > 0) {
      if (config) {
        if (config.currency) {
          const fee = Math.ceil(charge.amount * config.rate / 100);
          const net = charge.amount - fee;
          return {
            id: charge.id,
            fee,
            net,
            currency: config.currency,
            status: "processed",
          };
        } else {
          return { error: "Missing currency" };
        }
      } else {
        return { error: "Missing config" };
      }
    } else {
      return { error: "Invalid amount" };
    }
  } else {
    return { error: "Missing charge" };
  }
}

function validateUser(user: any): any {
  if (user) {
    if (user.name) {
      if (user.email) {
        if (user.email.includes("@")) {
          return { valid: true, user };
        } else {
          return { valid: false, error: "Invalid email" };
        }
      } else {
        return { valid: false, error: "Missing email" };
      }
    } else {
      return { valid: false, error: "Missing name" };
    }
  } else {
    return { valid: false, error: "Missing user" };
  }
}
