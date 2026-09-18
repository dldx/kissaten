#!/usr/bin/env node
/**
 * Offline-first verification harness for Kissaten (Phase 4).
 *
 * Codifies the CDP methodology that worked during the offline investigation:
 *
 *   1. Use `Network.setBlockedURLs([origin + "/*"])` to simulate offline, NEVER
 *      `Network.emulateNetworkConditions(offline)` — loopback/Cloudflare
 *      routing still resolves through emulation in the test browser, so the
 *      "offline" fetch succeeds and the scenario reports the wrong state.
 *   2. Use raw browser-level CDP (`Target.attachToTarget` + flattened nested
 *      `{sessionId, ...}` messages on the SAME socket). Playwright's
 *      `connectOverCDP` handshake fails against this browser; raw CDP is
 *      reliable.
 *
 * Each scenario (except `varietals`, which deliberately has NO warm-up) runs:
 *   warm online -> block the origin -> reload -> assert.
 *
 * Asserts are pragmatic text checks (`document.body.innerText`) plus broken-img
 * counts (`i.complete && i.naturalWidth === 0`, visible only). Selectors may
 * need tweaking if page copy/classes change.
 *
 * Run:  bun scripts/offline-test.mjs [--cdp-ws ws://127.0.0.1:9222] [--url https://kissaten.app] [--scenario home|search|roasters|bean|varietals|vault]
 * Node (>=21) also works. Requires a Chromium started with
 * `--remote-debugging-port=9222`.
 */

import { writeFileSync } from "node:fs";

const args = process.argv.slice(2);
function arg(name, fallback) {
	const i = args.indexOf(name);
	return i !== -1 && args[i + 1] ? args[i + 1] : fallback;
}
const CDP_WS = arg("--cdp-ws", "ws://127.0.0.1:9222");
const BASE_URL = arg("--url", "https://kissaten.app").replace(/\/$/, "");
const ONLY = arg("--scenario", null);
const ORIGIN = new URL(BASE_URL).origin;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- CDP plumbing ------------------------------------------------------------

let ws;
let msgId = 0;
const pending = new Map();
const eventListeners = [];
let sessionId = null;

const urlOf = new Map(); // requestId -> url
const failedRequestUrls = new Set();
const badResponses = new Set();
const consoleErrors = [];

function connect() {
	return new Promise((resolve, reject) => {
		ws = new WebSocket(CDP_WS);
		ws.addEventListener("open", resolve);
		ws.addEventListener("error", () =>
			reject(
				new Error(
					`Cannot connect to ${CDP_WS}. Start Chromium with --remote-debugging-port=9222.`,
				),
			),
		);
		ws.addEventListener("message", (event) => {
			const msg = JSON.parse(event.data);
			if (msg.id && pending.has(msg.id)) {
				const { resolve: r, reject: j } = pending.get(msg.id);
				pending.delete(msg.id);
				if (msg.error) j(new Error(`${msg.error.message} (${msg.error.code})`));
				else r(msg.result);
				return;
			}
			if (msg.sessionId && msg.sessionId !== sessionId) return; // other session
			for (const handler of eventListeners) handler(msg);
			if (msg.method === "Network.requestWillBeSent")
				urlOf.set(msg.params.requestId, msg.params.request.url);
			else if (msg.method === "Network.loadingFailed")
				failedRequestUrls.add(urlOf.get(msg.params.requestId) ?? msg.params.requestId);
			else if (msg.method === "Network.responseReceived") {
				const { status, url } = msg.params.response;
				if (status >= 400) badResponses.add(`${status} ${url}`);
			} else if (msg.method === "Runtime.consoleAPICalled") {
				if (msg.params.type === "error") {
					consoleErrors.push(
						(msg.params.args ?? []).map((a) => a.value ?? a.description ?? "").join(" "),
					);
				}
			}
		});
	});
}

function send(method, params = {}) {
	const id = ++msgId;
	return new Promise((resolve, reject) => {
		pending.set(id, { resolve, reject });
		ws.send(
			JSON.stringify(sessionId ? { id, sessionId, method, params } : { id, method, params }),
		);
	});
}

