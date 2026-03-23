type Charge = {
  id: string;
  amount: number;
  currency: string;
  source: string;
  status: "succeeded" | "failed";
};

type ChargeResult = {
  chargeId: string;
  fee: number;
  net: number;
  currency: string;
};

type RefundResult = {
  chargeId: string;
  refundedAmount: number;
  remainingBalance: number;
};

function processCharge(charge: Charge, feePercent: number): ChargeResult {
  const { id, amount, currency } = charge;
  const fee = Math.ceil(amount * feePercent / 100);
  const net = amount - fee;
  return { chargeId: id, fee, net, currency };
}

function processRefund(charge: Charge, refundAmount: number): RefundResult {
  const { id, amount } = charge;
  return { chargeId: id, refundedAmount: refundAmount, remainingBalance: amount - refundAmount };
}
