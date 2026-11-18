import fs from 'node:fs';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
import {inflateSync} from 'node:zlib';
import {abi} from 'genlayer-js';
import {rpc, receipt, source, read, digest, sha, denied} from './check.mjs';

const code = 'contracts/PngAlphaScrub.py';
const publisher = {name: 'studio-proof-deployer', address: '0x7a413BB4AB62E31d62d4cD9efC8C8a8Dae37FB42'};
const journal = 'PROOFS.json';
const commit = process.argv[2];
const verifyOnly = process.argv.includes('--verify-only');
const resumeUnbroadcast = process.argv.includes('--resume-unbroadcast');
assert(/^[a-f0-9]{40}$/.test(commit ?? ''));
const proof = fs.existsSync(journal)
  ? JSON.parse(fs.readFileSync(journal, 'utf8'))
  : {network: 'StudioNet', source_commit: commit, transactions: []};
assert.equal(proof.source_commit, commit);
const save = () => fs.writeFileSync(journal, JSON.stringify(proof, null, 2) + '\n');

function send(args, signer, entry) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['scripts/run-cli.cjs', ...args], {
      windowsHide: true,
      env: {...process.env, PAS_TEST_ACCOUNT: signer.name},
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let pending = '';
    child.stderr.resume();
    child.stdout.on('data', chunk => {
      const lines = (pending + chunk.toString()).split(/\r?\n/);
      pending = lines.pop();
      for (const line of lines) {
        const matched = /^BROADCAST_HASH (0x[0-9a-f]{64})$/i.exec(line);
        if (matched) {
          entry.hash = matched[1];
          save();
          console.log(entry.step, entry.hash);
        }
      }
    });
    child.on('error', reject);
    child.on('close', resolve);
  });
}

async function transaction(step, args, signer, expected = 'SUCCESS', message) {
  let entry = proof.transactions.find(item => item.step === step);
  if (!entry) {
    assert(!verifyOnly, 'Verification requires an original broadcast journal');
    const nonce = await rpc('eth_getTransactionCount', [signer.address, 'latest']);
    assert.equal(await rpc('eth_getTransactionCount', [signer.address, 'pending']), nonce);
    entry = {step, args, signer: signer.address, nonce};
    proof.transactions.push(entry);
    save();
    await send(args, signer, entry);
  } else if (!entry.hash && !verifyOnly && resumeUnbroadcast) {
    assert.deepEqual(entry.args, args);
    assert.equal(entry.signer, signer.address);
    const [latest, pending] = await Promise.all([
      rpc('eth_getTransactionCount', [signer.address, 'latest']),
      rpc('eth_getTransactionCount', [signer.address, 'pending']),
    ]);
    assert.equal(latest, entry.nonce, 'Recorded nonce was already used');
    assert.equal(pending, entry.nonce, 'Recorded nonce already has a pending write');
    if (proof.address) {
      const history = await rpc('sim_getTransactionsForAddress', [proof.address]);
      assert(!history.some(t => t.from_address?.toLowerCase() === signer.address.toLowerCase()
        && BigInt(t.nonce) === BigInt(entry.nonce)), 'Recorded transaction already exists');
    }
    await send(args, signer, entry);
  }
  assert.deepEqual(entry.args, args);
  assert.equal(entry.signer, signer.address);
  assert(entry.hash, 'Broadcast status unknown. Inspect account history before any retry.');
  entry.receipt = await receipt(entry.hash, expected, message);
  save();
  assert.equal(entry.receipt.committed, expected === 'SUCCESS');
  const native = await rpc('eth_getTransactionByHash', [entry.hash]);
  assert.equal(native.from_address.toLowerCase(), signer.address.toLowerCase());
  assert.equal(BigInt(native.nonce), BigInt(entry.nonce));
  assert.equal(BigInt(native.value), 0n);
  console.log(step, entry.receipt.status, entry.receipt.execution);
  return entry.receipt.address;
}

const repo = 'Al1ranger/png-alpha-scrub';
const reference = JSON.parse(fs.readFileSync('REFERENCE.json', 'utf8'));
assert.equal(await rpc('eth_chainId', []), '0xf22f');
proof.address = await transaction('deploy', ['deploy', '--contract', code], publisher);
proof.source = await source(proof.address);
proof.examples ??= {};
save();

for (const [name, evidence] of Object.entries(reference)) {
  const ref = `${repo}/${commit}/fixtures/${name}.png`;
  const {png_hex, rgba_hex, ...fields} = evidence;
  assert.equal(sha(fs.readFileSync('fixtures/' + name + '.png')), fields.source_sha256);
  const report = {schema: 'png-alpha-scrub/1', source_url: 'https://raw.githubusercontent.com/' + ref, ...fields};
  const args = ['write', proof.address, 'scrub', '--args', ref, fields.source_sha256];
  assert.equal((await transaction(name, args, publisher)).toLowerCase(), proof.address.toLowerCase());
  const entry = proof.transactions.find(t => t.step === name);
  const tx = await rpc('eth_getTransactionByHash', [entry.hash]);
  const leader = tx.consensus_data.leader_receipt.find(x => x.mode === 'leader');
  const bytes = Buffer.from(leader.result, 'base64');
  assert.equal(bytes[0], 0);
  const id = abi.calldata.decode(bytes.subarray(1));
  assert.equal(id, digest(report));
  assert.deepEqual(await read(proof.address, 'get_report', [id]), report);
  const png = await read(proof.address, 'get_png', [report.png_id]);
  assert.equal(png, png_hex);
  const binary = Buffer.from(png, 'hex');
  assert.equal(sha(binary), report.png_id);
  const raw = inflateSync(binary.subarray(41, 41 + binary.readUInt32BE(33)));
  const lines = [];
  for (let row = 0; row < report.height; row++) {
    const start = row * (1 + 4 * report.width);
    assert.equal(raw[start], 0);
    lines.push(raw.subarray(start + 1, start + 1 + 4 * report.width));
  }
  assert.equal(Buffer.concat(lines).toString('hex'), rgba_hex);
  proof.examples[name] = {id, report, png};
  save();
  console.log(name, report.changed_pixels, report.png_id);
}
const a = proof.examples['alpha-original'];
const b = proof.examples['alpha-variant'];
assert.notEqual(a.id, b.id);
assert.equal(a.report.png_id, b.report.png_id);
assert.notEqual(a.report.png_id, proof.examples['visible-change'].report.png_id);
assert(await denied(proof.address, 'get_png', ['0'.repeat(64)]));
proof.unknown_png_reverted = true;
const history = await rpc('sim_getTransactionsForAddress', [proof.address]);
assert.deepEqual(history.map(t => t.hash).sort(), proof.transactions.map(t => t.hash).sort());
proof.verified = true;
save();
