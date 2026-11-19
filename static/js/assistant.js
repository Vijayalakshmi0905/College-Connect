/** Read-only CollegeConnect canteen assistant UI. */
document.addEventListener('DOMContentLoaded', () => {
    const launcher = document.getElementById('assistantLauncher');
    const panel = document.getElementById('canteenAssistantPanel');
    const closeButton = document.querySelector('[data-assistant-close]');
    const messages = document.getElementById('assistantMessages');
    const form = document.getElementById('assistantForm');
    const input = document.getElementById('assistantInput');
    const sendButton = form?.querySelector('button[type="submit"]');
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

    if (!launcher || !panel || !messages || !form || !input || !sendButton) return;

    function setOpen(open) {
        panel.classList.toggle('d-none', !open);
        launcher.setAttribute('aria-expanded', String(open));
        if (open) input.focus();
    }

    function appendMessage(text, kind = 'bot') {
        const node = document.createElement('div');
        node.className = `assistant-message assistant-message-${kind}`;
        node.textContent = text;
        messages.appendChild(node);
        messages.scrollTop = messages.scrollHeight;
        return node;
    }

    async function sendMessage(message) {
        const cleanMessage = String(message || '').trim();
        if (!cleanMessage || sendButton.disabled) return;

        appendMessage(cleanMessage, 'user');
        input.value = '';
        input.disabled = true;
        sendButton.disabled = true;
        const pending = appendMessage('Checking the current canteen information…', 'bot assistant-message-pending');
        const endpoint = panel.dataset.assistantEndpoint;

        try {
            if (!endpoint || endpoint.includes('{{')) {
                throw new Error('The assistant API URL is missing from the page configuration.');
            }
            const response = await fetch(endpoint, {
                method: 'POST',
                mode: 'same-origin',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken
                },
                body: JSON.stringify({ message: cleanMessage }),
                cache: 'no-store'
            });
            const responseText = await response.text();
            let data;
            try {
                data = responseText ? JSON.parse(responseText) : {};
            } catch (_parseError) {
                pending.remove();
                appendMessage(`The assistant endpoint returned an unexpected response (HTTP ${response.status}). Refresh the page and try again.`, 'error');
                console.error('Assistant returned a non-JSON response', { endpoint, status: response.status });
                return;
            }
            pending.remove();
            if (!response.ok || !data.success) {
                appendMessage(data.error || `The assistant request failed (HTTP ${response.status}). Please try again.`, 'error');
                if (data.needs_login) {
                    const signIn = document.createElement('a');
                    signIn.href = '/login';
                    signIn.textContent = 'Sign in to CollegeConnect';
                    signIn.className = 'assistant-message assistant-message-bot';
                    messages.appendChild(signIn);
                }
            } else {
                appendMessage(data.reply || 'I don’t have an answer for that yet.', 'bot');
            }
        } catch (error) {
            pending.remove();
            const unresolvedTemplateValue = !endpoint || endpoint.includes('{{');
            const apiPath = endpoint && !unresolvedTemplateValue
                ? new URL(endpoint, window.location.href).pathname
                : 'the Flask-configured assistant API';
            const errorMessage = unresolvedTemplateValue
                ? 'The assistant API URL was not rendered. Open this page through the CollegeConnect Flask app, then refresh.'
                : `Could not connect to ${apiPath}. Check that this page is served by the CollegeConnect Flask app, then refresh and retry.`;
            appendMessage(errorMessage, 'error');
            console.error('Canteen assistant request failed before receiving an HTTP response.', error);
        } finally {
            input.disabled = false;
            sendButton.disabled = false;
            input.focus();
        }
    }

    launcher.addEventListener('click', () => setOpen(panel.classList.contains('d-none')));
    closeButton?.addEventListener('click', () => setOpen(false));
    form.addEventListener('submit', (event) => {
        event.preventDefault();
        return sendMessage(input.value);
    });
    document.querySelectorAll('[data-assistant-prompt]').forEach((button) => {
        button.addEventListener('click', () => sendMessage(button.dataset.assistantPrompt));
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !panel.classList.contains('d-none')) setOpen(false);
    });
});
