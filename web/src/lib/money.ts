/**
 * Money is integer minor units end to end.
 * The backend stores Decimal as integer minor units (e.g. 500 = $5.00).
 * This module is the SINGLE place that converts minor units to a display string.
 * No float is ever introduced on the client.
 */

const CURRENCY_FRACTION_DIGITS: Readonly<Record<string, number>> = {
  USD: 2,
  EUR: 2,
  GBP: 2,
  JPY: 0,
  KRW: 0,
  CHF: 2,
  CAD: 2,
  AUD: 2,
  SGD: 2,
};

const DEFAULT_FRACTION_DIGITS = 2;

/**
 * Format integer minor units as a currency string.
 *
 * @param minorUnits - integer minor units (e.g. 500 => "$5.00")
 * @param currency - ISO 4217 code (e.g. "USD")
 * @returns formatted string, e.g. "$5.00", "£20.00", "¥1,000"
 *
 * Uses BigInt internally to avoid any float intermediate.
 */
export function formatMoney(minorUnits: number, currency: string): string {
  if (!Number.isInteger(minorUnits)) {
    // Defensive: should never happen from the backend, but fail safe.
    minorUnits = Math.trunc(minorUnits);
  }
  const fractionDigits = CURRENCY_FRACTION_DIGENTS(currency);
  const isNegative = minorUnits < 0;
  const absMinor = Math.abs(minorUnits);

  // Use BigInt to avoid float — divide by 10^fractionDigits manually.
  const divisor = 10n ** BigInt(fractionDigits);
  const major = BigInt(absMinor) / divisor;
  const minor = BigInt(absMinor) % divisor;

  const minorStr = minor.toString().padStart(fractionDigits, '0');
  const majorStr = formatMajorWithGroups(major.toString());

  const symbol = currencySymbol(currency);
  const sign = isNegative ? '-' : '';
  const body =
    fractionDigits === 0
      ? majorStr
      : `${majorStr}.${minorStr}`;

  // en-GB convention: symbol before amount for USD/GBP/EUR, after for JPY etc.
  if (currency === 'JPY' || currency === 'KRW') {
    return `${sign}${body}${symbol}`;
  }
  return `${sign}${symbol}${body}`;
}

function CURRENCY_FRACTION_DIGENTS(currency: string): number {
  return CURRENCY_FRACTION_DIGITS[currency.toUpperCase()] ?? DEFAULT_FRACTION_DIGITS;
}

function formatMajorWithGroups(digits: string): string {
  // Group with thin spaces (en-GB style for large numbers)
  if (digits.length <= 3) return digits;
  const parts: string[] = [];
  let remaining = digits;
  while (remaining.length > 3) {
    parts.unshift(remaining.slice(-3));
    remaining = remaining.slice(0, -3);
  }
  parts.unshift(remaining);
  return parts.join(',');
}

function currencySymbol(currency: string): string {
  const symbols: Record<string, string> = {
    USD: '$',
    EUR: '\u20AC',
    GBP: '\u00A3',
    JPY: '\u00A5',
    KRW: '\u20A9',
    CHF: 'CHF ',
    CAD: 'C$',
    AUD: 'A$',
    SGD: 'S$',
  };
  return symbols[currency.toUpperCase()] ?? currency + ' ';
}

/**
 * Format a delta between two minor-unit amounts, with sign.
 * e.g. diffMoney(500, 200) => "+$3.00"
 */
export function diffMoney(fromMinor: number, toMinor: number, currency: string): string {
  const delta = toMinor - fromMinor;
  const formatted = formatMoney(Math.abs(delta), currency);
  if (delta > 0) return `+${formatted}`;
  if (delta < 0) return `-${formatted}`;
  return formatted;
}
