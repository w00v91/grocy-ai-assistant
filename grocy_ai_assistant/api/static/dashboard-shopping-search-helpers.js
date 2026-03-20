export function parseAmountPrefixedSearch(rawValue) {
  const value = String(rawValue || '').trim();
  const match = value.match(/^(\d+(?:[.,]\d+)?)\s+(.+)$/);
  if (!match) {
    return { productName: value, amountFromName: null };
  }

  const parsedAmount = Number(match[1].replace(',', '.'));
  if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
    return { productName: value, amountFromName: null };
  }

  return {
    productName: match[2].trim(),
    amountFromName: parsedAmount,
  };
}

export function shouldShowClearButton(rawValue) {
  return Boolean(String(rawValue || ''));
}
