/**
 * Design system primitives.
 * shadcn-style: simple, accessible, variant-driven, no external UI lib.
 * Radix-quality accessibility without the Radix dependency for these basic
 * primitives (we use native elements with ARIA where sufficient).
 */
import { forwardRef } from 'react';
import type { ButtonHTMLAttributes, HTMLAttributes } from 'react';
import { cn } from '../lib/cn';

// ── Button ──────────────────────────────────────────────────────────

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'allow';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const buttonVariants: Record<ButtonVariant, string> = {
  primary:
    'bg-accent text-paper hover:bg-accent/90 border border-transparent font-semibold',
  secondary:
    'bg-surface-2 text-ink hover:bg-edge border border-edge-strong font-medium',
  ghost:
    'bg-transparent text-ink hover:bg-surface-2 border border-transparent font-medium',
  danger:
    'bg-deny text-paper hover:bg-deny/90 border border-transparent font-semibold',
  allow:
    'bg-allow text-paper hover:bg-allow/90 border border-transparent font-semibold',
};

const buttonSizes: Record<ButtonSize, string> = {
  sm: 'h-7 px-3 text-2xs rounded-sm',
  md: 'h-9 px-4 text-sm rounded-md',
  lg: 'h-11 px-6 text-base rounded-md',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'secondary', size = 'md', className, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center gap-2 transition-colors duration-150 ease-decisive',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface',
        buttonVariants[variant],
        buttonSizes[size],
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = 'Button';

// ── Card / Panel ────────────────────────────────────────────────────

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padded?: boolean;
}

export function Card({ padded = false, className, ...props }: CardProps) {
  return (
    <div
      className={cn('panel', padded && 'p-5', className)}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('panel-header', className)} {...props} />;
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('panel-body', className)} {...props} />;
}

// ── Badge ───────────────────────────────────────────────────────────

type BadgeTone = 'neutral' | 'allow' | 'deny' | 'pending' | 'accent' | 'muted';

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

const badgeTones: Record<BadgeTone, string> = {
  neutral: 'bg-surface-2 text-muted border-edge-strong',
  allow: 'bg-allow/10 text-allow border-allow/30',
  deny: 'bg-deny/10 text-deny border-deny/30',
  pending: 'bg-pending/10 text-pending border-pending/30',
  accent: 'bg-accent/10 text-accent border-accent/30',
  muted: 'bg-surface-2 text-muted border-edge',
};

export function Badge({ tone = 'neutral', className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 text-2xs font-semibold uppercase tracking-wide rounded-xs border',
        badgeTones[tone],
        className,
      )}
      {...props}
    />
  );
}

// ── DefinitionRow — the atomic unit of the trust surface ────────────

interface DefinitionRowProps {
  label: string;
  children: React.ReactNode;
  mono?: boolean;
}

export function DefinitionRow({ label, children, mono = false }: DefinitionRowProps) {
  return (
    <div className="def-row">
      <dt className="def-label">{label}</dt>
      <dd className={cn('def-value', mono && 'font-mono')}>{children}</dd>
    </div>
  );
}

// ── SectionHeading ──────────────────────────────────────────────────

interface SectionHeadingProps {
  eyebrow?: string;
  title: string;
  description?: string;
}

export function SectionHeading({ eyebrow, title, description }: SectionHeadingProps) {
  return (
    <div className="mb-4">
      {eyebrow && (
        <p className="text-2xs font-semibold uppercase tracking-widest text-accent mb-1">
          {eyebrow}
        </p>
      )}
      <h2 className="text-lg font-semibold text-ink">{title}</h2>
      {description && <p className="text-sm text-muted mt-1">{description}</p>}
    </div>
  );
}

// ── Spinner (minimal, respects reduced motion) ──────────────────────

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'inline-block h-4 w-4 rounded-full border-2 border-edge border-t-accent animate-spin',
        className,
      )}
      role="status"
      aria-label="Loading"
    />
  );
}
