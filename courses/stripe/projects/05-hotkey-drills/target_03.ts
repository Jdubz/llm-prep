export const getUserName = function(user: any): string {
  const name = `${user.first} ${user.last}`;
  return name;
}

export const formatCharge = function(id: any, amount: any, currency: any): string {
  const display = `Charge ${id}: ${amount} ${currency}`;
  return display;
}

export const formatRefund = function(chargeId: any, amount: any): string {
  const msg = `Refund for ${chargeId} of ${amount}`;
  return msg;
}

export const buildError = function(code: any, message: any): string {
  const err = `Error ${code}: ${message}`;
  return err;
}
