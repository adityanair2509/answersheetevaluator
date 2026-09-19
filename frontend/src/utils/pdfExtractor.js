// Lightweight client-side PDF text extractor without heavy external dependencies
export async function extractTextFromPdfBuffer(arrayBuffer) {
  try {
    const bytes = new Uint8Array(arrayBuffer);
    const sBuf = [115, 116, 114, 101, 97, 109]; // 'stream'
    let p = 0;
    let fullText = '';
    
    while (p < bytes.length - 10) {
      let match = true;
      for (let i = 0; i < 6; i++) {
        if (bytes[p + i] !== sBuf[i]) { match = false; break; }
      }
      if (!match) { p++; continue; }
      
      let start = p + 6;
      while (bytes[start] === 10 || bytes[start] === 13 || bytes[start] === 32) start++;
      
      let end = -1;
      for (let j = start; j < bytes.length - 9; j++) {
        if (bytes[j] === 101 && bytes[j+1] === 110 && bytes[j+2] === 100 && 
            bytes[j+3] === 115 && bytes[j+4] === 116 && bytes[j+5] === 114 && 
            bytes[j+6] === 101 && bytes[j+7] === 97 && bytes[j+8] === 109) {
          end = j;
          break;
        }
      }
      if (end === -1) break;
      
      let chunk = bytes.subarray(start, end);
      let flateBytes = chunk;
      
      // Check if ASCII85 encoded
      let endStr = '';
      for (let k = Math.max(0, chunk.length - 10); k < chunk.length; k++) endStr += String.fromCharCode(chunk[k]);
      if (endStr.includes('~>')) {
        let str = '';
        for (let k = 0; k < chunk.length; k++) {
          const c = chunk[k];
          if (c > 32) str += String.fromCharCode(c);
        }
        if (str.startsWith('<~')) str = str.slice(2);
        if (str.endsWith('~>')) str = str.slice(0, -2);
        const out = [];
        for (let i = 0; i < str.length; i += 5) {
          const c = str.slice(i, i + 5);
          if (c === 'z') { out.push(0,0,0,0); continue; }
          let val = 0;
          const pad = 5 - c.length;
          const fc = c + 'u'.repeat(pad);
          for (let j = 0; j < 5; j++) val = val * 85 + (fc.charCodeAt(j) - 33);
          out.push((val >>> 24) & 255, (val >>> 16) & 255, (val >>> 8) & 255, val & 255);
          if (pad > 0) out.splice(out.length - pad, pad);
        }
        flateBytes = new Uint8Array(out);
      }
      
      try {
        let decompBytes = null;
        if (typeof DecompressionStream !== 'undefined') {
          const stream = new Response(new Blob([flateBytes]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer();
          decompBytes = new Uint8Array(await stream);
        }
        
        if (decompBytes) {
          let decStr = '';
          for (let k = 0; k < decompBytes.length; k++) decStr += String.fromCharCode(decompBytes[k]);
          
          const tjMatches = decStr.match(/\((.*?)\)\s*Tj/g);
          if (tjMatches) {
            for (const m of tjMatches) {
              const t = m.replace(/\s*Tj$/, '').slice(1, -1).replace(/\\([\\()])/g, '$1');
              fullText += t;
            }
            fullText += '\n';
          }
        }
      } catch(e) {}
      p = end + 9;
    }
    return fullText.trim();
  } catch (err) {
    console.warn("Failed to extract PDF text:", err);
    return '';
  }
}
