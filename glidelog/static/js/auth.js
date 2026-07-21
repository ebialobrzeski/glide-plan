/**
 * auth.js — GlideLog's own login / registration / email-verification flow.
 *
 * Rendered on the standalone login page (templates/logbook/login.html) that
 * GlideLog now serves in place of redirecting to the main GlidePlan app.
 * On success it sends the browser back to where the visitor was headed
 * (window.GLIDELOG_NEXT_URL), or to the dashboard as a fallback.
 */
(function () {
    'use strict';

    const DEFAULT_NEXT = '/logbook/dashboard';

    class AuthManager {
        constructor() {
            this._pendingVerifyEmail = null;
            this._bindDialogButtons();
            // Auto-open the login popup as soon as Shoelace dialogs are ready.
            customElements.whenDefined('sl-dialog').then(() => this.showLoginDialog());
        }

        // ── redirect helper ──────────────────────────────────────────────────
        _nextUrl() {
            const raw = window.GLIDELOG_NEXT_URL;
            if (!raw) return DEFAULT_NEXT;
            try {
                const url = new URL(raw, window.location.origin);
                // Only same-origin targets are allowed — never redirect off-site.
                if (url.origin === window.location.origin) return url.href;
            } catch (_) { /* malformed — fall through */ }
            return DEFAULT_NEXT;
        }

        _goToApp() {
            window.location.replace(this._nextUrl());
        }

        // ── wiring ───────────────────────────────────────────────────────────
        _bindDialogButtons() {
            document.getElementById('auth-login-btn')?.addEventListener('click', () => this.showLoginDialog());
            document.getElementById('auth-register-btn')?.addEventListener('click', () => this.showRegisterDialog());

            document.getElementById('switch-to-register')?.addEventListener('click', (e) => {
                e.preventDefault();
                this.hideLoginDialog();
                this.showRegisterDialog();
            });
            document.getElementById('switch-to-login')?.addEventListener('click', (e) => {
                e.preventDefault();
                this.hideRegisterDialog();
                this.showLoginDialog();
            });

            document.getElementById('login-form')?.addEventListener('submit', (e) => this._handleLoginSubmit(e));
            document.getElementById('register-form')?.addEventListener('submit', (e) => this._handleRegisterSubmit(e));

            document.getElementById('verify-submit-btn')?.addEventListener('click', () => this._handleVerifySubmit());
            document.getElementById('verify-code-input')?.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') this._handleVerifySubmit();
            });
            document.getElementById('verify-resend-link')?.addEventListener('click', (e) => {
                e.preventDefault();
                this._handleResendCode();
            });
        }

        // ── API calls ────────────────────────────────────────────────────────
        async login(email, password) {
            const resp = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Login failed.');
            return data;
        }

        async register(email, displayName, password) {
            const resp = await fetch('/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, display_name: displayName, password }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Registration failed.');
            return data;
        }

        async verifyEmail(email, code) {
            const resp = await fetch('/auth/verify-email', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, code }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || 'Verification failed.');
            return data;
        }

        // ── dialog visibility ────────────────────────────────────────────────
        showLoginDialog() {
            const dlg = document.getElementById('login-dialog');
            if (!dlg) return;
            const err = document.getElementById('login-error');
            if (err) err.style.display = 'none';
            document.getElementById('login-form')?.reset();
            dlg.show();
        }
        hideLoginDialog() { document.getElementById('login-dialog')?.hide(); }

        showRegisterDialog() {
            const dlg = document.getElementById('register-dialog');
            if (!dlg) return;
            const err = document.getElementById('register-error');
            if (err) err.style.display = 'none';
            document.getElementById('register-form')?.reset();
            dlg.show();
        }
        hideRegisterDialog() { document.getElementById('register-dialog')?.hide(); }

        showVerifyDialog(email) {
            this._pendingVerifyEmail = email;
            const dlg = document.getElementById('verify-email-dialog');
            if (!dlg) return;
            const addr = document.getElementById('verify-email-addr');
            if (addr) addr.textContent = email;
            const err = document.getElementById('verify-error');
            if (err) err.style.display = 'none';
            const input = document.getElementById('verify-code-input');
            if (input) input.value = '';
            dlg.show();
            setTimeout(() => input?.focus(), 150);
        }
        hideVerifyDialog() { document.getElementById('verify-email-dialog')?.hide(); }

        // ── form handlers ────────────────────────────────────────────────────
        async _handleLoginSubmit(e) {
            e.preventDefault();
            const email = document.getElementById('login-email').value.trim();
            const password = document.getElementById('login-password').value;
            const errorEl = document.getElementById('login-error');
            const submitBtn = document.getElementById('login-submit-btn');

            this._setButtonLoading(submitBtn, true);
            try {
                const data = await this.login(email, password);
                if (data.requires_verification) {
                    this.hideLoginDialog();
                    this.showVerifyDialog(data.email);
                    return;
                }
                this._goToApp();
            } catch (err) {
                if (errorEl) { errorEl.textContent = err.message; errorEl.style.display = ''; }
            } finally {
                this._setButtonLoading(submitBtn, false);
            }
        }

        async _handleRegisterSubmit(e) {
            e.preventDefault();
            const email = document.getElementById('register-email').value.trim();
            const displayName = document.getElementById('register-display-name').value.trim();
            const password = document.getElementById('register-password').value;
            const confirm = document.getElementById('register-confirm-password').value;
            const errorEl = document.getElementById('register-error');
            const submitBtn = document.getElementById('register-submit-btn');

            if (password !== confirm) {
                if (errorEl) {
                    errorEl.textContent = window.i18n?.t('auth.passwords_mismatch', 'Passwords do not match.') || 'Passwords do not match.';
                    errorEl.style.display = '';
                }
                return;
            }

            this._setButtonLoading(submitBtn, true);
            try {
                const data = await this.register(email, displayName, password);
                if (data.requires_verification) {
                    this.hideRegisterDialog();
                    this.showVerifyDialog(data.email);
                    return;
                }
                this._goToApp();
            } catch (err) {
                if (errorEl) { errorEl.textContent = err.message; errorEl.style.display = ''; }
            } finally {
                this._setButtonLoading(submitBtn, false);
            }
        }

        async _handleVerifySubmit() {
            const code = (document.getElementById('verify-code-input')?.value || '').trim();
            const errorEl = document.getElementById('verify-error');
            const submitBtn = document.getElementById('verify-submit-btn');

            if (!code || code.length !== 6) {
                if (errorEl) {
                    errorEl.textContent = window.i18n?.t('auth.enter_6_digit', 'Please enter the 6-digit code.') || 'Please enter the 6-digit code.';
                    errorEl.style.display = '';
                }
                return;
            }

            this._setButtonLoading(submitBtn, true);
            try {
                await this.verifyEmail(this._pendingVerifyEmail, code);
                this._goToApp();
            } catch (err) {
                // Map known error keys to translated messages when available.
                const msg = window.i18n?.t(`auth.${err.message}`, null);
                if (errorEl) { errorEl.textContent = msg || err.message; errorEl.style.display = ''; }
            } finally {
                this._setButtonLoading(submitBtn, false);
            }
        }

        async _handleResendCode() {
            const resendLink = document.getElementById('verify-resend-link');
            if (resendLink) resendLink.style.pointerEvents = 'none';
            try {
                await fetch('/auth/resend-code', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: this._pendingVerifyEmail }),
                });
                const errorEl = document.getElementById('verify-error');
                if (errorEl) {
                    errorEl.style.color = 'var(--sl-color-success-600)';
                    errorEl.textContent = window.i18n?.t('auth.code_resent', 'A new code has been sent.') || 'A new code has been sent.';
                    errorEl.style.display = '';
                    setTimeout(() => { errorEl.style.display = 'none'; errorEl.style.color = ''; }, 4000);
                }
            } finally {
                setTimeout(() => { if (resendLink) resendLink.style.pointerEvents = ''; }, 30000);
            }
        }

        // ── helpers ──────────────────────────────────────────────────────────
        _setButtonLoading(btn, loading) {
            if (!btn) return;
            btn.loading = loading;
            btn.disabled = loading;
        }
    }

    window.authManager = new AuthManager();
})();
