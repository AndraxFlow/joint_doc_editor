class CollaborativeEditor {
    constructor() {
        this.editor = null;
        this.documentId = null;
        this.userId = null;
        this.websocket = null;
        this.localVersion = 0;
        this.pendingOperations = [];
        this.isApplyingRemoteOperation = false;
        this.userCursors = new Map();
        this.operationQueue = [];
        this.isProcessingQueue = false;
        
        this.init();
    }
    
    init() {
        // Инициализация будет вызвана из app.js
        window.initializeEditor = (content = '') => {
            this.createEditor(content);
        };
        
        // Глобальные функции для операций
        window.sendOperation = (operation) => {
            this.sendOperation(operation);
        };
        
        window.updateCursor = (position) => {
            this.updateLocalCursor(position);
        };
    }
    
    createEditor(content) {
        const textarea = window.document.getElementById('editor');
        
        if (!textarea) {
            console.error('Textarea element not found!');
            return;
        }
        
        try {
            this.editor = CodeMirror.fromTextArea(textarea, {
                mode: 'plain',
                theme: 'default',
                lineNumbers: true,
                lineWrapping: true,
                autoCloseBrackets: true,
                matchBrackets: true,
                indentUnit: 4,
                tabSize: 4,
                indentWithTabs: false,
                value: content
            });
            
            // Устанавливаем глобальную ссылку на редактор
            window.editor = this.editor;
            
            // Устанавливаем начальное содержимое
            if (content !== undefined && content !== null) {
                this.editor.setValue(content);
            }
            
            // Обработчики событий
            this.editor.on('change', (change) => {
                if (!this.isApplyingRemoteOperation) {
                    this.handleLocalChange(change);
                }
            });
            
            this.editor.on('cursorActivity', () => {
                if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                    const cursor = this.editor.getCursor();
                    const position = this.editor.indexFromPos(cursor);
                    this.updateLocalCursor(position);
                }
            });
            
            // Обработчик изменений размера
            window.addEventListener('resize', () => {
                this.editor.refresh();
            });
            
            // Горячие клавиши
            this.editor.setOption('extraKeys', {
                'Ctrl-S': () => {
                    if (window.app) {
                        window.app.saveDocument();
                    }
                },
                'Cmd-S': () => {
                    if (window.app) {
                        window.app.saveDocument();
                    }
                }
            });
            
            console.log('Editor initialization completed');
            
        } catch (error) {
            console.error('Error creating CodeMirror editor:', error);
        }
    }
    
    handleLocalChange(change) {
        if (change.origin === 'setValue') {
            // Полная замена содержимого (при загрузке документа)
            return;
        }
        
        // Создаем операции для локальных изменений
        const operations = this.changeToOperations(change);
        
        operations.forEach(operation => {
            this.localVersion++;
            operation.version = this.localVersion;
            this.pendingOperations.push(operation);
            
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.sendOperation(operation);
            }
        });
    }
    
    changeToOperations(change) {
        const operations = [];
        
        if (change.origin === 'insert') {
            const position = this.calculatePosition(change.from);
            operations.push({
                type: 'insert',
                position: position,
                content: change.text.join(''),
                length: change.text.join('').length
            });
        } else if (change.origin === 'delete') {
            const position = this.calculatePosition(change.from);
            const deletedText = change.removed.join('');
            operations.push({
                type: 'delete',
                position: position,
                content: '',
                length: deletedText.length
            });
        } else if (change.origin === '+input' || change.origin === 'paste') {
            // Комплексные изменения
            const position = this.calculatePosition(change.from);
            if (change.text.length > 0) {
                operations.push({
                    type: 'insert',
                    position: position,
                    content: change.text.join(''),
                    length: change.text.join('').length
                });
            }
            if (change.removed && change.removed.length > 0) {
                operations.push({
                    type: 'delete',
                    position: position,
                    content: '',
                    length: change.removed.join('').length
                });
            }
        }
        
        return operations;
    }
    
    calculatePosition(pos) {
        return this.editor.indexFromPos(pos);
    }
    
    positionToCursor(position) {
        return this.editor.posFromIndex(position);
    }
    
    sendOperation(operation) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            return;
        }
        
        const message = {
            type: 'operation',
            data: {
                type: operation.type,
                position: operation.position,
                content: operation.content,
                length: operation.length,
                version: operation.version
            }
        };
        
        this.websocket.send(JSON.stringify(message));
    }
    
    updateLocalCursor(position) {
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            return;
        }
        
        const message = {
            type: 'cursor',
            data: {
                position: position,
                selection_start: position,
                selection_end: position
            }
        };
        
        this.websocket.send(JSON.stringify(message));
    }
    
    applyRemoteOperation(operation) {
        this.isApplyingRemoteOperation = true;
        
        try {
            const cursor = this.editor.getCursor();
            const currentContent = this.editor.getValue();
            
            // Трансформируем операцию относительно pending операций
            const transformedOp = this.transformOperation(operation);
            
            // Применяем операцию к редактору
            this.applyOperationToEditor(transformedOp);
            
            // Обновляем локальную версию
            this.localVersion = Math.max(this.localVersion, operation.version);
            
            // Восстанавливаем курсор
            this.editor.setCursor(cursor);
            
        } catch (error) {
            console.error('Failed to apply remote operation:', error);
        } finally {
            this.isApplyingRemoteOperation = false;
        }
    }
    
    transformOperation(operation) {
        let transformedOp = { ...operation };
        
        // Трансформируем относительно всех pending операций
        for (const pendingOp of this.pendingOperations) {
            transformedOp = this.transformTwoOperations(transformedOp, pendingOp);
        }
        
        return transformedOp;
    }
    
    transformTwoOperations(op1, op2) {
        // Упрощенная реализация Operational Transformation
        if (op1.type === 'insert' && op2.type === 'insert') {
            if (op1.position <= op2.position) {
                return op1;
            } else {
                return {
                    ...op1,
                    position: op1.position + op2.content.length
                };
            }
        } else if (op1.type === 'delete' && op2.type === 'insert') {
            if (op1.position <= op2.position) {
                return op1;
            } else {
                return {
                    ...op1,
                    position: op1.position + op2.content.length
                };
            }
        } else if (op1.type === 'insert' && op2.type === 'delete') {
            if (op1.position <= op2.position) {
                return op1;
            } else if (op1.position >= op2.position + op2.length) {
                return {
                    ...op1,
                    position: op1.position - op2.length
                };
            } else {
                return {
                    ...op1,
                    position: op2.position
                };
            }
        } else if (op1.type === 'delete' && op2.type === 'delete') {
            if (op1.position + op1.length <= op2.position) {
                return op1;
            } else if (op1.position >= op2.position + op2.length) {
                return {
                    ...op1,
                    position: op1.position - op2.length
                };
            } else {
                // Пересекающиеся удаления
                const start = Math.max(op1.position, op2.position);
                const end = Math.min(op1.position + op1.length, op2.position + op2.length);
                const overlap = end - start;
                
                if (op1.position < op2.position) {
                    return {
                        ...op1,
                        length: Math.max(0, op1.length - overlap)
                    };
                } else {
                    return {
                        ...op1,
                        position: op2.position,
                        length: Math.max(0, op1.length - overlap)
                    };
                }
            }
        }
        
        return op1;
    }
    
    applyOperationToEditor(operation) {
        if (operation.type === 'insert') {
            const pos = this.positionToCursor(operation.position);
            this.editor.replaceRange(operation.content, pos, pos);
        } else if (operation.type === 'delete') {
            const startPos = this.positionToCursor(operation.position);
            const endPos = this.positionToCursor(operation.position + operation.length);
            this.editor.replaceRange('', startPos, endPos);
        }
    }
    
    updateRemoteCursor(userId, cursorData) {
        // Удаляем старый курсор пользователя
        this.removeUserCursor(userId);
        
        // Создаем новый курсор
        const cursorElement = this.createUserCursor(userId, cursorData);
        
        // Сохраняем информацию о курсоре
        this.userCursors.set(userId, {
            element: cursorElement,
            data: cursorData
        });
    }
    
    createUserCursor(userId, cursorData) {
        const cursor = window.document.createElement('div');
        cursor.className = 'user-cursor';
        cursor.style.backgroundColor = this.getUserColor(userId);
        cursor.id = `cursor-${userId}`;
        
        // Позиционируем курсор
        this.positionCursor(cursor, cursorData.position);
        
        // Добавляем в DOM
        this.editor.getWrapperElement().appendChild(cursor);
        
        return cursor;
    }
    
    positionCursor(cursorElement, position) {
        const pos = this.positionToCursor(position);
        const coords = this.editor.cursorCoords(pos);
        
        cursorElement.style.left = `${coords.left}px`;
        cursorElement.style.top = `${coords.top}px`;
    }
    
    removeUserCursor(userId) {
        const existingCursor = window.document.getElementById(`cursor-${userId}`);
        if (existingCursor) {
            existingCursor.remove();
        }
        this.userCursors.delete(userId);
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
    
    setContent(content) {
        if (this.editor) {
            this.isApplyingRemoteOperation = true;
            this.editor.setValue(content);
            this.isApplyingRemoteOperation = false;
        }
    }
    
    getContent() {
        return this.editor ? this.editor.getValue() : '';
    }
    
    focus() {
        if (this.editor) {
            this.editor.focus();
        }
    }
    
    refresh() {
        if (this.editor) {
            this.editor.refresh();
        }
    }
    
    destroy() {
        if (this.editor) {
            this.editor.toTextArea();
            this.editor = null;
            window.editor = null;
        }
        
        // Очищаем курсоры
        this.userCursors.forEach((cursor, userId) => {
            this.removeUserCursor(userId);
        });
        
        // Закрываем WebSocket
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
    
    // Утилиты для работы с операциями
    static createInsertOperation(position, content) {
        return {
            type: 'insert',
            position: position,
            content: content,
            length: content.length,
            timestamp: new Date().toISOString()
        };
    }
    
    static createDeleteOperation(position, length) {
        return {
            type: 'delete',
            position: position,
            content: '',
            length: length,
            timestamp: new Date().toISOString()
        };
    }
    
    static createRetainOperation(length) {
        return {
            type: 'retain',
            position: 0,
            content: '',
            length: length,
            timestamp: new Date().toISOString()
        };
    }
}

// Расширяем глобальный объект для доступа из других скриптов
window.CollaborativeEditor = CollaborativeEditor;

// Инициализируем редактор при загрузке страницы
window.document.addEventListener('DOMContentLoaded', () => {
    window.editorInstance = new CollaborativeEditor();
});