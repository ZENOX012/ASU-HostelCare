/**
 * ASU HostelCare — Client-Side Anti-Inspect & Source Code Protection
 * Safeguards front-facing interfaces against unauthorized scraping, inspection & source dumping.
 */
(function () {
  'use strict';

  // 1. Disable Right-Click Context Menu
  document.addEventListener('contextmenu', function (e) {
    // Allow right click ONLY inside input and textarea for paste/copy convenience
    const tag = e.target && e.target.tagName ? e.target.tagName.toLowerCase() : '';
    if (tag === 'input' || tag === 'textarea') {
      return true;
    }
    e.preventDefault();
    return false;
  }, false);

  // 2. Block DevTools & Source Inspect Keyboard Shortcuts
  document.addEventListener('keydown', function (e) {
    // F12 (Developer Tools)
    if (e.key === 'F12' || e.keyCode === 123) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }

    // Ctrl+Shift+I or Cmd+Opt+I (Inspect)
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'I' || e.key === 'i' || e.keyCode === 73)) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }

    // Ctrl+Shift+J or Cmd+Opt+J (Console)
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'J' || e.key === 'j' || e.keyCode === 74)) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }

    // Ctrl+Shift+C (Inspect Element)
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'C' || e.key === 'c' || e.keyCode === 67)) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }

    // Ctrl+U or Cmd+Opt+U (View Page Source)
    if ((e.ctrlKey || e.metaKey) && (e.key === 'U' || e.key === 'u' || e.keyCode === 85)) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }

    // Ctrl+S or Cmd+S (Save Complete Webpage)
    if ((e.ctrlKey || e.metaKey) && (e.key === 'S' || e.key === 's' || e.keyCode === 83)) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }
  }, false);

  // 3. Console Warning Notice
  try {
    const bannerStyle = 'color: #c59b27; font-size: 20px; font-weight: bold; font-family: serif;';
    const warningStyle = 'color: #ef4444; font-size: 13px; font-weight: bold;';
    console.log('%c🏛️ ASU HostelCare — Apeejay Stya University', bannerStyle);
    console.log('%c⚠️ SECURITY NOTICE: Unauthorized inspection, source reproduction, or scraping is monitored.', warningStyle);
  } catch (err) {}
})();
