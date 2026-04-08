import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';
import { fileURLToPath } from 'url';
import { copyFileSync, mkdirSync, existsSync, readdirSync, statSync, readFileSync, writeFileSync } from 'fs';
import type { Plugin } from 'vite';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

// Plugin to bundle content script dependencies into a single file
// Background script can use ES modules, so we keep chunks for it
function bundleContentScript(): Plugin {
  let chunkMap: Map<string, string> = new Map();
  
  return {
    name: 'bundle-content-script',
    generateBundle(options, bundle) {
      // Store chunk code for later inlining
      for (const chunk of Object.values(bundle)) {
        if (chunk.type === 'chunk' && chunk.fileName) {
          if (chunk.fileName.includes('constants') || 
              chunk.fileName.includes('url-builder') || 
              chunk.fileName.includes('metadata-extractor')) {
            chunkMap.set(chunk.fileName, chunk.code);
          }
        }
      }
    },
    renderChunk(code, chunk, options) {
      // Only process content script chunk
      if (chunk.name !== 'content/metadata-checker') {
        return null; // Use default rendering
      }
      
      // Find chunks that should be inlined
      const chunksToInline: Array<{ fileName: string; code: string }> = [];
      for (const [fileName, chunkCode] of Array.from(chunkMap.entries())) {
        // Check if content script imports this chunk
        if (code.includes(fileName)) {
          chunksToInline.push({ fileName, code: chunkCode });
        }
      }
      
      if (chunksToInline.length === 0) {
        // Still remove imports
        return code.replace(/import\s*\{[^}]*\}\s*from\s*['"][^'"]+['"];?/g, '');
      }
      
      // Inline chunk code before minification
      // The chunk code is already minified, so we need to extract the actual values
      // and create const declarations with the original names that content script uses
      let inlinedCode = '';
      for (const chunk of chunksToInline) {
        let chunkCode = chunk.code;
        
        // If this is the constants chunk, we need to extract values and create proper declarations
        if (chunk.fileName.includes('constants')) {
          // Extract the const declarations from the minified code
          // Format: const E="...",T=...,_=...,A={...},...
          const constMatch = chunkCode.match(/^const\s+([^=]+)=(.+?);export/);
          if (constMatch) {
            const declarations = constMatch[1];
            const values = constMatch[2];
            
            // Parse the declarations and create mappings
            // The exports tell us the mapping: export{L as A,E as B,...}
            const exportMatch = chunkCode.match(/export\s*\{([^}]+)\}/);
            if (exportMatch) {
              // Parse export aliases: L as A, E as B, s as Y, S as a
              // We need to map back to original names
              // For now, let's just inline the const declarations and remove exports
              // The minifier will handle the rest
              chunkCode = chunkCode.replace(/export\s*\{[^}]+\};?/g, '');
            } else {
              chunkCode = chunkCode.replace(/export\s*\{[^}]+\};?/g, '');
            }
          } else {
            // Fallback: just remove exports
            chunkCode = chunkCode.replace(/export\s*\{[^}]+\};?/g, '');
          }
        } else {
          // For other chunks, just remove exports
          chunkCode = chunkCode.replace(/export\s*\{[^}]+\};?/g, '');
        }
        
        inlinedCode += chunkCode + '\n';
      }
      
      // Prepend inlined code
      let result = inlinedCode + code;
      
      // Remove import statements
      for (const chunk of chunksToInline) {
        const chunkName = chunk.fileName.split('/').pop() || chunk.fileName;
        const patterns = [
          new RegExp(`import\\s*\\{[^}]*\\}\\s*from\\s*['"]\\.\\./assets/${chunkName.replace(/\.js$/, '')}[^'"]*['"];?`, 'g'),
          new RegExp(`import\\s*\\{[^}]*\\}\\s*from\\s*['"]\\.\\./assets/${chunkName}['"];?`, 'g'),
          new RegExp(`import\\s*\\{[^}]*\\}\\s*from\\s*['"]${chunk.fileName}['"];?`, 'g'),
        ];
        
        for (const pattern of patterns) {
          result = result.replace(pattern, '');
        }
      }
      
      // Remove any remaining imports
      result = result.replace(/import\s*\{[^}]*\}\s*from\s*['"][^'"]+['"];?/g, '');
      
      return result;
    },
    async writeBundle(options) {
      // After bundle is written, wrap content script in IIFE and clean up
      const contentScriptPath = resolve(options.dir || 'dist', 'content/metadata-checker.js');
      if (!existsSync(contentScriptPath)) return;
      
      let code = readFileSync(contentScriptPath, 'utf-8');
      
      // Remove any remaining import/export statements
      code = code.replace(/import\s*\{[^}]*\}\s*from\s*['"][^'"]+['"];?/g, '');
      code = code.replace(/export\s*\{[^}]+\};?/g, '');
      
      // If constants are referenced but not defined, inline them from the chunk file
      if (code.includes('YOUTUBE_HOSTNAME') || code.includes('YOUTUBE_WATCH_PATH') || 
          code.includes('METADATA_CACHE_TTL') || code.includes('CONFIDENCE_THRESHOLD') ||
          code.includes('MESSAGE_TYPES') || code.includes('NAVIGATION_CHECK_DELAY')) {
        // Find and read the constants chunk file
        const assetsDir = resolve(options.dir || 'dist', 'assets');
        if (existsSync(assetsDir)) {
          const files = readdirSync(assetsDir);
          const constantsFile = files.find(f => f.includes('constants'));
          if (constantsFile) {
            const constantsPath = resolve(assetsDir, constantsFile);
            const constantsCode = readFileSync(constantsPath, 'utf-8');
            
            // Extract the const declarations from minified constants chunk
            // Format: const E="...",T=...,_=...,A={...},s="...",S="...",C=...
            // We need to map these to: YOUTUBE_HOSTNAME, YOUTUBE_WATCH_PATH, etc.
            // The export tells us: export{...s as Y,S as a,...} means s->YOUTUBE_HOSTNAME, S->YOUTUBE_WATCH_PATH
            // Based on constants.ts: s="www.youtube.com" (Y), S="/watch" (a), C=1000 (NAVIGATION_CHECK_DELAY)
            // T=300000 (METADATA_CACHE_TTL), _=0.5 (CONFIDENCE_THRESHOLD), A=MESSAGE_TYPES, L=ALARM_NAMES, R=STORAGE_KEYS
            
            // Extract const values
            const constMatch = constantsCode.match(/^const\s+([^=]+)=(.+?);export/);
            if (constMatch) {
              // For simplicity, just prepend the constants with proper names
              // We'll extract s, S, T, _, A, C and map them
              const constDecl = constMatch[1].trim();
              const constVals = constMatch[2].trim();
              
              // Parse the declarations: E,T,_,A,L,R,s,S,U,C
              // And create mappings based on export: s as Y (YOUTUBE_HOSTNAME), S as a (YOUTUBE_WATCH_PATH)
              // Create const declarations with original names
              const constantsDecl = `const EXTENSION_VERBOSE_LOGS=!1,YOUTUBE_HOSTNAME="www.youtube.com",YOUTUBE_WATCH_PATH="/watch",METADATA_CACHE_TTL=3e5,CONFIDENCE_THRESHOLD=.5,MESSAGE_TYPES={GENERATE_RULES:"GENERATE_RULES",GET_RULES:"GET_RULES",GET_ACTIVE_RULES:"GET_ACTIVE_RULES",SAVE_RULE:"SAVE_RULE",TOGGLE_RULE:"TOGGLE_RULE",DELETE_RULE:"DELETE_RULE",CHECK_METADATA:"CHECK_METADATA",REDIRECT_TO_BLOCKED:"REDIRECT_TO_BLOCKED"},ALARM_NAMES={EVALUATE_RULES:"evaluateRules"},STORAGE_KEYS={RULES:"rules"},DAY_NAMES=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],NAVIGATION_CHECK_DELAY=1e3;`;
              
              // Prepend constants before the code
              code = constantsDecl + '\n' + code;
            }
          }
        }
      }
      
      // Also check for buildBlockedUrl function - it might be minified to a different name
      // Find the minified function name and replace buildBlockedUrl references
      if (code.includes('buildBlockedUrl')) {
        // The function is likely already inlined but with a minified name
        // Find the function definition pattern: function X(e){...chrome.runtime.getURL("blocked.html")...}
        const funcMatch = code.match(/function\s+(\w+)\s*\([^)]*\)\s*\{[^}]*chrome\.runtime\.getURL\(["']blocked\.html["'][^}]*\}/);
        if (funcMatch) {
          const minifiedName = funcMatch[1];
          // Replace all buildBlockedUrl calls with the minified name
          code = code.replace(/\bbuildBlockedUrl\s*\(/g, `${minifiedName}(`);
        } else {
          // If not found, try to inline from url-builder chunk
          const assetsDir = resolve(options.dir || 'dist', 'assets');
          if (existsSync(assetsDir)) {
            const files = readdirSync(assetsDir);
            const urlBuilderFile = files.find(f => f.includes('url-builder'));
            if (urlBuilderFile) {
              const urlBuilderPath = resolve(assetsDir, urlBuilderFile);
              const urlBuilderCode = readFileSync(urlBuilderPath, 'utf-8');
              // Extract function and inline with original name
              const funcMatch = urlBuilderCode.match(/function\s+(\w+)\s*\([^)]*\)\s*\{[^}]+\}/);
              if (funcMatch) {
                let funcCode = urlBuilderCode.replace(/export\s*\{[^}]+\};?/g, '');
                // Rename the function to buildBlockedUrl
                funcCode = funcCode.replace(/function\s+\w+\s*\(/, 'function buildBlockedUrl(');
                code = funcCode + '\n' + code;
              }
            }
          }
        }
      }
      
      // Fix duplicate declarations created by minification
      // Simple approach: find conflicts and rename function declarations (keep const/let/var)
      // This handles the common case where a constant and function get the same minified name
      const conflicts = new Set<string>();
      const constPattern = /\bconst\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\b/g;
      const funcPattern = /\bfunction\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(/g;
      
      const constNames = new Set<string>();
      let match;
      while ((match = constPattern.exec(code)) !== null) {
        constNames.add(match[1]);
      }
      
      // Find functions that conflict with const names
      while ((match = funcPattern.exec(code)) !== null) {
        if (constNames.has(match[1])) {
          conflicts.add(match[1]);
        }
      }
      
      // Rename conflicting functions and their calls
      for (const conflictName of Array.from(conflicts)) {
        const newName = `${conflictName}Fn`;
        // Replace function declaration
        code = code.replace(
          new RegExp(`\\bfunction\\s+${conflictName}\\s*\\(`, 'g'),
          `function ${newName}(`
        );
        // Replace function calls (but not the declaration we just replaced)
        // This is a simple approach - replace all occurrences that aren't part of a declaration
        code = code.replace(
          new RegExp(`\\b${conflictName}\\s*\\(`, 'g'),
          `${newName}(`
        );
      }
      
      // Wrap in IIFE to isolate scope (content scripts can't use ES modules)
      writeFileSync(contentScriptPath, `(function() {\n${code}\n})();`);
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    bundleContentScript(),
    {
      name: 'copy-files',
      closeBundle() {
        // Copy manifest.json
        const manifestSrc = resolve(__dirname, 'manifest.json');
        const manifestDest = resolve(__dirname, 'dist', 'manifest.json');
        if (existsSync(manifestSrc)) {
          copyFileSync(manifestSrc, manifestDest);
        }

        // Copy icons
        const iconsSrc = resolve(__dirname, 'icons');
        const iconsDest = resolve(__dirname, 'dist', 'icons');
        if (existsSync(iconsSrc)) {
          mkdirSync(iconsDest, { recursive: true });
          readdirSync(iconsSrc).forEach(file => {
            const src = resolve(iconsSrc, file);
            const dest = resolve(iconsDest, file);
            if (statSync(src).isFile()) {
              copyFileSync(src, dest);
            }
          });
        }

        // Copy blocked.html and blocked.js
        const blockedHtmlSrc = resolve(__dirname, 'src', 'blocked.html');
        const blockedHtmlDest = resolve(__dirname, 'dist', 'blocked.html');
        if (existsSync(blockedHtmlSrc)) {
          copyFileSync(blockedHtmlSrc, blockedHtmlDest);
        }
        const blockedJsSrc = resolve(__dirname, 'src', 'blocked.js');
        const blockedJsDest = resolve(__dirname, 'dist', 'blocked.js');
        if (existsSync(blockedJsSrc)) {
          copyFileSync(blockedJsSrc, blockedJsDest);
        }
      },
    },
  ],
  build: {
    outDir: 'dist',
    minify: 'esbuild', // Use esbuild for minification (default)
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'popup.html'),
        background: resolve(__dirname, 'src/background/background.ts'),
        'content/metadata-checker': resolve(__dirname, 'src/content/metadata-checker.ts'),
      },
      output: {
        format: 'es',
        entryFileNames: (chunkInfo) => {
          if (chunkInfo.name === 'background') return 'background.js';
          if (chunkInfo.name === 'content/metadata-checker') return 'content/metadata-checker.js';
          return 'assets/[name]-[hash].js';
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        // Prevent chunking for content script dependencies - inline them directly
        // Background/popup can use ES modules and chunks normally
        manualChunks: (id, { getModuleInfo }) => {
          // Only create vendor chunks for node_modules
          if (id.includes('node_modules')) {
            return 'vendor';
          }
          // For constants, url-builder, metadata-extractor - check who imports them
          if (id.includes('constants') || id.includes('url-builder') || id.includes('metadata-extractor')) {
            const moduleInfo = getModuleInfo(id);
            if (moduleInfo) {
              const importers = moduleInfo.importers || [];
              const isImportedByContentScript = importers.some(imp => imp.includes('content/metadata-checker'));
              const isImportedByBackground = importers.some(imp => imp.includes('background'));
              const isImportedByPopup = importers.some(imp => imp.includes('popup'));
              
              // If content script imports it, inline it (return null) so it's bundled directly
              // This prevents chunking and ensures variable names match after minification
              if (isImportedByContentScript) {
                return null; // Inline into content script - no separate chunk
              }
              // If only background/popup use it, create chunk normally
              // (Background/popup can use ES modules)
            }
          }
        },
        assetFileNames: (assetInfo) => {
          if (assetInfo.name === 'popup.html' || assetInfo.name === 'blocked.html') {
            return '[name][extname]';
          }
          return 'assets/[name]-[hash].[ext]';
        },
      },
    },
  },
});

