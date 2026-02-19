// XPathGenie — shared utilities
// Key obfuscation (not encryption — just hides from casual DevTools inspection)
function obfuscateKey(key) { return btoa(key.split('').reverse().join('')); }
function deobfuscateKey(stored) { try { return atob(stored).split('').reverse().join(''); } catch { return ''; } }
