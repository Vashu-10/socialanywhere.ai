import { useState, useEffect } from "react";

function ThemeToggle() {
  // Always show light mode (moon icon) since dark mode is disabled
  const isDark = false;

  const toggleTheme = (e) => {
    e.preventDefault();
    e.stopPropagation();
    // Theme toggle is disabled - do nothing but show a message
    console.log('Theme toggle clicked - Dark mode is currently disabled');
  };

  // Force light mode always
  useEffect(() => {
    // Always set light mode
    document.documentElement.classList.remove('dark');
    document.body.classList.remove('dark');
    document.documentElement.setAttribute('data-theme', 'light');
    localStorage.setItem('theme', 'light');
  }, []);

  return (
    <button
      onClick={toggleTheme}
      className="w-12 h-12 rounded-2xl bg-gray-400 hover:bg-gray-500 flex items-center justify-center hover:scale-105 transition-all duration-300 cursor-not-allowed shadow-lg opacity-60"
      style={{
        pointerEvents: 'auto',
        zIndex: 9999,
        position: 'relative'
      }}
      title="Dark mode is currently disabled"
    >
      {isDark ? (
        // Sun icon for light mode
        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
      ) : (
        // Moon icon for dark mode
        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      )}
    </button>
  );
}

export default ThemeToggle;
