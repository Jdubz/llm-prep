// DRILL 3 — Bulk Transform
// Transform this into target_03.ts using hotkeys.
//
// Tasks:
//   1. Convert all "var" to "const" (Find & Replace: var → const)
//   2. Convert all string concatenation to template literals
//      e.g. "User " + name + " has " + count  →  `User ${name} has ${count}`
//   3. Add return types to all functions (multi-cursor after each ")")
//   4. Add "export" to all functions (Ctrl+Shift+L on "function")
//
// Key hotkeys: Ctrl+H (find & replace), Ctrl+D, regex replace

var getUserName = function(user: any) {
  var name = user.first + " " + user.last;
  return name;
}

var formatCharge = function(id: any, amount: any, currency: any) {
  var display = "Charge " + id + ": " + amount + " " + currency;
  return display;
}

var formatRefund = function(chargeId: any, amount: any) {
  var msg = "Refund for " + chargeId + " of " + amount;
  return msg;
}

var buildError = function(code: any, message: any) {
  var err = "Error " + code + ": " + message;
  return err;
}
