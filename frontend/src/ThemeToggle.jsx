import { useEffect, useState } from "react";

const STORAGE_KEY = "tokcost_theme";

function systemTheme() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function initTheme() {
  const saved = localStorage.getItem(STORAGE_KEY);
  const theme = saved === "light" || saved === "dark" ? saved : systemTheme();
  document.documentElement.setAttribute("data-theme", theme);
  return saved;
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState(() => {
    return document.documentElement.getAttribute("data-theme") || systemTheme();
  });

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    function onChange() {
      if (!localStorage.getItem(STORAGE_KEY)) {
        const next = mq.matches ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", next);
        setTheme(next);
      }
    }
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    localStorage.setItem(STORAGE_KEY, next);
    document.documentElement.setAttribute("data-theme", next);
    setTheme(next);
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={theme === "dark" ? "Light mode" : "Dark mode"}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
