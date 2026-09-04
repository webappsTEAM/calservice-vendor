import React from 'react';
import { Loader2 } from 'lucide-react';

export function Button({
  children,
  type = 'button',
  variant = 'primary', // 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'dangerSubtle' | 'success' | 'successSubtle' | 'subtle'
  size = 'md',        // 'xs' | 'sm' | 'md' | 'lg'
  shape = 'rounded',  // 'rounded' (rounded-lg) | 'pill' (rounded-full)
  isLoading = false,
  disabled = false,
  leftIcon: LeftIcon = null,
  rightIcon: RightIcon = null,
  className = '',
  onClick = () => {},
  ...props
}) {
  const baseStyles =
    'inline-flex items-center justify-center font-medium select-none transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-950/20 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none disabled:cursor-not-allowed';

  const variantStyles = {
    primary:
      'bg-zinc-900 text-white shadow-xs hover:bg-zinc-800 active:bg-zinc-950 border border-zinc-900',
    secondary:
      'bg-zinc-100 text-zinc-900 hover:bg-zinc-200/80 active:bg-zinc-200 border border-zinc-200/60',
    outline:
      'bg-white text-zinc-800 border border-zinc-300 hover:bg-zinc-50 active:bg-zinc-100 shadow-xs',
    ghost:
      'bg-transparent text-zinc-700 hover:bg-zinc-100 active:bg-zinc-200/60',
    danger:
      'bg-rose-600 text-white shadow-xs hover:bg-rose-700 active:bg-rose-800 border border-rose-600',
    dangerSubtle:
      'bg-rose-50 text-rose-700 hover:bg-rose-100 active:bg-rose-200/80 border border-rose-200/80',
    success:
      'bg-emerald-600 text-white shadow-xs hover:bg-emerald-700 active:bg-emerald-800 border border-emerald-600',
    successSubtle:
      'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 active:bg-emerald-200/80 border border-emerald-200/80',
    subtle:
      'bg-zinc-100/90 text-zinc-700 hover:bg-zinc-200/70 border border-transparent',
  };

  const sizeStyles = {
    xs: 'text-[11px] px-2.5 py-1 gap-1.5 min-h-[28px]',
    sm: 'text-xs px-3 py-1.5 gap-2 min-h-[34px]',
    md: 'text-xs px-3.5 py-2 gap-2 min-h-[38px]',
    lg: 'text-sm px-4 py-2.5 gap-2.5 min-h-[44px]',
  };

  const shapeStyles = shape === 'pill' ? 'rounded-full' : 'rounded-lg';

  return (
    <button
      type={type}
      disabled={disabled || isLoading}
      onClick={onClick}
      className={`${baseStyles} ${variantStyles[variant] || variantStyles.primary} ${
        sizeStyles[size] || sizeStyles.md
      } ${shapeStyles} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0 text-current" />
      ) : LeftIcon ? (
        typeof LeftIcon === 'function' || typeof LeftIcon === 'object' ? (
          <LeftIcon className="w-3.5 h-3.5 shrink-0 text-current" />
        ) : (
          LeftIcon
        )
      ) : null}
      <span>{children}</span>
      {!isLoading && RightIcon && (
        typeof RightIcon === 'function' || typeof RightIcon === 'object' ? (
          <RightIcon className="w-3.5 h-3.5 shrink-0 text-current" />
        ) : (
          RightIcon
        )
      )}
    </button>
  );
}

export default Button;
