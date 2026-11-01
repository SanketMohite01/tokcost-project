export default function ProviderIcon({ platform, size = 28 }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 32 32",
    "aria-hidden": true,
  };

  if (platform === "chatgpt") {
    return (
      <svg {...common} className="provider-icon">
        <circle cx="16" cy="16" r="14" fill="currentColor" opacity="0.12" />
        <path
          d="M16 7c4.5 0 7.5 2.7 7.5 6.4 0 2.6-1.5 4.4-3.8 5.2v.1c2.8.6 4.8 2.9 4.8 5.8 0 3.6-3.4 6.5-8.5 6.5S7.5 29.1 7.5 25.5c0-2.9 2-5.2 4.8-5.8v-.1C10 17.8 8.5 16 8.5 13.4 8.5 9.7 11.5 7 16 7z"
          fill="currentColor"
        />
      </svg>
    );
  }

  if (platform === "claude") {
    return (
      <svg {...common} className="provider-icon">
        <rect x="5" y="5" width="22" height="22" rx="6" fill="currentColor" opacity="0.12" />
        <path
          d="M11 21l5-10 5 10h-3l-1.2-2.4H15.2L14 21h-3zm3.2-5.6h3.6L16 12.8l-1.8 2.6z"
          fill="currentColor"
        />
      </svg>
    );
  }

  return (
    <svg {...common} className="provider-icon">
      <polygon
        points="16,6 24,12 20,26 12,26 8,12"
        fill="currentColor"
        opacity="0.15"
      />
      <circle cx="16" cy="16" r="5" fill="currentColor" />
    </svg>
  );
}
