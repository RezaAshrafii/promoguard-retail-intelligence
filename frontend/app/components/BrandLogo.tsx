type BrandLogoProps = {
  size?: number;
  showWordmark?: boolean;
};

export function BrandLogo({ size = 44, showWordmark = true }: BrandLogoProps) {
  return (
    <div className="brand-lockup" aria-label="PromoGuard">
      <svg className="brand-symbol" width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="PromoGuard shield">
        <defs>
          <linearGradient id="pg-brand-gradient" x1="7" y1="58" x2="57" y2="6" gradientUnits="userSpaceOnUse">
            <stop stopColor="#1A9DF2" />
            <stop offset="0.52" stopColor="#14D4C0" />
            <stop offset="1" stopColor="#39E39F" />
          </linearGradient>
        </defs>
        <path d="M32 4 55 12v19c0 14-8.8 23.7-23 29C17.8 54.7 9 45 9 31V12L32 4Z" fill="url(#pg-brand-gradient)" />
        <path d="M32 14 46 19v12c0 8.3-4.8 14.6-14 18.7C22.8 45.6 18 39.3 18 31V19l14-5Z" fill="#07131C" />
        <path d="M28 25h7.2c5.5 0 9.2 3 9.2 7.6 0 4.2-3.2 7-8.3 7h-3v9.2H28V25Zm5.1 4.5v5.7h2.5c2 0 3.1-1 3.1-2.9 0-1.8-1.1-2.8-3.1-2.8h-2.5Z" fill="url(#pg-brand-gradient)" />
      </svg>
      {showWordmark && <div className="brand-wordmark"><strong>Promo<span>Guard</span></strong><small>Retail intelligence</small></div>}
    </div>
  );
}
