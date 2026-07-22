/**
 * Structured failure code glossary.
 *
 * These are the kernel's FailureCode taxonomy values. The cloud's
 * decision_reason may carry one of these codes; the Trust Surface
 * extracts it and shows a plain-English gloss alongside the code.
 *
 * Source of truth: actenon-kernel FailureCode enum (taxonomy_version=1).
 */

export type FailureCode =
  | 'BUDGET_EXCEEDED'
  | 'SCOPE_DENIED'
  | 'ACTION_MISMATCH'
  | 'REVOKED'
  | 'EXPIRED'
  | 'RATE_LIMITED'
  | 'DUPLICATE_REPLAY'
  | 'CURRENCY_MISMATCH'
  | 'GRANT_INVALID'
  | 'AMOUNT_NEGATIVE'
  | 'PAYLOAD_TOO_LARGE'
  | 'TARGET_FORBIDDEN'
  | 'SIGNATURE_INVALID'
  | 'UNKNOWN';

interface FailureCodeMeta {
  code: FailureCode;
  gloss: string;
  severity: 'deny' | 'warn';
}

const TAXONOMY: Record<FailureCode, FailureCodeMeta> = {
  BUDGET_EXCEEDED: {
    code: 'BUDGET_EXCEEDED',
    gloss: 'The action would exceed the remaining budget on the grant.',
    severity: 'deny',
  },
  SCOPE_DENIED: {
    code: 'SCOPE_DENIED',
    gloss: 'The action type is not within the scopes the grant permits.',
    severity: 'deny',
  },
  ACTION_MISMATCH: {
    code: 'ACTION_MISMATCH',
    gloss: 'The attempted action does not match the authorised action bound in the proof.',
    severity: 'deny',
  },
  REVOKED: {
    code: 'REVOKED',
    gloss: 'The grant has been revoked by an operator or the kill switch.',
    severity: 'deny',
  },
  EXPIRED: {
    code: 'EXPIRED',
    gloss: 'The grant or the proof has passed its expiry time.',
    severity: 'deny',
  },
  RATE_LIMITED: {
    code: 'RATE_LIMITED',
    gloss: 'The action exceeds the rate limit on the grant.',
    severity: 'deny',
  },
  DUPLICATE_REPLAY: {
    code: 'DUPLICATE_REPLAY',
    gloss: 'This proof has already been used. Replays are refused.',
    severity: 'deny',
  },
  CURRENCY_MISMATCH: {
    code: 'CURRENCY_MISMATCH',
    gloss: 'The currency does not match the currency authorised on the grant.',
    severity: 'deny',
  },
  GRANT_INVALID: {
    code: 'GRANT_INVALID',
    gloss: 'The grant signature failed verification.',
    severity: 'deny',
  },
  AMOUNT_NEGATIVE: {
    code: 'AMOUNT_NEGATIVE',
    gloss: 'A negative amount was supplied. Negative amounts are rejected.',
    severity: 'deny',
  },
  PAYLOAD_TOO_LARGE: {
    code: 'PAYLOAD_TOO_LARGE',
    gloss: 'The request payload exceeds the maximum permitted size.',
    severity: 'deny',
  },
  TARGET_FORBIDDEN: {
    code: 'TARGET_FORBIDDEN',
    gloss: 'The target account is not on the allow-list for this grant.',
    severity: 'deny',
  },
  SIGNATURE_INVALID: {
    code: 'SIGNATURE_INVALID',
    gloss: 'The proof signature failed Ed25519 verification.',
    severity: 'deny',
  },
  UNKNOWN: {
    code: 'UNKNOWN',
    gloss: 'An unrecognised failure code was returned.',
    severity: 'warn',
  },
};

const CODE_PATTERN = /\b([A-Z][A-Z_]{4,})\b/;

/**
 * Attempt to extract a structured failure code from a freeform decision_reason.
 * Returns UNKNOWN if no recognised code is found.
 */
export function extractFailureCode(reason: string | null | undefined): FailureCode {
  if (!reason) return 'UNKNOWN';
  // Direct match first
  const upper = reason.trim().toUpperCase();
  if (upper in TAXONOMY) return upper as FailureCode;
  // Search for a code pattern
  const match = upper.match(CODE_PATTERN);
  if (match && match[1] in TAXONOMY) return match[1] as FailureCode;
  return 'UNKNOWN';
}

export function failureCodeMeta(code: FailureCode): FailureCodeMeta {
  return TAXONOMY[code] ?? TAXONOMY.UNKNOWN;
}

export function glossForCode(code: FailureCode): string {
  return failureCodeMeta(code).gloss;
}

export const ALL_FAILURE_CODES: FailureCode[] = [
  'BUDGET_EXCEEDED',
  'SCOPE_DENIED',
  'ACTION_MISMATCH',
  'REVOKED',
  'EXPIRED',
  'RATE_LIMITED',
  'DUPLICATE_REPLAY',
  'CURRENCY_MISMATCH',
  'GRANT_INVALID',
  'AMOUNT_NEGATIVE',
  'PAYLOAD_TOO_LARGE',
  'TARGET_FORBIDDEN',
  'SIGNATURE_INVALID',
];