function waitForEvent(method, timeoutMs = 45000) {
	return new Promise((resolve, reject) => {
		const timer = setTimeout(() => {
			eventListeners.splice(eventListeners.indexOf(handler), 1);
			reject(new Error(`Timed out waiting for ${method}`));
		}, timeoutMs);
		const handler = (msg) => {
			if (msg.method === method) {
				clearTimeout(timer);
				eventListeners.splice(eventListeners.indexOf(handler), 1);
				resolve(msg.params);
			}
		};
		eventListeners.push(handler);
	});
}

async function evalJs(expression) {
	const result = await send("Runtime.evaluate", {
		expression,
		returnByValue: true,
		awaitPromise: true,
	});
	if (result.exceptionDetails)
		throw new Error(
			`eval failed: ${result.exceptionDetails.exception?.description ?? result.exceptionDetails.text}`,
		);
	return result.result?.value;
}

async function nav(url) {
	await send("Page.navigate", { url });
	await waitForEvent("Page.loadEventFired");
}

async function reload() {
	await send("Page.reload", { ignoreCache: false });
	await waitForEvent("Page.loadEventFired");
}

async function blockOffline() {
	// Block every request to the tested origin — see the header comment for
	// why this is preferred over emulateNetworkConditions.
	await send("Network.setBlockedURLs", { urls: [`${ORIGIN}/*`] });
}

async function unblock() {
	await send("Network.setBlockedURLs", { urls: [] });
}

function clearEvents() {
	failedRequestUrls.clear();
	badResponses.clear();
	consoleErrors.length = 0;
}

async function findOrCreatePage() {
	const { targetInfos } = await send("Target.getTargets");
	let target =
		targetInfos.find((t) => t.type === "page" && t.url.startsWith(ORIGIN)) ??
		targetInfos.find((t) => t.type === "page");
	if (!target) {
		const created = await send("Target.createTarget", { url: `${BASE_URL}/` });
		target = { targetId: created.targetId };
	}
	const attach = await send("Target.attachToTarget", {
		targetId: target.targetId,
		flatten: true,
	});
	sessionId = attach.sessionId;
	await send("Page.enable");
	await send("Runtime.enable");
	await send("Network.enable");
}

// --- Scenarios ---------------------------------------------------------------

