// frontend/src/components/ui/Modal.tsx
// Built on the native <dialog>: focus trapping, Escape and the backdrop come free.
import { useEffect, useId, useRef, type ReactNode } from "react";

interface ModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  /** false = Escape and backdrop clicks do nothing (e.g. while saving). */
  dismissible?: boolean;
}

export function Modal({ open, title, onClose, children, footer, dismissible = true }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        if (dismissible) onClose();
      }}
      onClick={(e) => {
        if (dismissible && e.target === e.currentTarget) onClose();
      }}
    >
      {open && (
        <div className="modal__body">
          <h2 id={titleId} className="modal__title">
            {title}
          </h2>
          {children}
          {footer && <div className="modal__footer">{footer}</div>}
        </div>
      )}
    </dialog>
  );
}
