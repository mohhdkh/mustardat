/**
 * Lost & Found API Client
 * Centralized API handling for all frontend pages
 */

const ERROR_TRANSLATIONS = {
    'Incorrect email or password': 'البريد الإلكتروني أو كلمة المرور غير صحيحة.',
    'User account is disabled': 'هذا الحساب موقوف. تواصل مع الدعم للمساعدة.',
    'Email already registered': 'يوجد حساب مسجل بهذا البريد الإلكتروني.',
    'Could not validate credentials': 'تعذر التحقق من الجلسة. سجّل الدخول من جديد.',
    'Not authenticated': 'يرجى تسجيل الدخول للمتابعة.',
    'Item not found': 'البلاغ المطلوب غير موجود أو تم حذفه.',
    'Maximum 6 images per item': 'يمكنك إضافة 6 صور كحد أقصى لكل بلاغ.',
    'Item has no processed images. Please upload and wait for processing.': 'لم تكتمل معالجة صور هذا البلاغ بعد. ارفع صورة أو انتظر قليلًا ثم حاول مجددًا.',
    'Image embeddings not ready. Please wait for processing to complete.': 'الصور ما زالت قيد المعالجة. انتظر قليلًا ثم حاول مجددًا.',
    'Token refresh not implemented. Please login again.': 'انتهت الجلسة. سجّل الدخول من جديد.',
    'Validation error': 'بعض البيانات المدخلة غير صحيحة.',
    'Match not found': 'التطابق المطلوب غير موجود.',
    'Notification not found': 'الإشعار المطلوب غير موجود.',
    'Upload failed': 'تعذر رفع الصورة. تحقق من اتصالك وحاول مجددًا.',
    'An internal error occurred': 'حدث خطأ غير متوقع في الخادم. حاول مرة أخرى بعد قليل.'
};

const FIELD_NAMES = {
    email: 'البريد الإلكتروني', password: 'كلمة المرور', full_name: 'الاسم الكامل',
    phone_number: 'رقم الهاتف', title: 'عنوان البلاغ', description: 'الوصف',
    item_type: 'تصنيف الغرض', lost_or_found: 'نوع البلاغ', location_name: 'المكان',
    event_date: 'التاريخ والوقت', file: 'الصورة'
};

function translateValidationMessage(message = '') {
    if (/field required/i.test(message)) return 'هذا الحقل مطلوب';
    if (/valid email/i.test(message)) return 'أدخل بريدًا إلكترونيًا صالحًا';
    if (/at least 8 characters|at least 8/i.test(message)) return 'يجب ألا تقل كلمة المرور عن 8 أحرف';
    if (/at least 3 characters|at least 3/i.test(message)) return 'يجب ألا يقل النص عن 3 أحرف';
    if (/string should have at most/i.test(message)) return 'النص أطول من الحد المسموح';
    if (/valid datetime/i.test(message)) return 'أدخل تاريخًا ووقتًا صالحين';
    return message;
}

function friendlyApiError(payload, status) {
    if (Array.isArray(payload?.errors) && payload.errors.length) {
        const messages = payload.errors.slice(0, 3).map(error => {
            const rawField = String(error.field || '').split('.').pop();
            const field = FIELD_NAMES[rawField] || 'البيانات';
            return `${field}: ${translateValidationMessage(error.message)}`;
        });
        return `يرجى تصحيح البيانات التالية: ${messages.join('، ')}`;
    }

    const detail = typeof payload?.detail === 'string' ? payload.detail : '';
    if (ERROR_TRANSLATIONS[detail]) return ERROR_TRANSLATIONS[detail];
    if (/already registered/i.test(detail)) return 'يوجد حساب مسجل بهذا البريد الإلكتروني.';
    if (/permission/i.test(detail)) return 'ليس لديك صلاحية لتنفيذ هذا الإجراء.';
    if (/file too large/i.test(detail)) return 'حجم الصورة أكبر من الحد المسموح (10 ميجابايت).';
    if (/invalid file type/i.test(detail)) return 'نوع الملف غير مدعوم. استخدم JPG أو PNG أو WebP.';
    if (/maximum 6 images/i.test(detail)) return 'يمكنك إضافة 6 صور كحد أقصى لكل بلاغ.';
    if (/already (both_confirmed|rejected|confirmed)/i.test(detail)) return 'تم التعامل مع هذا التطابق مسبقًا.';

    const statusMessages = {
        400: 'تعذر تنفيذ الطلب. تحقق من البيانات وحاول مجددًا.',
        401: 'البريد الإلكتروني أو كلمة المرور غير صحيحة.',
        403: 'ليس لديك صلاحية لتنفيذ هذا الإجراء.',
        404: 'المحتوى المطلوب غير موجود.',
        409: 'يوجد تعارض مع بيانات محفوظة مسبقًا.',
        413: 'الملف المرفوع كبير جدًا.',
        422: 'يرجى التأكد من تعبئة الحقول المطلوبة بشكل صحيح.',
        429: 'أرسلت طلبات كثيرة خلال وقت قصير. انتظر دقيقة وحاول مجددًا.',
        500: 'حدث خطأ في الخادم. حاول مرة أخرى بعد قليل.',
        502: 'الخدمة غير متاحة مؤقتًا. حاول بعد قليل.',
        503: 'الخدمة مشغولة حاليًا. حاول بعد قليل.'
    };
    return statusMessages[status] || detail || 'تعذر إكمال الطلب. حاول مجددًا.';
}