const scenarios = {
	async home() {
		await unblock();
		await nav(`${BASE_URL}/`);
		await sleep(4000); // let the data stream + carousel caches fill
		clearEvents();
		await blockOffline();
		await sleep(300);
		await reload();
		await sleep(4500); // 3s dataPromise race + counter animation
		const text = await evalJs("document.body.innerText");
		const match = text.match(/([\d.,]{4,})\+?\s*\n?\s*Coffee Beans/);
		const num = match ? parseFloat(match[1].replace(/,/g, "")) : NaN;
		const stuckZero = /\b0\+\s*\n?\s*Coffee Beans/.test(text);
		const pass = !stuckZero && num >= 1000 && consoleErrors.length === 0;
		return {
			pass,
			details: `beans counter = ${match ? match[1] : "not found"} (stuckZero=${stuckZero}); console errors = ${consoleErrors.length}`,
		};
	},

	async search() {
		await unblock();
		await nav(`${BASE_URL}/search`);
		await sleep(3500);
		clearEvents();
		await blockOffline();
		await sleep(300);
		await reload();
		await sleep(1500);
		const text = await evalJs("document.body.innerText");
		const found =
			/Showing\s+[\d.,]+\s+of\s+[\d.,]+\s+beans/i.test(text) ||
			/([\d.,]+)\s*beans? found/i.test(text);
		return { pass: found, details: `cached results present = ${found}` };
	},

	async roasters() {
		await unblock();
		await nav(`${BASE_URL}/roasters`);
		await sleep(3500);
		clearEvents();
		await blockOffline();
		await sleep(300);
		await reload();
		await sleep(2000);
		const text = await evalJs("document.body.innerText");
		const hasRoasters = /roasters/i.test(text) && text.includes("Explore");
		// Count ONLY visible broken images (hidden ones are the intended outcome
		// of the sticker-wall second-error fix).
		const broken = await evalJs(
			`[...document.images].filter(i => i.complete && i.naturalWidth === 0 && i.getBoundingClientRect().width > 0).length`,
		);
		const pass = hasRoasters && broken <= 15;
		return {
			pass,
			details: `roaster names present = ${hasRoasters}; broken (visible) logos = ${broken} (${
				broken === 0 ? "ok" : broken <= 15 ? "warning" : "FAIL >15"
			})`,
		};
	},

	async bean() {
		await unblock();
		await nav(`${BASE_URL}/`);
		await sleep(2500);
		let href = await evalJs(
			`(() => { const a = document.querySelector('a[href*="/roasters/"]'); return a ? a.href : null; })()`,
		);
		if (!href) {
			await nav(`${BASE_URL}/roasters`);
			await sleep(2000);
			href = await evalJs(
				`(() => { const a = document.querySelector('a[href*="/roasters/"]'); return a ? a.href : null; })()`,
			);
		}
		if (!href) return { pass: false, details: "no bean link found while online" };
		await nav(href);
		await sleep(2500);
		const warmh1 = await evalJs("document.querySelector('h1')?.innerText || ''");
		clearEvents();
		await blockOffline();
		await sleep(300);
		await reload();
		await sleep(2500);
		const text = await evalJs("document.body.innerText");
		const h1 = await evalJs("document.querySelector('h1')?.innerText || ''");
		const imgsOk = await evalJs(
			`[...document.images].filter(i => i.complete && i.naturalWidth > 0).length`,
		);
		const placeholder = /unavailable offline/i.test(text);
		const pass = Boolean(h1) && (imgsOk > 0 || placeholder);
		return {
			pass,
			details: `h1 = "${h1 || "(none)"}"; ok imgs = ${imgsOk}; placeholder = ${placeholder}; warm h1 was "${warmh1 || "(none)"}"`,
		};
	},

	async varietals() {
		// Deliberately NO warm-up — this page has never been visited.
		clearEvents();
		await blockOffline();
		await sleep(300);
		await nav(`${BASE_URL}/varietals`);
		await sleep(3000);
		const text = await evalJs("document.body.innerText");
		const blank = text.trim().length === 0;
		const bare408 = /Network error/.test(text);
		let state = "unknown";
		if (/You're offline|isn't cached/.test(text)) state = "offline-error-page";
		else if (/[Vv]arietal/.test(text)) state = "varietals-content";
		else if (/Kissaten/.test(text)) state = "app-shell";
		const pass = !blank && !bare408 && state !== "unknown";
		return {
			pass,
			details: `state = ${state}; blank = ${blank}; bare408 = ${bare408}`,
		};
	},

	async vault() {
		await unblock();
		await nav(`${BASE_URL}/vault/saved`);
		await sleep(3500);
		clearEvents();
		await blockOffline();
		await sleep(300);
		await reload();
		await sleep(2000);
		const text = await evalJs("document.body.innerText");
		const pass = /My Coffee Vault|Saved Beans/.test(text);
		return { pass, details: `vault UI present = ${pass}` };
	},
};

// --- Runner ------------------------------------------------------------------

async function run() {
	await connect();
	await findOrCreatePage();

	const names = ONLY ? [ONLY] : Object.keys(scenarios);
	if (!names.every((n) => scenarios[n]))
		throw new Error(
			`Unknown scenario "${ONLY}" (expected ${Object.keys(scenarios).join(", ")})`,
		);

	const report = { timestamp: new Date().toISOString(), url: BASE_URL, scenarios: {} };

	for (const name of names) {
		try {
			const { pass, details } = await scenarios[name]();
			report.scenarios[name] = {
				pass,
				details: details ?? "",
				failedRequestUrls: [...failedRequestUrls].slice(0, 25),
				consoleErrors: consoleErrors.slice(0, 10),
			};
		} catch (err) {
			report.scenarios[name] = {
				pass: false,
				details: `scenario threw: ${err.message}`,
				failedRequestUrls: [...failedRequestUrls].slice(0, 25),
				consoleErrors: consoleErrors.slice(0, 10),
			};
		}
	}

	const json = JSON.stringify(report, null, 2);
	console.log(json);
	writeFileSync(new URL("./offline-test-report.json", import.meta.url), json);
	const anyFailed = Object.values(report.scenarios).some((s) => !s.pass);
	process.exitCode = anyFailed ? 1 : 0;
}

run().catch((err) => {
	console.error(`[offline-test] ${err.message}`);
	process.exitCode = 1;
});