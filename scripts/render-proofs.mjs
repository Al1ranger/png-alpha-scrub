import assert from 'node:assert/strict';
import fs from 'node:fs';

const repo = 'https://github.com/Al1ranger/png-alpha-scrub';
const explorer = 'https://explorer-studio.genlayer.com';
const proof = JSON.parse(fs.readFileSync('PROOFS.json', 'utf8'));
assert(proof.verified && proof.source.source_match && proof.unknown_png_reverted);
assert.match(proof.address, /^0x[a-fA-F0-9]{40}$/);
assert.match(proof.source_commit, /^[a-f0-9]{40}$/);
assert.deepEqual(proof.transactions.map(entry => entry.step), [
  'deploy', 'alpha-original', 'alpha-variant', 'visible-change',
]);

const rows = proof.transactions.map(({step, hash, receipt}) => {
  assert.match(hash, /^0x[a-f0-9]{64}$/);
  assert.equal(receipt.status, 'FINALIZED');
  assert.equal(receipt.execution, 'SUCCESS');
  assert.equal(receipt.consensus, 'MAJORITY_AGREE');
  assert(receipt.committed && receipt.agree_votes >= 2 && receipt.leader_only === false);
  const example = proof.examples[step];
  assert.equal(Boolean(example), step !== 'deploy');
  return {
    tx: `[${step}](${explorer}/tx/${hash})`,
    votes: receipt.agree_votes,
    report: example?.id,
    png: example?.report.png_id,
  };
});
assert.notEqual(rows[1].report, rows[2].report);
assert.equal(rows[1].png, rows[2].png);
assert.notEqual(rows[1].png, rows[3].png);

const address = `[StudioNet contract](${explorer}/address/${proof.address})`;
const source = `[Deployed source](${repo}/blob/${proof.source_commit}/contracts/PngAlphaScrub.py)`;
const fixtures = `[Pinned fixtures](${repo}/tree/${proof.source_commit}/fixtures)`;
const evidence = `[Receipt and readback data](${repo}/blob/main/PROOFS.json)`;
const ledger = [
  '# StudioNet proofs',
  '',
  `${address} · ${source} · ${fixtures} · ${evidence}`,
  '',
  `The deployed source matches the pinned commit. Normalized source SHA-256 is \`${proof.source.sha256}\`.`,
  'All four receipts finalized with successful execution and majority agreement.',
  '',
  '| Transaction | Agree votes | Report ID | Rewritten PNG SHA-256 |',
  '| --- | ---: | --- | --- |',
  ...rows.map(({tx, votes, report, png}) =>
    `| ${tx} | ${votes} | ${report ? '\`' + report + '\`' : '—'} | ${png ? '\`' + png + '\`' : '—'} |`),
  '',
  'Each readback matched the expected PNG bytes. An independent Node.js decoder checked each RGBA sample.',
  'The first two images share one output despite different transparent RGB samples and text chunks.',
  'The third changes one red sample at alpha 1 and yields a distinct output.',
  'A read against an unknown PNG digest reverted.',
  '',
].join('\n');

const submission = [
  '**Contribution type** Builder → Intelligent Contracts',
  '',
  '**Title** PngAlphaScrub — Consensus-Verified PNG Rewriting',
  '',
  '**Notes / Description**',
  '',
  'PngAlphaScrub is a reusable GenLayer primitive for stripping hidden RGB data from fully transparent PNG pixels. The leader and validators independently fetch a commit-pinned image, verify its SHA-256 and chunk CRCs, decompress the bounded image, reverse its filters, and rebuild the PNG after clearing RGB at alpha zero. Exact agreement covers the full rewritten bytes and source-bound report. Consumers retrieve the stored image by digest.',
  '',
  'StudioNet proofs cover deployment and three rewrites. Two images with different hidden RGB and text chunks produced the same PNG, with separate provenance reports. A change at alpha 1 yielded a different output. The contract supports non-interlaced RGBA8 PNGs up to 32×32. Original GitHub files remain public.',
  '',
  '**Evidence**',
  '',
  `- [Repository](${repo})`,
  `- ${source}`,
  `- ${address}`,
  `- [Proof ledger](${repo}/blob/main/LIVE_PROOFS.md)`,
  ...rows.map(({tx}) => `- ${tx}`),
  '',
].join('\n');

fs.writeFileSync('LIVE_PROOFS.md', ledger);
fs.writeFileSync('SUBMISSION.md', submission);
