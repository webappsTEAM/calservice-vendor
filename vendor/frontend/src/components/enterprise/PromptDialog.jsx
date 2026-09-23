import React, { useEffect, useState } from 'react';
import { Modal } from './Modal.jsx';
import { Button } from './Button.jsx';
import { MessageSquare } from 'lucide-react';

/**
 * Asks for one value before an action goes ahead.
 *
 * This replaces `prompt()`, which was still handling rejection reasons that
 * land in a permanent audit trail and, in one case, the rupee amount an admin
 * approves for a work extension. A native prompt gives a single unstyled line
 * with no validation, no context about what is being decided, no way to make
 * an answer mandatory, and it freezes the whole tab while it is open. On the
 * amount field that was a real correctness problem: whatever was typed went
 * straight to `parseFloat`, so "5,000" or "₹5000" became NaN and was sent.
 *
 * Deliberate behaviour:
 *
 * - `required` blocks confirmation on an empty answer rather than silently
 *   substituting a default, which is what the old code did with reasons.
 * - `type="amount"` accepts only a positive number and says so before the
 *   request is made.
 * - Enter confirms on a single-line field; Escape cancels. Both are what the
 *   native prompt did, and admins reject in batches.
 */
export function PromptDialog({
  isOpen = false,
  onClose = () => {},
  onSubmit = () => {},
  title = '',
  message = '',
  label = '',
  placeholder = '',
  initialValue = '',
  type = 'textarea', // 'textarea' | 'text' | 'amount'
  required = true,
  confirmText = 'Confirm',
  confirmVariant = 'primary',
  isLoading = false,
  helpText = '',
}) {
  const [value, setValue] = useState(initialValue);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setValue(initialValue == null ? '' : String(initialValue));
      setTouched(false);
    }
  }, [isOpen, initialValue]);

  const trimmed = String(value).trim();

  let problem = '';
  if (required && !trimmed) {
    problem = 'This is required.';
  } else if (type === 'amount' && trimmed) {
    const numeric = Number(trimmed.replace(/[₹,\s]/g, ''));
    if (!Number.isFinite(numeric)) problem = 'Enter a number, for example 4500.';
    else if (numeric <= 0) problem = 'The amount must be greater than zero.';
  }

  const submit = () => {
    setTouched(true);
    if (problem) return;
    if (type === 'amount') {
      onSubmit(trimmed ? Number(trimmed.replace(/[₹,\s]/g, '')) : null);
    } else {
      onSubmit(trimmed);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && type !== 'textarea' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      icon={MessageSquare}
      maxWidth="max-w-md"
      footer={
        <>
          <Button variant="outline" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            variant={confirmVariant === 'danger' ? 'danger' : 'primary'}
            size="sm"
            onClick={submit}
            isLoading={isLoading}
            disabled={Boolean(problem)}
          >
            {confirmText}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        {message && <p className="text-xs text-zinc-600 leading-relaxed">{message}</p>}

        <label className="block">
          {label && (
            <span className="block text-[11px] font-semibold text-zinc-700 mb-1">{label}</span>
          )}
          {type === 'textarea' ? (
            <textarea
              autoFocus
              rows={3}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onBlur={() => setTouched(true)}
              placeholder={placeholder}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-900/10"
            />
          ) : (
            <div className="relative">
              {type === 'amount' && (
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-zinc-500">
                  &#8377;
                </span>
              )}
              <input
                autoFocus
                type="text"
                inputMode={type === 'amount' ? 'decimal' : 'text'}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onBlur={() => setTouched(true)}
                onKeyDown={onKeyDown}
                placeholder={placeholder}
                className={`w-full rounded-lg border border-zinc-300 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-zinc-900/10 ${
                  type === 'amount' ? 'pl-7 pr-3' : 'px-3'
                }`}
              />
            </div>
          )}
        </label>

        {touched && problem ? (
          <p className="text-[11px] text-rose-700">{problem}</p>
        ) : helpText ? (
          <p className="text-[11px] text-zinc-500">{helpText}</p>
        ) : null}
      </div>
    </Modal>
  );
}

export default PromptDialog;
