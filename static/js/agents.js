// static/js/agents.js - FINAL OPTIMIZED VERSION
console.log("🔥 agents.js FILE LOADED");
class AgentManager {
    
    constructor() {
        this.currentConnection = null;
        this.selectedTables = new Set();
        this.selectedColumns = {};
        this.currentChatAgent = null;
        this.currentAgentType = 'bi';
        this.chatHistory = [];
        this.currentChatType = null;
        this.currentAgentId = null;

        this.initializeEventListeners();
        
    }

    initializeEventListeners() {
        // Agent creation modal events
        document.getElementById('agentConnections')?.addEventListener('change', (e) => {
            this.onConnectionSelect(e.target.value);
        });

        document.getElementById('generateSchemaBtn')?.addEventListener('click', () => {
            this.generateSchemaContext();
        });

        document.getElementById('createAgentBtn')?.addEventListener('click', () => {
            this.createAgent();
        });

        // Form validation events
        document.getElementById('agentName')?.addEventListener('input', () => {
            this.updateCreateAgentButton();
        });

        document.getElementById('agentDescription')?.addEventListener('input', () => {
            this.updateCreateAgentButton();
        });

        // Chat modal events
        document.getElementById('sendChatMessageBtn')?.addEventListener('click', () => {
            this.sendChatMessage();
        });

        document.getElementById('clearChatBtn')?.addEventListener('click', () => {
            this.clearChat();
        });

        document.getElementById('chatInput')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendChatMessage();
        });

        // Load agents if on agents page
        if (document.getElementById('agents-tbody')) {
            this.loadBIAgents();
        }
    }
    initializeContainerEvents() {
    console.log("initializeContainerEvents() placeholder");
    }

    // ========== SIDEBAR CHAT FUNCTIONS ==========

    openAgentChat(type, agentId, agentName) {
        this.currentChatType = type;
        this.currentAgentId = agentId;
        this.currentAgentType = type;
        
        const agentList = document.getElementById(type + '-agents-list');
        const chatDiv = document.getElementById(type + '-agent-chat');
        const chatTitle = document.getElementById(type + '-chat-title');
        const messagesDiv = document.getElementById(type + '-chat-messages');
        
        if (agentList) agentList.classList.add('hidden');
        if (chatDiv) chatDiv.classList.remove('hidden');
        if (chatTitle) chatTitle.textContent = `Chat with ${agentName}`;
        
        const welcomeMessage = type === 'bi' ? 
            "Hello! I'm your BI Agent. Ask me anything about your business data using natural language." :
            "Hello! I'm your Reasoning Agent. I can help you with complex analysis and decision-making.";
        
        if (messagesDiv) {
            messagesDiv.innerHTML = `
                <div class="message">
                    <div class="message-content">
                        <div class="welcome-message">
                            <strong>🤖 ${type === 'bi' ? 'BI' : 'Reasoning'} Assistant</strong>
                            <p class="mb-0">${welcomeMessage}</p>
                        </div>
                    </div>
                </div>
            `;
        }
        
        const input = document.getElementById(type + '-message-input');
        if (input) input.focus();
    }

    closeAgentChat() {
        if (this.currentChatType) {
            const agentList = document.getElementById(this.currentChatType + '-agents-list');
            const chatDiv = document.getElementById(this.currentChatType + '-agent-chat');
            
            if (agentList) agentList.classList.remove('hidden');
            if (chatDiv) chatDiv.classList.add('hidden');
            
            this.currentChatType = null;
            this.currentAgentId = null;
        }
    }

    sendSidebarMessage(type) {
        const input = document.getElementById(type + '-message-input');
        if (!input) return;
        
        const message = input.value.trim();
        if (message === '') return;
        
        const messagesDiv = document.getElementById(type + '-chat-messages');
        if (messagesDiv) {
            const userMessageDiv = document.createElement('div');
            userMessageDiv.className = 'message user';
            userMessageDiv.innerHTML = `<div class="message-content">${message}</div>`;
            messagesDiv.appendChild(userMessageDiv);
            
            input.value = '';
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            this.sendChatMessageToBackend(this.currentAgentId, message, type);
        }
    }

    displaySidebarResponse(type, response) {
        const messagesDiv = document.getElementById(type + '-chat-messages');
        if (messagesDiv) {
            const agentMessageDiv = document.createElement('div');
            agentMessageDiv.className = 'message';
            
            if (typeof response === 'object' && response !== null) {
                agentMessageDiv.innerHTML = this.formatStructuredResponse(response);
            } else {
                agentMessageDiv.innerHTML = `<div class="message-content">${response}</div>`;
            }
            
            messagesDiv.appendChild(agentMessageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    }

    // ========== MODAL CHAT FUNCTIONS ==========

    // openChatWithAgent(agentName, agentType = 'bi') {
    //     this.currentChatAgent = agentName;
    //     this.currentAgentType = agentType;
    //     this.chatHistory = [];

    //     const title = agentType === 'bi' ? `BI Agent: ${agentName}` : `Reasoning Agent: ${agentName}`;
    //     document.getElementById('chatModalTitle').textContent = title;
        
    //     const welcomeMessage = agentType === 'bi' ?
    //         "Hello! I'm your BI Agent. Ask me anything about your business data using natural language." :
    //         "Hello! I'm your Reasoning Agent. I can help you with complex analysis and decision-making.";

    //     document.getElementById('chatMessages').innerHTML = `
    //         <div class="message">
    //             <div class="message-content">
    //                 <div class="welcome-message">
    //                     <strong>🤖 ${agentType === 'bi' ? 'BI' : 'Reasoning'} Assistant</strong>
    //                     <p class="mb-0">${welcomeMessage}</p>
    //                 </div>
    //             </div>
    //         </div>
    //     `;

    //     new bootstrap.Modal(document.getElementById('chatModal')).show();
    // }

        
    

// Main method to open chat with agent (no modal, inline panel)
     openChatWithAgent(agentName, agentType = 'bi') {
          this.currentChatAgent = agentName;
          this.currentAgentType = agentType;
          this.chatHistory = [];

          const title = agentType === 'bi' ? `BI Agent: ${agentName}` : `Reasoning Agent: ${agentName}`;
          const welcomeMessage = agentType === 'bi' ?
             "Hello! I'm your BI Agent. Ask me anything about your business data using natural language." :
             "Hello! I'm your Reasoning Agent. I can help you with complex analysis and decision-making.";

        // Render inline chat panel
            renderInlineChatPanel(title, welcomeMessage);
        }



    async sendChatMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        if (!message || !this.currentChatAgent) return;

        this.addChatMessage('user', message);
        input.value = '';

        try {
            const response = await fetch('/api/bi-agents/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    agent_name: this.currentChatAgent,
                    question: message,
                    chat_history: this.chatHistory
                })
            });

            const result = await response.json();
            
            if (response.ok) {
                let agentResponse;
                
                if (result.response && result.response.response) {
                    agentResponse = result.response.response;
                } else if (result.response) {
                    agentResponse = result.response;
                } else if (result.success !== undefined) {
                    agentResponse = this.formatStructuredResponse(result);
                } else {
                    agentResponse = JSON.stringify(result, null, 2);
                }

                this.addChatMessage('agent', agentResponse);
                window.agentManager.lastQueryResult = result;
                this.chatHistory.push({ role: 'user', content: message });
                this.chatHistory.push({ role: 'assistant', content: agentResponse });
            } else {
                this.addChatMessage('error', `Error: ${result.message || 'Unknown error'}`);
            }
        } catch (error) {
            this.addChatMessage('error', 'Sorry, I encountered an error. Please try again.');
        }
    }

    async sendChatMessageToBackend(agentId, message, type) {
        try {
            const response = await fetch('/api/bi-agents/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    agent_id: agentId,
                    question: message,
                    agent_config: this.getAgentConfig(agentId),
                    connection_name: this.getConnectionName(agentId),
                    session_id: this.getSessionId(agentId)
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                this.displaySidebarResponse(type, data);
            } else {
                this.displaySidebarResponse(type, {
                    success: false,
                    error: data.error || 'Unknown error occurred',
                    response: data.response || 'Failed to process query'
                });
            }
        } catch (error) {
            this.displaySidebarResponse(type, {
                success: false,
                error: 'Network error',
                response: 'Failed to send message. Please check your connection.'
            });
        }
    }

    addChatMessage(role, content) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role === 'user' ? 'user' : ''}`;
        messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    clearChat() {
        document.getElementById('chatMessages').innerHTML = `
            <div class="message">
                <div class="message-content">
                    <div class="welcome-message">
                        <strong>🤖 ${this.currentAgentType === 'bi' ? 'BI' : 'Reasoning'} Assistant</strong>
                        <p class="mb-0">Ask natural language questions about your data.</p>
                    </div>
                </div>
            </div>
        `;
        this.chatHistory = [];
    }

    // ========== STRUCTURED RESPONSE FORMATTING ==========

    formatStructuredResponse(response) {
        if (!response.success) {
            return `
                <div class="error-message">
                    <div class="error-header">
                        <span class="error-icon">❌</span>
                        <strong>Query Execution Failed</strong>
                    </div>
                    <div class="error-details">
                        <p><strong>Error:</strong> ${response.error}</p>
                        ${response.suggestions ? `
                            <div class="suggestions">
                                <strong>Suggestions:</strong>
                                <ul>
                                    ${response.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                        ${response.sql_query ? `
                            <div class="sql-section">
                                <details class="sql-details">
                                    <summary class="sql-summary">
                                        <span class="sql-icon">⚡</span>
                                        SQL Query
                                        <span class="toggle-arrow">▼</span>
                                    </summary>
                                    <pre class="sql-code"><code>${response.sql_query}</code></pre>
                                </details>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }

        // Format execution time nicely
        const executionTime = response.execution_time_ms < 1000 ? 
            `${Math.round(response.execution_time_ms)}ms` : 
            `${(response.execution_time_ms / 1000).toFixed(1)}s`;

        let html = `
            <div class="structured-response">
                <div class="response-header">
                    <div class="response-title">
                        <span class="success-icon">📊</span>
                        <strong>Query Results</strong>
                    </div>
                    <div class="response-meta">
                        <span class="execution-time">${executionTime}</span>
                        <span class="record-count">${response.row_count} records</span>
                    </div>
                </div>
                
                <div class="question-context">
                    <strong>Your Question:</strong> "${response.question}"
                </div>
        `;

        // 1. Quick Insights
        if (response.insights && response.insights.length > 0) {
            html += `
                <div class="insights-section">
                    <div class="section-title">
                        <span class="section-icon">💡</span>
                        <strong>Quick Insights</strong>
                    </div>
                    <div class="insights-list">
                        ${response.insights.map(insight => `
                            <div class="insight-item ${insight.type}">
                                <span class="insight-icon">${insight.icon}</span>
                                <span class="insight-text">${insight.message}</span>
                                ${insight.value ? `<span class="insight-value">${insight.value}</span>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // 2. Results Table
        if (response.data && response.data.length > 0) {
            const displayData = response.row_count > 10 ? response.data.slice(0, 5) : response.data;
            
            html += `
                <div class="results-section">
                    <div class="section-title">
                        <span class="section-icon">📋</span>
                        <strong>Results</strong>
                        ${response.row_count > 10 ? 
                            `<span class="results-count">(showing first 5 of ${response.row_count})</span>` : 
                            `<span class="results-count">(${response.row_count} records)</span>`
                        }
                    </div>
                    <div class="table-container">
                        <table class="results-table">
                            <thead>
                                <tr>
                                    ${response.columns.map(col => `<th>${col}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${displayData.map(row => `
                                    <tr>
                                        ${response.columns.map(col => `
                                            <td>${this.formatCellValue(row[col])}</td>
                                        `).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    ${response.row_count > 10 ? 
                        `<div class="more-records">... and ${response.row_count - 5} more records</div>` : ''
                    }
                </div>
            `;
        } else if (response.row_count === 0) {
            html += `
                <div class="no-results">
                    <div class="no-results-icon">🔍</div>
                    <strong>No Results Found</strong>
                    <p>The query executed successfully but returned no matching records.</p>
                </div>
            `;
        }

        // 3. SQL Query with toggle
        if (response.sql_query) {
            html += `
                <div class="sql-section">
                    <details class="sql-details">
                        <summary class="sql-summary">
                            <span class="sql-icon">⚡</span>
                            SQL Query
                            <span class="toggle-arrow">▼</span>
                        </summary>
                        <pre class="sql-code"><code>${response.sql_query}</code></pre>
                    </details>
                </div>
            `;
        }

        // 4. Metadata with toggle
        if (response.column_metadata && response.column_metadata.length > 0) {
            html += `
                <div class="metadata-section">
                    <details class="metadata-details">
                        <summary class="metadata-summary">
                            <span class="metadata-icon">📊</span>
                            Column Metadata
                            <span class="toggle-arrow">▼</span>
                        </summary>
                        <div class="metadata-list">
                            ${response.column_metadata.map(meta => `
                                <div class="column-meta">
                                    <div class="column-header">
                                        <strong class="column-name">${meta.name}</strong>
                                        <span class="column-type">${meta.type}</span>
                                    </div>
                                    <div class="column-tags">
                                        ${meta.is_numeric ? '<span class="meta-tag numeric">numeric</span>' : ''}
                                        ${meta.is_date ? '<span class="meta-tag date">date</span>' : ''}
                                        ${meta.has_nulls ? '<span class="meta-tag nulls">has nulls</span>' : ''}
                                        ${meta.unique_count ? `<span class="meta-tag unique">${meta.unique_count} unique</span>` : ''}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </details>
                </div>
            `;
        }

        html += `</div>`;
        return html;
    }

    formatCellValue(value) {
        if (value === null || value === undefined) return '<span class="null-value">NULL</span>';
        if (typeof value === 'boolean') return value ? '<span class="bool-true">✓</span>' : '<span class="bool-false">✗</span>';
        if (typeof value === 'number') return `<span class="number-value">${value.toLocaleString()}</span>`;
        
        const strValue = String(value);
        return strValue.length > 50 ? 
            `<span title="${strValue}">${strValue.substring(0, 47)}...</span>` : 
            strValue;
    }

    // ========== AGENT CREATION METHODS ==========

    showCreateAgentModal() {
        this.selectedTables.clear();
        this.selectedColumns = {};
        this.currentConnection = null;

        document.getElementById('createAgentForm').reset();
        document.getElementById('schemaSelection').style.display = 'none';
        document.getElementById('createAgentBtn').disabled = true;
        document.getElementById('generateSchemaBtn').disabled = true;
        document.getElementById('schemaContext').value = '';

        this.updatePreview();
        this.loadDatabaseConnections();
        new bootstrap.Modal(document.getElementById('createAgentModal')).show();
    }

    async loadDatabaseConnections() {
        try {
            const response = await fetch('/api/connections');
            const connections = await response.json();
            
            const select = document.getElementById('agentConnections');
            select.innerHTML = '<option value="">Select a database connection</option>';
            
            connections.forEach(conn => {
                const option = document.createElement('option');
                option.value = conn.name;
                option.textContent = `${conn.name} (${conn.type})`;
                select.appendChild(option);
            });
        } catch (error) {
            this.showNotification('Error loading database connections', 'error');
        }
    }

    async onConnectionSelect(connectionName) {
        if (!connectionName) {
            document.getElementById('schemaSelection').style.display = 'none';
            document.getElementById('createAgentBtn').disabled = true;
            return;
        }

        this.currentConnection = connectionName;
        this.showNotification(`Loading tables for ${connectionName}...`, 'info');

        try {
            const response = await fetch('/api/bi-agents/schema', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    connection_name: connectionName,
                    tables: []
                })
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.displayTables(result.schema);
                document.getElementById('schemaSelection').style.display = 'block';
                this.showNotification(`Found ${result.schema.length} tables! Click on tables to load columns.`, 'success');
            } else {
                this.showNotification('Error loading schema: ' + result.message, 'error');
                document.getElementById('schemaSelection').style.display = 'none';
            }
        } catch (error) {
            this.showNotification('Error loading database schema', 'error');
            document.getElementById('schemaSelection').style.display = 'none';
        }
    }

    displayTables(tables) {
        const container = document.getElementById('schemaTables');
        container.innerHTML = '';

        if (!tables || tables.length === 0) {
            container.innerHTML = `
                <div class="alert alert-warning">
                    No tables found in this database.
                </div>
            `;
            return;
        }

        tables.forEach(table => {
            const tableCard = this.createTableCard(table);
            container.appendChild(tableCard);
        });

        this.updatePreview();
    }

    createTableCard(table) {
        const card = document.createElement('div');
        card.className = 'card mb-3';

        const tableName = table.name || table.table_name || 'unknown';
        const columns = table.columns || [];
        const hasColumns = columns.length > 0;
        const hasError = table.error;

        card.innerHTML = `
        <div class="card-header">
            <div class="form-check">
                <input class="form-check-input table-checkbox" type="checkbox" 
                       value="${tableName}" id="table-${tableName}"
                       ${hasError ? 'disabled' : ''}>
                <label class="form-check-label fw-bold" for="table-${tableName}">
                    ${tableName}
                    ${hasError ? '<span class="badge bg-danger ms-2">Error</span>' : ''}
                    ${!hasColumns && !hasError ? '<span class="badge bg-secondary ms-2">Click to load columns</span>' : ''}
                </label>
            </div>
        </div>
        <div class="card-body">
            <div class="table-columns" id="columns-${tableName}" style="display: none;">
                ${hasError ?
                `<div class="alert alert-warning py-2">
                        <small>Error loading columns: ${table.error}</small>
                    </div>` :
                hasColumns ?
                    columns.map(col => {
                        const colName = col.name || 'unknown';
                        const colType = col.type || 'unknown';
                        return `
                                <div class="form-check">
                                    <input class="form-check-input column-checkbox" type="checkbox" 
                                           value="${colName}" id="col-${tableName}-${colName}"
                                           data-table="${tableName}">
                                    <label class="form-check-label" for="col-${tableName}-${colName}">
                                        ${colName} <small class="text-muted">(${colType})</small>
                                        ${col.nullable ? '<span class="badge bg-secondary ms-1">nullable</span>' : ''}
                                    </label>
                                </div>
                            `;
                    }).join('')
                    :
                    '<div class="text-muted"><small>Click the table to load columns</small></div>'
            }
            </div>
        </div>
    `;

        if (!hasError) {
            const tableCheckbox = card.querySelector('.table-checkbox');
            tableCheckbox.addEventListener('change', (e) => {
                this.onTableSelect(tableName, e.target.checked);
            });

            if (hasColumns) {
                const columnCheckboxes = card.querySelectorAll('.column-checkbox');
                columnCheckboxes.forEach(checkbox => {
                    checkbox.addEventListener('change', (e) => {
                        this.onColumnSelect(tableName, e.target.value, e.target.checked);
                    });
                });
            }
        }

        return card;
    }

    async onTableSelect(tableName, isSelected) {
        const columnsDiv = document.getElementById(`columns-${tableName}`);
        const tableCheckbox = document.getElementById(`table-${tableName}`);

        if (isSelected) {
            this.selectedTables.add(tableName);
            columnsDiv.style.display = 'block';

            const hasColumns = columnsDiv.querySelector('.column-checkbox');
            const hasError = columnsDiv.querySelector('.alert-warning');

            if (!hasColumns && !hasError) {
                await this.loadTableColumns(tableName, columnsDiv, tableCheckbox);
            }
        } else {
            this.selectedTables.delete(tableName);
            delete this.selectedColumns[tableName];
            columnsDiv.style.display = 'none';

            const columnCheckboxes = columnsDiv.querySelectorAll('.column-checkbox');
            columnCheckboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
        }

        this.updateGenerateSchemaButton();
        this.updatePreview();
        this.updateCreateAgentButton();
    }

    async loadTableColumns(tableName, columnsDiv, tableCheckbox) {
        try {
            columnsDiv.innerHTML = '<div class="text-center"><div class="spinner-border spinner-border-sm" role="status"></div> Loading columns...</div>';
            tableCheckbox.disabled = true;

            const response = await fetch('/api/bi-agents/schema', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    connection_name: this.currentConnection,
                    tables: [tableName]
                })
            });

            const result = await response.json();
            tableCheckbox.disabled = false;

            if (result.status === 'success') {
                if (result.schema && result.schema.length > 0) {
                    const tableData = result.schema[0];
                    const columns = tableData.columns || [];

                    if (columns.length > 0) {
                        columnsDiv.innerHTML = columns.map(col => {
                            const colName = col.name || 'unknown';
                            const colType = col.type || 'unknown';
                            return `
                            <div class="form-check">
                                <input class="form-check-input column-checkbox" type="checkbox" 
                                       value="${colName}" id="col-${tableName}-${colName}"
                                       data-table="${tableName}">
                                <label class="form-check-label" for="col-${tableName}-${colName}">
                                    ${colName} <small class="text-muted">(${colType})</small>
                                    ${col.nullable ? '<span class="badge bg-secondary ms-1">nullable</span>' : ''}
                                </label>
                            </div>
                        `;
                        }).join('');

                        const columnCheckboxes = columnsDiv.querySelectorAll('.column-checkbox');
                        columnCheckboxes.forEach(checkbox => {
                            checkbox.addEventListener('change', (e) => {
                                this.onColumnSelect(tableName, e.target.value, e.target.checked);
                            });
                        });
                    } else {
                        columnsDiv.innerHTML = '<div class="text-muted"><small>No columns found</small></div>';
                    }
                } else {
                    columnsDiv.innerHTML = '<div class="text-muted"><small>No table data returned</small></div>';
                }
            } else {
                columnsDiv.innerHTML = `<div class="alert alert-warning py-2">
                    <small>Error loading columns: ${result.message || 'Unknown error'}</small>
                </div>`;
            }
        } catch (error) {
            tableCheckbox.disabled = false;
            columnsDiv.innerHTML = `<div class="alert alert-warning py-2">
                <small>Error loading columns: ${error.message}</small>
            </div>`;
        }
    }

    onColumnSelect(tableName, columnName, isSelected) {
        if (!this.selectedColumns[tableName]) {
            this.selectedColumns[tableName] = new Set();
        }

        if (isSelected) {
            this.selectedColumns[tableName].add(columnName);
        } else {
            this.selectedColumns[tableName].delete(columnName);
            if (this.selectedColumns[tableName].size === 0) {
                delete this.selectedColumns[tableName];
            }
        }

        this.updateGenerateSchemaButton();
        this.updatePreview();
        this.updateCreateAgentButton();
    }

    updateGenerateSchemaButton() {
        const button = document.getElementById('generateSchemaBtn');
        const hasTables = this.selectedTables.size > 0;
        const hasColumns = Object.keys(this.selectedColumns).length > 0;
        button.disabled = !(hasTables && hasColumns);
    }

    updateCreateAgentButton() {
        const button = document.getElementById('createAgentBtn');
        if (!button) return;

        const hasName = document.getElementById('agentName').value.trim().length > 0;
        const hasDescription = document.getElementById('agentDescription').value.trim().length > 0;
        const hasConnection = this.currentConnection !== null;
        const hasTables = this.selectedTables.size > 0;

        button.disabled = !(hasName && hasDescription && hasConnection && hasTables);
    }

    updatePreview() {
        const previewBody = document.getElementById('previewBody');
        previewBody.innerHTML = '';

        if (this.selectedTables.size === 0) {
            previewBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted">
                        <small>Select tables and columns to see preview</small>
                    </td>
                </tr>
            `;
            return;
        }

        Array.from(this.selectedTables).forEach(tableName => {
            const columns = this.selectedColumns[tableName] ? Array.from(this.selectedColumns[tableName]) : [];
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><strong>${tableName}</strong></td>
                <td>${columns.length > 0 ? columns.join(', ') : 'No columns selected'}</td>
                <td>${columns.length} columns selected</td>
            `;
            previewBody.appendChild(row);
        });
    }

    // ========== AGENT MANAGEMENT ==========

    async loadBIAgents() {
        try {
            const response = await fetch('/api/bi-agents');
            const agents = await response.json();
            this.renderAgents(agents);
        } catch (error) {
            console.error('Error loading agents:', error);
        }
    }

    renderAgents(agents) {
        const tbody = document.getElementById('agents-tbody');
        if (!tbody) return;

        if (!agents || agents.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center py-4 text-muted">
                        No BI agents found. Create your first agent to get started.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = agents.map(agent => `
            <tr>
                <td><strong>${agent.name}</strong></td>
                <td>${agent.description}</td>
                <td><span class="badge bg-secondary">${agent.database_connection}</span></td>
                <td><small>${agent.selected_tables?.length || 0} tables</small></td>
                <td><small>${new Date(agent.created_at).toLocaleDateString()}</small></td>
                <td class="table-actions">
                    <button class="btn btn-sm btn-primary me-1" onclick="agentManager.openChatWithAgent('${agent.name}', 'bi')" title="Chat with Agent">
                        <i class="fas fa-comments"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="agentManager.deleteAgent('${agent.name}')" title="Delete Agent">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }

    async deleteAgent(agentName) {
        if (!confirm(`Are you sure you want to delete agent "${agentName}"?`)) return;

        try {
            const response = await fetch('/api/bi-agents', {
                method: 'DELETE',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name: agentName })
            });

            const result = await response.json();
            
            if (result.status === 'success') {
                this.showNotification('Agent deleted successfully!', 'success');
                this.loadBIAgents();
            } else {
                this.showNotification('Error deleting agent: ' + result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error deleting agent', 'error');
        }
    }

    // ========== HELPER METHODS ==========

    getAgentConfig(agentId) {
        return {
            selected_tables: [],
            schema_context: {}
        };
    }

    getConnectionName(agentId) {
        return 'your-connection-name';
    }

    getSessionId(agentId) {
        return null;
    }

    showNotification(message, type = 'info') {
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger', 
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 1060; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 5000);
    }

    async generateSchemaContext() {
        if (!this.currentConnection || this.selectedTables.size === 0) {
            this.showNotification('Please select a connection and tables first', 'error');
            return;
        }

        try {
            this.showNotification('AI is analyzing your database schema...', 'info');

            const generateBtn = document.getElementById('generateSchemaBtn');
            const originalText = generateBtn.innerHTML;
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Analyzing...';
            generateBtn.disabled = true;

            const response = await fetch('/api/bi-agents/generate-schema-context', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    connection_name: this.currentConnection,
                    tables: Array.from(this.selectedTables),
                    columns: Object.fromEntries(
                        Object.entries(this.selectedColumns).map(([table, cols]) => [table, Array.from(cols)])
                    )
                })
            });

            const result = await response.json();
            generateBtn.innerHTML = originalText;
            generateBtn.disabled = false;

            if (result.status === 'success') {
                document.getElementById('schemaContext').value = JSON.stringify(result.schema_context, null, 2);
                this.showNotification('AI schema analysis completed!', 'success');
            } else {
                this.showNotification('Error: ' + result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error generating schema context', 'error');
        }
    }

    async createAgent() {
        const agentName = document.getElementById('agentName').value.trim();
        const agentDescription = document.getElementById('agentDescription').value.trim();

        if (!agentName || !agentDescription || !this.currentConnection) {
            this.showNotification('Please fill in all required fields', 'error');
            return;
        }

        if (this.selectedTables.size === 0) {
            this.showNotification('Please select at least one table', 'error');
            return;
        }

        const schemaContextValue = document.getElementById('schemaContext').value.trim();
        let schemaContext = {};

        if (schemaContextValue) {
            try {
                schemaContext = JSON.parse(schemaContextValue);
            } catch (error) {
                this.showNotification('Invalid schema context format', 'error');
                return;
            }
        }

        const agentData = {
            name: agentName,
            description: agentDescription,
            database_connection: this.currentConnection,
            selected_tables: Array.from(this.selectedTables),
            selected_columns: Object.fromEntries(
                Object.entries(this.selectedColumns).map(([table, cols]) => [table, Array.from(cols)])
            ),
            schema_context: schemaContext,
            created_at: new Date().toISOString()
        };

        try {
            const response = await fetch('/api/bi-agents', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(agentData)
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.showNotification('Agent created successfully!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('createAgentModal')).hide();
                setTimeout(() => location.reload(), 1000);
            } else {
                this.showNotification('Error creating agent: ' + result.message, 'error');
            }
        } catch (error) {
            this.showNotification('Error creating agent', 'error');
        }
    }
}

// Global functions
function showCreateAgentModal() {
    if (window.agentManager) window.agentManager.showCreateAgentModal();
}

function openChatWithAgent(agentName) {
    if (window.agentManager) window.agentManager.openChatWithAgent(agentName);
}

function openAgentChat(type, agentId, agentName) {
    if (window.agentManager) window.agentManager.openAgentChat(type, agentId, agentName);
}

function closeAgentChat() {
    if (window.agentManager) window.agentManager.closeAgentChat();
}

function sendMessage(type) {
    if (window.agentManager) window.agentManager.sendSidebarMessage(type);
}

// Initialize
// Create agentManager immediately
if (!window.agentManager) {
    console.log("🏗️ Creating agentManager immediately...");
    window.agentManager = new AgentManager();
}

// Also create it as soon as DOM is ready
document.addEventListener("readystatechange", () => {
    if (!window.agentManager && (document.readyState === "interactive" || document.readyState === "complete")) {
        console.log("🏗️ Creating agentManager on readystatechange...");
        window.agentManager = new AgentManager();
    }
});




// Helper function to render chat HTML inline in container
function renderInlineChatPanel(title, welcomeMessage) {
    const container = document.getElementById('chatPanelContainer');
    container.innerHTML = `
        <div class="card" style="width:100%; min-height:400px;">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">${title}</h5>
                <button class="btn btn-outline-secondary btn-sm" onclick="closeAgentChat()">Close</button>
            </div>
            <div class="card-body" style="max-height:60vh; overflow-y:auto; display:flex; flex-direction:column;">
                <div class="chat-container flex-grow-1 mb-2" 
                    style="min-height:250px; max-height:50vh; overflow-y:auto; border:1px solid #dee2e6; border-radius:8px; padding:1rem; background:white;">
                    <div id="chatMessages">
                        <div class="message">
                            <div class="message-content">
                                <div class="welcome-message">
                                    <strong>🤖 Assistant</strong>
                                    <p class="mb-0">${welcomeMessage}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="input-group mt-2">
                    <button class="btn btn-outline-secondary" type="button" id="speechBtn">
                        <i class="fas fa-microphone"></i>
                    </button>
                    <input type="text" class="form-control" id="chatInput" placeholder="Ask a question about your data...">
                    <button class="btn btn-primary" id="sendChatMessageBtn">
                        <i class="fas fa-paper-plane"></i>
                    </button>
                </div>
                <small id="speechTranscript" class="text-muted mt-1"></small>
            </div>
            <div class="card-footer d-flex align-items-center">
                <button class="btn btn-outline-danger btn-sm me-2" id="clearChatBtn">
                    <i class="fas fa-trash"></i> Clear Chat
                </button>
            </div>
        </div>
    `;
    container.style.display = 'block';

    // Bind event listeners for new buttons inside chat panel if needed
    document.getElementById('sendChatMessageBtn').onclick = () => {
        // your send message logic here
    };
    document.getElementById('clearChatBtn').onclick = () => {
        // your clear chat logic here
    };
}

// Global function to close the inline chat panel
function closeAgentChat() {
    const container = document.getElementById('chatPanelContainer');
    container.innerHTML = '';
    container.style.display = 'none';
}