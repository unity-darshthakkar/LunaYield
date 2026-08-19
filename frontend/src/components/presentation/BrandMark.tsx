type BrandMarkProps = {
  className?: string;
  compact?: boolean;
};

export function BrandMark({ className = 'h-10 w-10', compact = false }: BrandMarkProps) {
  return (
    <img
      src="/logo.png"
      alt={compact ? 'LunaYield logo' : 'LunaYield Mission Lab logo'}
      className={`${className} object-contain`}
      loading="eager"
      decoding="async"
    />
  );
}