const API = {
    BASE_URL: '/api/v1',
    
    // Get auth token from localStorage
    getToken() {
        return localStorage.getItem('authToken');
    },
    
    // Get current user from localStorage
    getUser() {
        try {
            return JSON.parse(localStorage.getItem('currentUser'));
        } catch {
            return null;
        }
    },
    
    // Check if user is logged in
    isLoggedIn() {
        return !!this.getToken();
    },
    
    // Save auth data
    saveAuth(token, user) {
        localStorage.setItem('authToken', token);
        if (user) {
            localStorage.setItem('currentUser', JSON.stringify(user));
        }
    },
    
    // Clear auth data (logout)
    clearAuth() {
        localStorage.removeItem('authToken');
        localStorage.removeItem('currentUser');
    },

    async parseBody(response) {
        if (response.status === 204) return null;
        const text = await response.text();
        if (!text) return null;
        try {
            return JSON.parse(text);
        } catch {
            return { detail: text };
        }
    },

    errorMessage(payload, status) {
        return friendlyApiError(payload, status);
    },
    
    // Make API request
    async request(endpoint, options = {}) {
        const url = `${this.BASE_URL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };
        
        // Add auth header if token exists
        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        try {
            const response = await fetch(url, {
                ...options,
                headers
            });
            
            const data = await this.parseBody(response);

            // Invalid credentials on the login page should not trigger a redirect.
            if (response.status === 401 && token && endpoint !== '/auth/login') {
                this.clearAuth();
                setTimeout(() => { window.location.href = '/static/login.html'; }, 800);
                throw new Error('انتهت جلستك. سجّل الدخول من جديد.');
            }

            if (!response.ok) {
                throw new Error(this.errorMessage(data, response.status));
            }
            
            return data;
        } catch (error) {
            if (error.name === 'TypeError') {
                throw new Error('تعذر الاتصال بالخادم. تحقق من الإنترنت ثم حاول مجددًا.');
            }
            throw error;
        }
    },
    
    // Auth endpoints
    auth: {
        async login(email, password) {
            const data = await API.request('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });
            return data;
        },
        
        async register(userData) {
            const data = await API.request('/users', {
                method: 'POST',
                body: JSON.stringify(userData)
            });
            return data;
        },
        
        async getProfile() {
            return await API.request('/users/me');
        }
    },
    
    // Items endpoints
    items: {
        async list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return await API.request(`/items?${query}`);
        },
        
        async get(itemId) {
            return await API.request(`/items/${itemId}`);
        },
        
        async create(itemData) {
            return await API.request('/items', {
                method: 'POST',
                body: JSON.stringify(itemData)
            });
        },
        
        async update(itemId, itemData) {
            return await API.request(`/items/${itemId}`, {
                method: 'PATCH',
                body: JSON.stringify(itemData)
            });
        },
        
        async delete(itemId) {
            return await API.request(`/items/${itemId}`, {
                method: 'DELETE'
            });
        },
        
        async uploadImage(itemId, file) {
            const formData = new FormData();
            formData.append('file', file);
            
            const token = API.getToken();
            try {
                const response = await fetch(`${API.BASE_URL}/items/${itemId}/images`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });
                const data = await API.parseBody(response);
                if (!response.ok) {
                    throw new Error(API.errorMessage(data, response.status));
                }
                return data;
            } catch (error) {
                if (error.name === 'TypeError') {
                    throw new Error('تعذر رفع الصورة بسبب مشكلة في الاتصال. حاول مجددًا.');
                }
                throw error;
            }
        },
        
        async findMatches(itemId, params = {}) {
            const query = new URLSearchParams(params).toString();
            return await API.request(`/items/${itemId}/matches?${query}`);
        }
    },
    
    // Matches endpoints
    matches: {
        async list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return await API.request(`/matches?${query}`);
        },
        
        async get(matchId) {
            return await API.request(`/matches/${matchId}`);
        },
        
        async confirm(matchId) {
            return await API.request(`/matches/${matchId}/confirm`, {
                method: 'POST',
                body: JSON.stringify({ confirmed: true })
            });
        },
        
        async reject(matchId, reason = '') {
            return await API.request(`/matches/${matchId}/confirm`, {
                method: 'POST',
                body: JSON.stringify({ confirmed: false, rejection_reason: reason })
            });
        }
    },
    
    // Notifications endpoints
    notifications: {
        async list(params = {}) {
            const query = new URLSearchParams(params).toString();
            return await API.request(`/notifications?${query}`);
        },
        
        async markRead(notificationIds) {
            return await API.request('/notifications/mark-read', {
                method: 'POST',
                body: JSON.stringify({ notification_ids: notificationIds })
            });
        },
        
        async markAllRead() {
            return await API.request('/notifications/mark-all-read', {
                method: 'POST'
            });
        }
    }
};

// UI Helpers
const UI = {
    // Show toast notification
    toast(message, type = 'info') {
        const toast = document.getElementById('toast');
        if (toast) {
            toast.textContent = message;
            toast.className = `toast show ${type}`;
            setTimeout(() => toast.classList.remove('show'), 3000);
        } else {
            console.log(`[${type}] ${message}`);
        }
    },
    
    // Update navigation based on auth state
    updateNav() {
        const authDiv = document.getElementById('navAuth');
        const userDiv = document.getElementById('navUser');
        const userName = document.getElementById('userName');
        const myItemsLink = document.getElementById('myItemsLink');
        
        if (API.isLoggedIn()) {
            const user = API.getUser();
            if (authDiv) authDiv.style.display = 'none';
            if (userDiv) userDiv.style.display = 'flex';
            if (userName) userName.textContent = user?.full_name || user?.email || 'مستخدم';
            if (myItemsLink) myItemsLink.style.display = 'inline';
        } else {
            if (authDiv) authDiv.style.display = 'flex';
            if (userDiv) userDiv.style.display = 'none';
            if (myItemsLink) myItemsLink.style.display = 'none';
        }
    },
    
    // Logout function
    logout() {
        API.clearAuth();
        window.location.href = '/';
    },
    
    // Format date
    formatDate(dateString) {
        if (!dateString) return 'غير محدد';
        return new Date(dateString).toLocaleDateString('ar-EG', {
            year: 'numeric', month: 'short', day: 'numeric'
        });
    },
    
    // Escape HTML
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    // Get category icon
    getCategoryIcon(category) {
        const icons = {
            phone: '📱', wallet: '👛', keys: '🔑', bag: '👜', laptop: '💻',
            tablet: '📱', watch: '⌚', jewelry: '💍', glasses: '👓',
            headphones: '🎧', camera: '📷', documents: '📄', pet: '🐕',
            clothing: '👕', electronics: '🔌', other: '📦'
        };
        return icons[category] || '📦';
    },

    getCategoryName(category) {
        const names = {
            phone: 'هاتف', wallet: 'محفظة', keys: 'مفاتيح', bag: 'حقيبة',
            laptop: 'حاسوب محمول', tablet: 'جهاز لوحي', watch: 'ساعة',
            jewelry: 'مجوهرات', glasses: 'نظارات', headphones: 'سماعات',
            camera: 'كاميرا', documents: 'وثائق', pet: 'حيوان أليف',
            clothing: 'ملابس', electronics: 'إلكترونيات', other: 'أخرى'
        };
        return names[category] || category || 'غير محدد';
    },
    
    // Require auth - redirect to login if not logged in
    requireAuth() {
        if (!API.isLoggedIn()) {
            window.location.href = '/static/login.html';
            return false;
        }
        return true;
    }
};

// Make logout available globally
window.logout = UI.logout;
