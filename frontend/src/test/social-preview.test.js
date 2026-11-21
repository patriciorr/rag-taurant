import { Buffer } from 'node:buffer';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('social preview metadata', () => {
  it('points to a public PNG with matching dimensions', () => {
    const html = readFileSync('index.html', 'utf8');
    const document = new DOMParser().parseFromString(html, 'text/html');
    const meta = (property) =>
      document.querySelector(`meta[property="${property}"]`)?.getAttribute('content');
    const siteUrl = new URL(meta('og:url'));
    const imageUrl = new URL(meta('og:image'));
    const image = readFileSync(join('public', imageUrl.pathname));

    expect(siteUrl.protocol).toBe('https:');
    expect(imageUrl.origin).toBe(siteUrl.origin);
    expect(meta('og:title')).toBeTruthy();
    expect(meta('og:description')).toBeTruthy();
    expect(meta('og:image:alt')).toBeTruthy();
    expect(meta('og:image:type')).toBe('image/png');
    expect(image.subarray(0, 8)).toEqual(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]));
    expect(image.readUInt32BE(16)).toBe(Number(meta('og:image:width')));
    expect(image.readUInt32BE(20)).toBe(Number(meta('og:image:height')));
  });
});
