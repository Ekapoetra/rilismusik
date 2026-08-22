import { api } from "@/api/client";

export async function openXenditCheckout(paymentId) {
  const { data } = await api.post(`/payments/${paymentId}/checkout`);
  if (!data.payment_url) throw new Error("URL checkout Xendit tidak tersedia");
  window.location.assign(data.payment_url);
}

export async function pollPaymentUntilTerminal(paymentId, onUpdate, maxAttempts = 75) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const { data } = await api.get(`/payments/${paymentId}/status`);
    onUpdate?.(data);
    if (["paid", "expired", "cancelled", "failed"].includes(data.status)) return data;
    await new Promise((resolve) => setTimeout(resolve, 4000));
  }
  return { payment_id: paymentId, status: "pending" };
}