import React, { createContext, useContext, useEffect, useState } from 'react';

const ThemeContext = createContext({ theme: 'light', setTheme: () => {} });

export function ThemeProvider({ children }) {
  // Always use light mode - dark mode is disabled
  const theme = 'light';
  const setTheme = () => {
    // Theme changing is disabled - do nothing
    console.log('Theme changing is disabled - light mode only');
  };

  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    
    // Force light mode always
    html.setAttribute('data-theme', 'light');
    html.classList.remove('dark');
    html.classList.add('light');
    body.classList.remove('dark');
    body.classList.add('light');
    
    try { 
      localStorage.setItem('theme', 'light'); 
    } catch (e) {}
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  return useContext(ThemeContext);
}
