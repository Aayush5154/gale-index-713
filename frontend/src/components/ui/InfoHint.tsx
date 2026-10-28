import { HelpCircle } from "lucide-react";

export function InfoHint({ text }: { text: string }) {
  return (
    <span
      className="inline-flex cursor-help items-center text-faint transition-colors hover:text-muted focus-visible:text-muted focus-visible:outline-none"
      title={text}
      aria-label={text}
      tabIndex={0}
      role="note"
    >
      <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
    </span>
  );
}
