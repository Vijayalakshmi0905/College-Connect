// Dependency-free checks for assistant fetch URL, CSRF, JSON, and error UI.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const listeners = {};
function makeNode(id = '') {
    const handlers = {};
    const classes = new Set();
    return {
        id, dataset: {}, value: '', disabled: false, textContent: '', className: '',
        children: [], scrollTop: 0, scrollHeight: 0,
        classList: {
            toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); },
            contains(name) { return classes.has(name); }
        },
        addEventListener(type, handler) { handlers[type] = handler; },
        querySelector() { return sendButton; },
        appendChild(child) {
            child.parent = this;
            child.remove = () => { this.children = this.children.filter(item => item !== child); };
            this.children.push(child);
            this.scrollHeight = this.children.length;
        },
        focus() {},
        _handlers: handlers
    };
}

const launcher = makeNode('assistantLauncher');
const panel = makeNode('canteenAssistantPanel');
panel.dataset.assistantEndpoint = '/api/assistant';
panel.classList.toggle('d-none', true);
const messages = makeNode('assistantMessages');
const form = makeNode('assistantForm');
const input = makeNode('assistantInput');
const sendButton = makeNode('assistantSubmit');
const closeButton = makeNode('assistantClose');
const document = {
    addEventListener(type, handler) { listeners[type] = handler; },
    getElementById(id) {
        return ({ assistantLauncher: launcher, canteenAssistantPanel: panel, assistantMessages: messages, assistantForm: form, assistantInput: input })[id] || null;
    },
    querySelector(selector) {
        if (selector === '[data-assistant-close]') return closeButton;
        if (selector === 'meta[name="csrf-token"]') return { content: 'test-csrf-token' };
        return null;
    },
    querySelectorAll() { return []; },
    createElement() { return makeNode(); }
};
form.querySelector = () => sendButton;

let fetchHandler = async () => ({ ok: true, status: 200, text: async () => JSON.stringify({ success: true, reply: 'Masala Dosa is available for ₹60.' }) });
let lastRequest;
const context = vm.createContext({
    document,
    window: { location: { href: 'http://localhost/menu' } },
    URL, JSON, String,
    console: { error() {} },
    fetch: async (url, options) => { lastRequest = { url, options }; return fetchHandler(url, options); }
});

vm.runInContext(fs.readFileSync('static/js/assistant.js', 'utf8'), context);
listeners.DOMContentLoaded();

(async () => {
    input.value = 'Show the current menu';
    await form._handlers.submit({ preventDefault() {} });
    assert.equal(lastRequest.url, '/api/assistant');
    assert.equal(lastRequest.options.method, 'POST');
    assert.equal(lastRequest.options.mode, 'same-origin');
    assert.equal(lastRequest.options.credentials, 'same-origin');
    assert.equal(lastRequest.options.headers['X-CSRF-Token'], 'test-csrf-token');
    assert.deepEqual(JSON.parse(lastRequest.options.body), { message: 'Show the current menu' });
    assert(messages.children.some(node => node.textContent === 'Masala Dosa is available for ₹60.'));

    fetchHandler = async () => ({ ok: false, status: 503, text: async () => JSON.stringify({ success: false, error: 'The assistant could not read canteen data right now. Please retry shortly.' }) });
    input.value = 'Show the menu';
    await form._handlers.submit({ preventDefault() {} });
    assert(messages.children.some(node => node.textContent.includes('Please retry shortly.')));

    panel.dataset.assistantEndpoint = '{{ url_for("assistant_chat") }}';
    input.value = 'Show the menu';
    await form._handlers.submit({ preventDefault() {} });
    assert(messages.children.some(node => node.textContent.includes('API URL was not rendered')));

    panel.dataset.assistantEndpoint = '/api/assistant';
    fetchHandler = async () => { throw new TypeError('Failed to fetch'); };
    input.value = 'Show the menu';
    await form._handlers.submit({ preventDefault() {} });
    assert(messages.children.some(node => node.textContent.includes('Could not connect to /api/assistant')));
    assert.equal(input.disabled, false);
    assert.equal(sendButton.disabled, false);
    console.log('PASS: assistant endpoint/CSRF payload, JSON response, HTTP error, and network error handling');
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
