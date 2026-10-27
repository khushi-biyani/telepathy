export function SectionHead({ label, title, sub }: { label: string; title: React.ReactNode; sub?: React.ReactNode }) {
  return (
    <div className="mb-10 max-w-2xl">
      <div className="label mb-3">{label}</div>
      <h2 className="text-[30px] font-medium leading-[1.12] tracking-[-0.025em] sm:text-[38px]">{title}</h2>
      {sub && <p className="mt-4 text-[17px] leading-relaxed text-muted">{sub}</p>}
    </div>
  );
}
