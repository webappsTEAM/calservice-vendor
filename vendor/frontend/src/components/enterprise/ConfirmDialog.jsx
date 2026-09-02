import React from 'react';
import { Modal } from './Modal.jsx';
import { Button } from './Button.jsx';
import { AlertTriangle, AlertCircle, HelpCircle } from 'lucide-react';

export function ConfirmDialog({
  isOpen = false,
  onClose = () => {},
  onConfirm = () => {},
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed with this action?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'primary', // 'primary', 'danger', 'warning'
  isLoading = false,
}) {
  const icon =
    confirmVariant === 'danger'
      ? AlertCircle
      : confirmVariant === 'warning'
      ? AlertTriangle
      : HelpCircle;

  const btnVariant =
    confirmVariant === 'danger'
      ? 'danger'
      : confirmVariant === 'warning'
      ? 'primary'
      : 'primary';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      icon={icon}
      maxWidth="max-w-md"
      footer={
        <>
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={isLoading}
          >
            {cancelText}
          </Button>
          <Button
            variant={btnVariant}
            size="sm"
            onClick={onConfirm}
            isLoading={isLoading}
          >
            {confirmText}
          </Button>
        </>
      }
    >
      <p className="text-xs text-zinc-600 leading-relaxed">{message}</p>
    </Modal>
  );
}

export default ConfirmDialog;

