/**
 * College Connect - Reusable Cart & Storage Engine
 * Manages cart state in localStorage and order history in sessionStorage
 */

const CART_STORAGE_KEY = 'college_connect_cart';
const LAST_ORDER_KEY = 'college_connect_last_order';

/** Escape untrusted text before placing it in an HTML string. */
function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[char]));
}

/**
 * Retrieve current cart from localStorage
 * @returns {Array} List of cart item objects
 */
function getCart() {
    try {
        const data = localStorage.getItem(CART_STORAGE_KEY);
        return data ? JSON.parse(data) : [];
    } catch (e) {
        console.error('Error loading cart from localStorage:', e);
        return [];
    }
}

/**
 * Persist cart array into localStorage and update UI counters
 * @param {Array} cart 
 */
function saveCart(cart) {
    try {
        localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    } catch (e) {
        console.error('Error saving cart to localStorage:', e);
    }
    updateCartBadge();
}

/**
 * Add a food item to the cart or increment its quantity if existing
 * @param {Object} item - { id, name, price, category, image }
 * @param {number} qty - Quantity to add (default 1)
 */
function addToCart(item, qty = 1) {
    const cart = getCart();
    const existingIndex = cart.findIndex(i => i.id === item.id);

    if (existingIndex > -1) {
        cart[existingIndex].quantity += qty;
    } else {
        cart.push({
            id: item.id,
            name: item.name,
            price: Number(item.price),
            category: item.category,
            image: item.image,
            quantity: qty
        });
    }

    saveCart(cart);
    showToast('Item Added', `${item.name} added to your cart!`, 'bi-bag-check-fill');
}

/**
 * Update quantity for a specific item
 * @param {number} itemId 
 * @param {number} delta - (+1 or -1)
 */
function updateCartItemQuantity(itemId, delta) {
    let cart = getCart();
    const index = cart.findIndex(i => i.id === itemId);

    if (index > -1) {
        cart[index].quantity += delta;
        if (cart[index].quantity <= 0) {
            cart.splice(index, 1);
            showToast('Item Removed', 'Item removed from your cart.', 'bi-trash');
        }
    }

    saveCart(cart);
}

/**
 * Remove an item completely from the cart
 * @param {number} itemId 
 */
function removeFromCart(itemId) {
    let cart = getCart();
    cart = cart.filter(i => i.id !== itemId);
    saveCart(cart);
    showToast('Item Removed', 'Item removed from your cart.', 'bi-trash');
}

/**
 * Clear all items from the cart
 */
function clearCart() {
    localStorage.removeItem(CART_STORAGE_KEY);
    updateCartBadge();
}

/**
 * Calculate totals for the current cart
 * @returns {Object} { count, subtotal, total }
 */
function getCartTotals() {
    const cart = getCart();
    const count = cart.reduce((sum, item) => sum + item.quantity, 0);
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    return {
        count,
        subtotal,
        total: subtotal // No extra platform or delivery fee in student canteen
    };
}

/**
 * Update the cart badge in navbar across pages
 */
function updateCartBadge() {
    const badges = document.querySelectorAll('.cart-count-badge');
    const { count } = getCartTotals();
    badges.forEach(badge => {
        badge.textContent = count;
        if (count > 0) {
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    });
}

/**
 * Display a user-friendly Bootstrap toast notification
 * @param {string} title 
 * @param {string} message 
 * @param {string} iconClass 
 */
function showToast(title, message, iconClass = 'bi-info-circle') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1100';
        document.body.appendChild(container);
    }

    const toastId = 'toast-' + Date.now();
    const toastHtml = `
        <div id="${toastId}" class="toast align-items-center text-bg-dark border-0 shadow-lg" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="d-flex">
                <div class="toast-body d-flex align-items-center">
            <i class="bi ${escapeHtml(iconClass)} text-warning fs-5 me-2"></i>
                    <div>
                <strong class="d-block text-white">${escapeHtml(title)}</strong>
                <span class="small text-white-50">${escapeHtml(message)}</span>
                    </div>
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    if (window.bootstrap && window.bootstrap.Toast) {
        const bsToast = new bootstrap.Toast(toastElement, { delay: 2500 });
        bsToast.show();
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Automatically sync cart count badge when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    updateCartBadge();
});
