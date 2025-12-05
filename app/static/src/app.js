class DocCollabApp {
    constructor() {
        // Используем относительные пути для работы в Docker
        this.apiBase = '';  // Будет использовать текущий домен
        this.token = localStorage.getItem('token');
        this.currentUser = null;
        this.currentDocument = null;
        this.documents = [];
        this.websocket = null;
        this.isConnected = false;
        this.isApplyingRemoteOperation = false; // Флаг для предотвращения циклов
        this.localVersion = 0; // Версия локальных изменений
        this.syncInterval = null; // Интервал периодической синхронизации
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        
        // В демо режиме пропускаем аутентификацию
        this.showMainApp();
        await this.loadUserData();
        await this.loadDocuments();
        
        // Проверяем URL для прямого перехода к документу
        this.handleDirectDocumentAccess();
    }
    
    handleDirectDocumentAccess() {
        const path = window.location.pathname;
        const documentMatch = path.match(/\/documents\/([a-f0-9-]{36})/);
        
        if (documentMatch) {
            const documentId = documentMatch[1];
            console.log('🎯 Direct document access detected:', documentId);
            
            // Ищем документ в списке
            const document = this.documents.find(doc => doc.uuid === documentId);
            if (document) {
                console.log('📄 Document found in list, opening...');
                setTimeout(() => {
                    this.openDocument(document);
                }, 500);
            } else {
                console.log('📄 Document not in list, loading directly...');
                this.loadDocumentDirectly(documentId);
            }
        }
    }
    
    async loadDocumentDirectly(documentId) {
        try {
            const fullDocument = await this.apiRequest(`/documents/${documentId}`);
            console.log('📄 Document loaded directly:', fullDocument);
            
            // Добавляем документ в список если его там нет
            if (!this.documents.find(doc => doc.uuid === documentId)) {
                this.documents.unshift(fullDocument);
                this.renderDocumentList();
            }
            
            this.openDocument(fullDocument);
        } catch (error) {
            console.error('❌ Failed to load document directly:', error);
            this.showError('Ошибка', 'Не удалось загрузить документ');
        }
    }
    
    setupEventListeners() {
        // Форма входа
        window.document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.login();
        });
        
        // Кнопка выхода
        window.document.getElementById('logoutBtn').addEventListener('click', () => {
            this.logout();
        });
        
        // Новый документ
        window.document.getElementById('newDocumentBtn').addEventListener('click', () => {
            this.showNewDocumentModal();
        });
        
        window.document.getElementById('createDocumentBtn').addEventListener('click', () => {
            this.createDocument();
        });
        
        // Переключение боковой панели
        window.document.getElementById('toggleSidebar').addEventListener('click', () => {
            this.toggleSidebar();
        });
        
        // Кнопка сохранения
        window.document.getElementById('saveBtn').addEventListener('click', () => {
            this.saveDocument();
        });
        
        // Режим совместной работы
        window.document.getElementById('collaborationMode').addEventListener('change', (e) => {
            this.toggleCollaborationMode(e.target.checked);
        });
        
        // Кнопка экспорта
        window.document.getElementById('exportBtn').addEventListener('click', () => {
            this.exportDocument();
        });
        
        // Кнопка "назад"
        window.document.getElementById('backBtn').addEventListener('click', () => {
            this.backToDocumentList();
        });
    }
    
    async apiRequest(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };
        
        // В демо режиме не отправляем токен
        // if (this.token) {
        //     config.headers.Authorization = `Bearer ${this.token}`;
        // }
        
        try {
            const response = await fetch(url, config);
            
            // В демо режиме не обрабатываем 401 как ошибку
            // if (response.status === 401) {
            //     this.logout();
            //     throw new Error('Unauthorized');
            // }
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Request failed');
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }
    
    async validateToken() {
        // В демо режиме используем существующего пользователя
        this.currentUser = {
            uuid: "c1de4629-e46b-4baf-b401-da37097508f7",
            username: "newuser",
            email: "newuser@example.com"
        };
    }
    
    async login() {
        const email = window.document.getElementById('email').value;
        const password = window.document.getElementById('password').value;
        const loginBtn = window.document.getElementById('loginBtn');
        const btnText = loginBtn.querySelector('.btn-text');
        const spinner = loginBtn.querySelector('.loading-spinner');
        
        // Показываем загрузку
        btnText.style.display = 'none';
        spinner.style.display = 'inline-block';
        loginBtn.disabled = true;
        
        try {
            const response = await this.apiRequest('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ email, password })
            });
            
            this.token = response.access_token;
            localStorage.setItem('token', this.token);
            
            await this.validateToken();
            this.showMainApp();
            await this.loadUserData();
            await this.loadDocuments();
            
        } catch (error) {
            this.showError('Ошибка входа', error.message);
        } finally {
            // Скрываем загрузку
            btnText.style.display = 'inline';
            spinner.style.display = 'none';
            loginBtn.disabled = false;
        }
    }
    
    logout() {
        this.token = null;
        this.currentUser = null;
        this.currentDocument = null;
        localStorage.removeItem('token');
        
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        this.showLoginScreen();
    }
    
    async loadUserData() {
        if (!this.currentUser) return;
        
        window.document.getElementById('userName').textContent = this.currentUser.username;
        window.document.getElementById('userEmail').textContent = this.currentUser.email;
        
        // Устанавливаем аватар
        const avatar = window.document.getElementById('userAvatar');
        avatar.textContent = this.currentUser.username.charAt(0).toUpperCase();
        avatar.style.backgroundColor = this.getUserColor(this.currentUser.uuid);
    }
    
    async loadDocuments() {
        console.log('loadDocuments called');
        try {
            const response = await this.apiRequest('/documents/');
            console.log('Documents API response:', response);
            this.documents = response.documents || [];
            console.log('Documents set:', this.documents);
            this.renderDocumentList();
        } catch (error) {
            console.error('Failed to load documents:', error);
            this.showError('Ошибка', 'Не удалось загрузить документы');
        }
    }
    
    renderDocumentList() {
        console.log('renderDocumentList called, documents count:', this.documents.length);
        console.log('Documents:', this.documents);
        
        const listElement = window.document.getElementById('documentList');
        console.log('Document list element found:', !!listElement);
        
        if (!listElement) {
            console.error('Document list element not found!');
            return;
        }
        
        listElement.innerHTML = '';
        
        if (this.documents.length === 0) {
            console.log('No documents to display');
            listElement.innerHTML = `
                <li class="text-center text-muted p-3">
                    <i class="fas fa-folder-open"></i>
                    <div>Нет документов</div>
                    <small>Создайте свой первый документ</small>
                </li>
            `;
            return;
        }
        
        console.log('Rendering documents:', this.documents);
        
        this.documents.forEach((doc, index) => {
            console.log(`Rendering document ${index}:`, doc);
            
            const li = window.document.createElement('li');
            li.className = 'document-item';
            if (this.currentDocument && this.currentDocument.uuid === doc.uuid) {
                li.classList.add('active');
            }
            
            const updatedAt = new Date(doc.updated_at).toLocaleDateString('ru-RU');
            const wordCount = doc.word_count || 0;
            
            li.innerHTML = `
                <div class="document-title">${this.escapeHtml(doc.title)}</div>
                <div class="document-meta">
                    ${wordCount} слов • ${updatedAt}
                </div>
            `;
            
            li.addEventListener('click', () => {
                console.log('Document clicked:', doc);
                this.openDocument(doc);
            });
            
            listElement.appendChild(li);
            console.log(`Document ${index} added to list`);
        });
        
        console.log('Document list rendering completed');
    }
    
    async openDocument(doc) {
        try {
            console.log('Opening document:', doc);
            
            const fullDocument = await this.apiRequest(`/documents/${doc.uuid}`);
            console.log('Full document loaded:', fullDocument);
            
            this.currentDocument = fullDocument;
            this.renderDocumentList();
            
            // 1. Скрываем welcome screen
            const welcomeScreen = window.document.getElementById('welcomeScreen');
            if (welcomeScreen) {
                welcomeScreen.style.display = 'none';
                console.log('Welcome screen hidden');
            }
            
            // 2. Показываем editor container
            const editorContainer = window.document.getElementById('editorContainer');
            if (editorContainer) {
                editorContainer.style.display = 'flex';
                editorContainer.style.opacity = '1';
                console.log('Editor container shown');
            }
            
            // 3. Устанавливаем заголовок и UI элементы
            window.document.getElementById('backBtn').style.display = 'block';
            window.document.getElementById('documentTitle').textContent = fullDocument.title;
            window.document.getElementById('documentVersion').style.display = 'inline-block';
            window.document.getElementById('documentVersion').textContent = `v${fullDocument.version}`;
            window.document.getElementById('saveBtn').style.display = 'block';
            window.document.getElementById('shareBtn').style.display = 'block';
            window.document.getElementById('exportBtn').style.display = 'block';
            
            // 4. ПОПРАВКА: Получаем элемент textarea/editor
            let editorElement;
            
            // Сначала пробуем найти CodeMirror
            if (window.editor && typeof window.editor.setValue === 'function') {
                window.editor.setValue(fullDocument.content || '');
                editorElement = window.editor.getWrapperElement();
                console.log('Using CodeMirror editor');
                
                // Добавляем обработчик изменений для CodeMirror
                window.editor.on('change', (change) => {
                    if (!this.isApplyingRemoteOperation) {
                        this.handleLocalChange(change);
                    }
                });
            }
            // Если нет CodeMirror, используем textarea
            else {
                const textarea = window.document.getElementById('editor');
                if (textarea) {
                    textarea.value = fullDocument.content || '';
                    textarea.style.display = 'block';
                    textarea.style.width = '100%';
                    textarea.style.height = '100%';
                    textarea.style.padding = '20px';
                    textarea.style.fontSize = '16px';
                    textarea.style.lineHeight = '1.5';
                    textarea.style.border = '1px solid #ddd';
                    textarea.style.borderRadius = '4px';
                    textarea.style.fontFamily = 'monospace';
                    textarea.style.outline = 'none';
                    textarea.style.resize = 'none';
                    textarea.focus();
                    editorElement = textarea;
                    console.log('Using textarea editor with content length:', fullDocument.content?.length || 0);
                    
                    // Добавляем обработчик изменений для textarea
                    let lastValue = textarea.value;
                    textarea.addEventListener('input', () => {
                        if (!this.isApplyingRemoteOperation && textarea.value !== lastValue) {
                            const change = {
                                origin: 'input',
                                from: {line: 0, ch: lastValue.length},
                                to: {line: 0, ch: textarea.value.length},
                                text: [textarea.value.slice(lastValue.length)],
                                removed: []
                            };
                            this.handleLocalChange(change);
                            lastValue = textarea.value;
                        }
                    });
                }
            }
            
            // 5. Подключаем WebSocket для совместного редактирования
            this.connectWebSocket(fullDocument.uuid);
            
            // 6. Прокручиваем к редактору
            if (editorElement) {
                editorElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
            
            console.log('Document opened successfully');
            
        } catch (error) {
            console.error('Failed to open document:', error);
            this.showError('Ошибка', 'Не удалось открыть документ: ' + error.message);
        }
    }
    
    backToDocumentList() {
        this.currentDocument = null;
        this.renderDocumentList();
        
        window.document.getElementById('welcomeScreen').style.display = 'flex';
        window.document.getElementById('editorContainer').style.display = 'none';
        window.document.getElementById('backBtn').style.display = 'none';
        window.document.getElementById('documentTitle').textContent = 'Выберите документ';
        window.document.getElementById('documentVersion').style.display = 'none';
        window.document.getElementById('saveBtn').style.display = 'none';
        window.document.getElementById('shareBtn').style.display = 'none';
        window.document.getElementById('exportBtn').style.display = 'none';
        window.document.getElementById('activeUsers').style.display = 'none';
        
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
    
    async saveDocument() {
        if (!this.currentDocument) return;
        
        let content = '';
        
        // Получаем содержимое из редактора или из textarea
        if (window.editor && typeof window.editor.getValue === 'function') {
            content = window.editor.getValue();
            console.log('Content from CodeMirror:', content);
        } else {
            const textarea = window.document.getElementById('editor');
            if (textarea) {
                content = textarea.value;
                console.log('Content from textarea:', content);
            }
        }
        
        console.log('Saving document with content length:', content.length);
        console.log('Content preview:', content.substring(0, 100));
        
        const saveBtn = window.document.getElementById('saveBtn');
        const originalText = saveBtn.innerHTML;
        
        try {
            saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Сохранение...';
            saveBtn.disabled = true;
            
            const response = await this.apiRequest(`/documents/${this.currentDocument.uuid}`, {
                method: 'PUT',
                body: JSON.stringify({
                    content: content
                })
            });
            
            console.log('Save response:', response);
            
            this.currentDocument = response;
            window.document.getElementById('documentVersion').textContent = `v${response.version}`;
            
            // Показываем успешное сохранение
            saveBtn.innerHTML = '<i class="fas fa-check"></i> Сохранено';
            setTimeout(() => {
                saveBtn.innerHTML = originalText;
                saveBtn.disabled = false;
            }, 2000);
            
        } catch (error) {
            console.error('Failed to save document:', error);
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
            this.showError('Ошибка', 'Не удалось сохранить документ');
        }
    }
    
    async createDocument() {
        const title = window.document.getElementById('newDocumentTitle').value.trim();
        
        if (!title) {
            this.showError('Ошибка', 'Введите название документа');
            return;
        }
        
        try {
            const response = await this.apiRequest('/documents/', {
                method: 'POST',
                body: JSON.stringify({ title, content: '' })
            });
            
            // Закрываем модальное окно
            const modal = bootstrap.Modal.getInstance(window.document.getElementById('newDocumentModal'));
            modal.hide();
            
            // Очищаем форму
            window.document.getElementById('newDocumentTitle').value = '';
            
            // Добавляем документ в список и открываем его
            this.documents.unshift(response);
            this.renderDocumentList();
            this.openDocument(response);
            
        } catch (error) {
            console.error('Failed to create document:', error);
            this.showError('Ошибка', 'Не удалось создать документ');
        }
    }
    
    async connectWebSocket(documentId) {
        console.log('🔌 connectWebSocket called with documentId:', documentId);
        console.log('👤 Current user:', this.currentUser);
        
        if (!this.currentUser) {
            console.error('❌ No current user, cannot connect WebSocket');
            return;
        }
        
        console.log('🌐 Window location:', {
            protocol: window.location.protocol,
            host: window.location.host,
            href: window.location.href
        });
        
        // Закрываем предыдущее соединение если есть
        if (this.websocket) {
            this.websocket.close();
        }
        
        // Используем текущий домен для WebSocket
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.host;
        const wsUrl = `${wsProtocol}//${wsHost}/collaboration/documents/${documentId}/ws/${this.currentUser.uuid}`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected successfully');
                this.updateConnectionStatus(true);
                this.isConnected = true;
                this.startPeriodicSync();
                
                // Показываем индикатор совместной работы
                const activeUsersDiv = window.document.getElementById('activeUsers');
                if (activeUsersDiv) {
                    activeUsersDiv.style.display = 'block';
                    console.log('Active users panel shown');
                }
            };
            
            this.websocket.onmessage = (event) => {
                const message = JSON.parse(event.data);
                console.log('📨 WebSocket message received:', message);
                this.handleWebSocketMessage(message);
            };
            
            this.websocket.onclose = (event) => {
                console.log('❌ WebSocket disconnected:', event.code, event.reason);
                this.updateConnectionStatus(false);
                this.isConnected = false;
                this.stopPeriodicSync();
                
                // Скрываем индикатор совместной работы
                const activeUsersDiv = window.document.getElementById('activeUsers');
                if (activeUsersDiv) {
                    activeUsersDiv.style.display = 'none';
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('🚫 WebSocket error:', error);
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            console.error('💥 Failed to connect WebSocket:', error);
            this.updateConnectionStatus(false);
        }
    }
    
    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'operation':
                this.handleRemoteOperation(message.data);
                break;
            case 'sync_response':
                this.handleSyncResponse(message.data);
                break;
            case 'cursor':
                this.handleRemoteCursor(message.data);
                break;
            case 'user_joined':
                this.handleUserJoined(message.data);
                break;
            case 'user_left':
                this.handleUserLeft(message.data);
                break;
            case 'error':
                this.showError('Ошибка', message.data.message);
                break;
        }
    }
    
    handleLocalChange(change) {
        if (!this.isConnected || !this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            console.log('WebSocket not connected, skipping local change');
            return;
        }
        
        console.log('Handling local change:', change);
        
        // Получаем текущее содержимое редактора
        let content = '';
        if (window.editor && typeof window.editor.getValue === 'function') {
            content = window.editor.getValue();
        } else {
            const textarea = window.document.getElementById('editor');
            if (textarea) {
                content = textarea.value;
            }
        }
        
        // Создаем операцию замены всего содержимого
        const operation = {
            type: 'operation',
            data: {
                type: 'replace',
                content: content,
                version: this.localVersion++
            }
        };
        
        console.log('Sending operation:', operation);
        this.websocket.send(JSON.stringify(operation));
    }
    
    getOperationType(change) {
        if (change.origin === 'input') {
            return 'insert';
        } else if (change.origin === '+delete') {
            return 'delete';
        }
        return 'insert';
    }
    
    getOperationPosition(change) {
        if (change.from && typeof change.from.ch === 'number') {
            return change.from.ch;
        }
        return 0;
    }
    
    getOperationContent(change) {
        if (change.text && Array.isArray(change.text) && change.text.length > 0) {
            return change.text.join('\n');
        }
        return '';
    }
    
    getOperationLength(change) {
        if (change.removed && Array.isArray(change.removed)) {
            return change.removed.join('\n').length;
        }
        return 0;
    }
    
    handleRemoteOperation(operation) {
        console.log('🔄 Applying remote operation:', operation);
        
        // Устанавливаем флаг, чтобы предотвратить отправку изменений обратно
        this.isApplyingRemoteOperation = true;
        
        try {
            // Работаем с CodeMirror если доступен
            if (window.editor && typeof window.editor.getValue === 'function') {
                if (operation.type === 'replace') {
                    const newContent = operation.content || '';
                    window.editor.setValue(newContent);
                    console.log('✅ Replace operation applied:', newContent);
                } else if (operation.type === 'insert') {
                    const currentContent = window.editor.getValue();
                    const pos = operation.position || 0;
                    const text = operation.content || '';
                    const newContent = currentContent.slice(0, pos) + text + currentContent.slice(pos);
                    window.editor.setValue(newContent);
                    console.log('✅ Insert operation applied:', { pos, text });
                } else if (operation.type === 'delete') {
                    const currentContent = window.editor.getValue();
                    const pos = operation.position || 0;
                    const length = operation.length || 0;
                    const newContent = currentContent.slice(0, pos) + currentContent.slice(pos + length);
                    window.editor.setValue(newContent);
                    console.log('✅ Delete operation applied:', { pos, length });
                }
            }
            // Работаем с textarea если CodeMirror недоступен
            else {
                const textarea = window.document.getElementById('editor');
                if (textarea) {
                    if (operation.type === 'replace') {
                        const newContent = operation.content || '';
                        textarea.value = newContent;
                        console.log('✅ Replace operation applied to textarea:', newContent);
                    } else if (operation.type === 'insert') {
                        const currentContent = textarea.value;
                        const pos = operation.position || 0;
                        const text = operation.content || '';
                        const newContent = currentContent.slice(0, pos) + text + currentContent.slice(pos);
                        textarea.value = newContent;
                        console.log('✅ Insert operation applied to textarea:', { pos, text });
                    } else if (operation.type === 'delete') {
                        const currentContent = textarea.value;
                        const pos = operation.position || 0;
                        const length = operation.length || 0;
                        const newContent = currentContent.slice(0, pos) + currentContent.slice(pos + length);
                        textarea.value = newContent;
                        console.log('✅ Delete operation applied to textarea:', { pos, length });
                    }
                }
            }
        } catch (error) {
            console.error('❌ Error applying remote operation:', error);
        } finally {
            // Сбрасываем флаг через небольшую задержку
            setTimeout(() => {
                this.isApplyingRemoteOperation = false;
            }, 100);
        }
    }
    
    handleRemoteCursor(cursorData) {
        // Обновляем курсор удаленного пользователя
        console.log('Remote cursor update:', cursorData);
        // Здесь будет обновление визуализации курсоров
    }
    
    handleUserJoined(userData) {
        console.log('User joined:', userData);
        this.updateActiveUsers();
    }
    
    handleUserLeft(userData) {
        console.log('User left:', userData);
        this.updateActiveUsers();
    }
    
    async updateActiveUsers() {
        if (!this.currentDocument) return;
        
        try {
            const response = await this.apiRequest(`/collaboration/documents/${this.currentDocument.uuid}/users`);
            this.renderActiveUsers(response.active_sessions);
        } catch (error) {
            console.error('Failed to load active users:', error);
        }
    }
    
    renderActiveUsers(sessions) {
        const usersList = window.document.getElementById('usersList');
        const activeUsersDiv = window.document.getElementById('activeUsers');
        
        if (sessions.length === 0) {
            activeUsersDiv.style.display = 'none';
            return;
        }
        
        activeUsersDiv.style.display = 'block';
        usersList.innerHTML = '';
        
        sessions.forEach(session => {
            const userDiv = window.document.createElement('div');
            userDiv.className = 'd-flex align-items-center mb-2';
            
            const avatar = window.document.createElement('div');
            avatar.className = 'user-avatar';
            avatar.style.backgroundColor = session.color;
            avatar.textContent = session.user_id.charAt(0).toUpperCase();
            
            const name = window.document.createElement('div');
            name.className = 'ms-2';
            name.innerHTML = `
                <div class="fw-bold">Пользователь ${session.user_id.slice(0, 8)}</div>
                <small class="text-muted">
                    <span class="status-indicator status-online"></span>
                    Редактирует
                </small>
            `;
            
            userDiv.appendChild(avatar);
            userDiv.appendChild(name);
            usersList.appendChild(userDiv);
        });
    }
    
    startPeriodicSync() {
        // Запускаем периодическую синхронизацию каждые 2 секунды
        this.syncInterval = setInterval(() => {
            if (this.isConnected && this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.requestSync();
            }
        }, 2000);
        console.log('🔄 Запущена периодическая синхронизация');
    }
    
    stopPeriodicSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
            console.log('⏹️ Остановлена периодическая синхронизация');
        }
    }
    
    requestSync() {
        const syncMessage = {
            type: 'sync_request'
        };
        this.websocket.send(JSON.stringify(syncMessage));
        console.log('📤 Запрошена синхронизация');
    }
    
    handleSyncResponse(data) {
        this.isApplyingRemoteOperation = true;
        try {
            const serverContent = data.content || '';
            const serverVersion = data.version || 0;
            
            // Применяем состояние с сервера только если версия новее
            if (serverVersion > this.localVersion) {
                if (window.editor && typeof window.editor.setValue === 'function') {
                    window.editor.setValue(serverContent);
                } else {
                    const textarea = window.document.getElementById('editor');
                    if (textarea) {
                        textarea.value = serverContent;
                    }
                }
                this.localVersion = serverVersion;
                console.log(`🔄 Синхронизировано с сервером: версия ${serverVersion}`);
            }
        } catch (error) {
            console.error(`❌ Ошибка синхронизации: ${error.message}`);
        } finally {
            setTimeout(() => {
                this.isApplyingRemoteOperation = false;
            }, 100);
        }
    }

    toggleCollaborationMode(enabled) {
        if (enabled && this.currentDocument) {
            this.connectWebSocket(this.currentDocument.uuid);
            window.document.getElementById('activeUsers').style.display = 'block';
        } else {
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }
            this.stopPeriodicSync();
            window.document.getElementById('activeUsers').style.display = 'none';
        }
    }
    
    async exportDocument() {
        if (!this.currentDocument) return;
        
        try {
            const response = await this.apiRequest(`/documents/${this.currentDocument.uuid}/export`, {
                method: 'POST',
                body: JSON.stringify({ format: 'txt' })
            });
            
            // Создаем ссылку для скачивания
            const blob = new Blob([response.content], { type: 'text/plain' });
            const url = window.URL.createObjectURL(blob);
            const a = window.document.createElement('a');
            a.href = url;
            a.download = response.filename;
            window.document.body.appendChild(a);
            a.click();
            window.document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
        } catch (error) {
            console.error('Failed to export document:', error);
            this.showError('Ошибка', 'Не удалось экспортировать документ');
        }
    }
    
    showNewDocumentModal() {
        const modal = new bootstrap.Modal(window.document.getElementById('newDocumentModal'));
        modal.show();
        window.document.getElementById('newDocumentTitle').focus();
    }
    
    toggleSidebar() {
        const sidebar = window.document.getElementById('sidebar');
        sidebar.classList.toggle('collapsed');
    }
    
    showLoginScreen() {
        window.document.getElementById('loginScreen').style.display = 'flex';
        window.document.getElementById('mainApp').style.display = 'none';
    }
    
    showMainApp() {
        window.document.getElementById('loginScreen').style.display = 'none';
        window.document.getElementById('mainApp').style.display = 'block';
    }
    
    updateConnectionStatus(connected) {
        const statusElement = window.document.getElementById('connectionStatus');
        const textElement = window.document.getElementById('connectionText');
        
        if (connected) {
            statusElement.className = 'connection-status connected';
            textElement.textContent = 'Подключено';
        } else {
            statusElement.className = 'connection-status disconnected';
            textElement.textContent = 'Нет соединения';
        }
    }
    
    getUserColor(userId) {
        const colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
        ];
        const hash = userId.split('').reduce((a, b) => {
            a = ((a << 5) - a) + b.charCodeAt(0);
            return a & a;
        }, 0);
        return colors[Math.abs(hash) % colors.length];
    }
    
    escapeHtml(text) {
        const div = window.document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showError(title, message) {
        // Создаем простое уведомление об ошибке
        const alert = window.document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        alert.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alert.innerHTML = `
            <strong>${title}</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        window.document.body.appendChild(alert);
        
        // Автоматически удаляем через 5 секунд
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
        }, 5000);
    }
}

// Инициализируем приложение при загрузке страницы
window.document.addEventListener('DOMContentLoaded', () => {
    window.app = new DocCollabApp();
});