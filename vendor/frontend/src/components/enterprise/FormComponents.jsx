import React from 'react';
import { AlertCircle, Check } from 'lucide-react';

export function FormField({ label, required = false, error = '', helperText = '', children, className = '' }) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      {label && (
        <label className="block text-xs font-semibold text-zinc-800 tracking-tight">
          {label}
          {required && <span className="text-rose-500 ml-1 font-bold">*</span>}
        </label>
      )}
      {children}
      {error ? (
        <p className="flex items-center gap-1 text-[11px] font-medium text-rose-600">
          <AlertCircle className="w-3 h-3 shrink-0" />
          <span>{error}</span>
        </p>
      ) : helperText ? (
        <p className="text-[11px] text-zinc-500">{helperText}</p>
      ) : null}
    </div>
  );
}

export function Input({
  label,
  error,
  helperText,
  required,
  leftIcon: LeftIcon,
  rightIcon: RightIcon,
  className = '',
  id,
  ...props
}) {
  const inputEl = (
    <div className="relative">
      {LeftIcon && (
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none">
          {typeof LeftIcon === 'function' || typeof LeftIcon === 'object' ? (
            <LeftIcon className="w-4 h-4" />
          ) : (
            LeftIcon
          )}
        </div>
      )}
      <input
        id={id}
        className={`w-full bg-white border text-xs text-zinc-900 placeholder:text-zinc-400 rounded-lg shadow-xs transition-all focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 disabled:bg-zinc-50 disabled:text-zinc-400 disabled:cursor-not-allowed ${
          LeftIcon ? 'pl-9' : 'pl-3'
        } ${RightIcon ? 'pr-9' : 'pr-3'} py-2 min-h-[38px] ${
          error ? 'border-rose-400 focus:border-rose-600 focus:ring-rose-500/10' : 'border-zinc-300'
        } ${className}`}
        {...props}
      />
      {RightIcon && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400">
          {typeof RightIcon === 'function' || typeof RightIcon === 'object' ? (
            <RightIcon className="w-4 h-4" />
          ) : (
            RightIcon
          )}
        </div>
      )}
    </div>
  );

  if (label || error || helperText) {
    return (
      <FormField label={label} required={required} error={error} helperText={helperText}>
        {inputEl}
      </FormField>
    );
  }

  return inputEl;
}

export function Select({
  label,
  error,
  helperText,
  required,
  options = [],
  children,
  className = '',
  ...props
}) {
  const selectEl = (
    <select
      className={`w-full bg-white border text-xs text-zinc-900 rounded-lg shadow-xs py-2 px-3 min-h-[38px] transition-all focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 disabled:bg-zinc-50 disabled:cursor-not-allowed ${
        error ? 'border-rose-400 focus:border-rose-600' : 'border-zinc-300'
      } ${className}`}
      {...props}
    >
      {options.length > 0
        ? options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))
        : children}
    </select>
  );

  if (label || error || helperText) {
    return (
      <FormField label={label} required={required} error={error} helperText={helperText}>
        {selectEl}
      </FormField>
    );
  }

  return selectEl;
}

export function Textarea({
  label,
  error,
  helperText,
  required,
  rows = 3,
  className = '',
  ...props
}) {
  const textareaEl = (
    <textarea
      rows={rows}
      className={`w-full bg-white border text-xs text-zinc-900 placeholder:text-zinc-400 rounded-lg shadow-xs py-2.5 px-3 transition-all focus:outline-none focus:ring-2 focus:ring-zinc-950/10 focus:border-zinc-900 disabled:bg-zinc-50 disabled:cursor-not-allowed ${
        error ? 'border-rose-400 focus:border-rose-600' : 'border-zinc-300'
      } ${className}`}
      {...props}
    />
  );

  if (label || error || helperText) {
    return (
      <FormField label={label} required={required} error={error} helperText={helperText}>
        {textareaEl}
      </FormField>
    );
  }

  return textareaEl;
}

export function Checkbox({ label, description, checked, onChange, disabled, className = '', id, ...props }) {
  return (
    <label
      htmlFor={id}
      className={`flex items-start gap-2.5 cursor-pointer select-none ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${className}`}
    >
      <div className="relative flex items-center justify-center mt-0.5">
        <input
          type="checkbox"
          id={id}
          checked={checked}
          onChange={onChange}
          disabled={disabled}
          className="peer sr-only"
          {...props}
        />
        <div className="w-4 h-4 rounded-md border border-zinc-300 bg-white peer-checked:bg-zinc-900 peer-checked:border-zinc-900 peer-focus-visible:ring-2 peer-focus-visible:ring-zinc-950/20 transition-all flex items-center justify-center text-white">
          <Check className="w-3 h-3 opacity-0 peer-checked:opacity-100 transition-opacity stroke-[3]" />
        </div>
      </div>
      {(label || description) && (
        <div className="text-xs">
          {label && <span className="font-medium text-zinc-900">{label}</span>}
          {description && <p className="text-[11px] text-zinc-500 mt-0.5">{description}</p>}
        </div>
      )}
    </label>
  );
}

export function Switch({ checked, onChange, label, disabled, className = '' }) {
  return (
    <label
      className={`inline-flex items-center gap-3 cursor-pointer select-none ${
        disabled ? 'opacity-50 cursor-not-allowed' : ''
      } ${className}`}
    >
      <div className="relative inline-flex items-center">
        <input
          type="checkbox"
          checked={checked}
          onChange={onChange}
          disabled={disabled}
          className="sr-only peer"
        />
        <div className="w-9 h-5 bg-zinc-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-zinc-900"></div>
      </div>
      {label && <span className="text-xs font-medium text-zinc-800">{label}</span>}
    </label>
  );
}

export function Badge({ children, variant = 'neutral', size = 'sm', className = '' }) {
  const variantStyles = {
    neutral: 'bg-zinc-100 text-zinc-800 border-zinc-200/80',
    dark: 'bg-zinc-900 text-white border-zinc-900',
    outline: 'bg-transparent text-zinc-700 border-zinc-300',
    emerald: 'bg-emerald-50 text-emerald-800 border-emerald-200/80',
    amber: 'bg-amber-50 text-amber-800 border-amber-200/80',
    rose: 'bg-rose-50 text-rose-800 border-rose-200/80',
    sky: 'bg-sky-50 text-sky-800 border-sky-200/80',
  };

  const sizeStyles = {
    xs: 'px-1.5 py-0.5 text-[10px]',
    sm: 'px-2.5 py-0.5 text-[11px]',
    md: 'px-3 py-1 text-xs',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold rounded-full border tracking-wide uppercase ${
        variantStyles[variant] || variantStyles.neutral
      } ${sizeStyles[size] || sizeStyles.sm} ${className}`}
    >
      {children}
    </span>
  );
}
