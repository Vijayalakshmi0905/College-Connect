// Dependency-free regression checks for the browser cart/storage engine.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const values = new Map();
const localStorage = {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key)
};
const document = {
    addEventListener() {},
    querySelectorAll() { return []; },
    getElementById() { return null; }
};
const context = vm.createContext({
    document, localStorage, console, Date, window: {},
    setTimeout() { return 0; }, clearTimeout() {}
});
vm.runInContext(fs.readFileSync('static/js/cart.js', 'utf8'), context);
context.showToast = () => {};

context.addToCart({ id: 7, name: 'Masala Dosa', price: 60, category: 'Breakfast', image: '/dosa.jpg' });
context.addToCart({ id: 7, name: 'Masala Dosa', price: 60, category: 'Breakfast', image: '/dosa.jpg' });
assert.deepEqual(JSON.parse(context.localStorage.getItem('college_connect_cart'))[0].quantity, 2);
assert.deepEqual(JSON.parse(JSON.stringify(context.getCartTotals())), { count: 2, subtotal: 120, total: 120 });
context.updateCartItemQuantity(7, -1);
assert.equal(JSON.parse(context.localStorage.getItem('college_connect_cart'))[0].quantity, 1);
context.updateCartItemQuantity(7, -1);
assert.deepEqual(JSON.parse(context.localStorage.getItem('college_connect_cart')), []);
context.addToCart({ id: 8, name: 'Tea', price: 15, category: 'Beverages', image: '/tea.jpg' });
context.clearCart();
assert.deepEqual(JSON.parse(context.localStorage.getItem('college_connect_cart') || '[]'), []);
assert.equal(context.escapeHtml('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');

console.log('PASS: cart add, increment, decrement, removal, persistence, clear, and HTML escaping');
