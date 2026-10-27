import type { ReactNode } from "react";

/** A closed-by-default section, so detail is there when wanted and out of the way otherwise. */
export function Accordion({ title, children, open }: { title: string; children: ReactNode; open?: boolean }) {
  return (
    <details open={open} className="group rounded-2xl border border-hair bg-surface">
      <summary className="flex items-center justify-between gap-3 px-5 py-4 text-[15px] font-medium">
        {title}
        <svg className="chev h-4 w-4 shrink-0 text-muted transition-transform" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M6 3l5 5-5 5" /></svg>
      </summary>
      <div className="border-t border-hair px-5 py-4 text-sm leading-relaxed text-ink2">{children}</div>
    </details>
  );
}
