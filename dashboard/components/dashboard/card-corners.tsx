export function CardCorners() {
  return (
    <div className="pointer-events-none absolute inset-0 z-10" aria-hidden>
      <div className="absolute left-0 top-0 size-3 border-l-2 border-t-2 border-white/50" />
      <div className="absolute right-0 top-0 size-3 border-r-2 border-t-2 border-white/50" />
      <div className="absolute left-0 bottom-0 size-3 border-l-2 border-b-2 border-white/50" />
      <div className="absolute right-0 bottom-0 size-3 border-r-2 border-b-2 border-white/50" />
    </div>
  );
}
