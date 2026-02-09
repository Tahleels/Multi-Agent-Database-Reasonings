// static/js/connections.js - FIXED VERSION

class ConnectionManager {
    constructor() {
        this.modal = null;
        this.isEditMode = false;
        this.currentConnectionName = null;
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        console.log('🔧 Initializing ConnectionManager event listeners...');
        
        // Connection modal events
        document.getElementById('testConnectionBtn')?.addEventListener('click', () => {
            this.testConnection();
        });

        document.getElementById('createConnectionBtn')?.addEventListener('click', () => {
            this.saveConnection();
        });

        // Form field events for dynamic port handling
        document.getElementById('dbType')?.addEventListener('change', (e) => {
            this.updatePortPlaceholder(e.target.value);
        });
    }

    updatePortPlaceholder(dbType) {
        const portInput = document.getElementById('port');
        if (portInput) {
            const defaultPort = this.getDefaultPort(dbType);
            portInput.placeholder = `Default: ${defaultPort}`;
        }
    }

    showCreateConnectionModal() {
        console.log('🔄 Showing create connection modal');
        this.isEditMode = false;
        this.currentConnectionName = null;
        
        // Reset form
        document.getElementById('createConnectionForm').reset();
        document.querySelector('#createConnectionModal .modal-title').textContent = 'Create Database Connection';
        
        // Set default port placeholder
        const dbType = document.getElementById('dbType').value;
        if (dbType) {
            this.updatePortPlaceholder(dbType);
        }
        
        // Show modal
        this.modal = new bootstrap.Modal(document.getElementById('createConnectionModal'));
        this.modal.show();
    }

    showEditConnectionModal(connectionName) {
        this.isEditMode = true;
        this.currentConnectionName = connectionName;
        
        // Fetch connection data and populate form
        fetch('/api/connections')
            .then(response => response.json())
            .then(connections => {
                const connection = connections.find(conn => conn.name === connectionName);
                if (connection) {
                    // Populate form fields
                    document.getElementById('connectionName').value = connection.name;
                    document.getElementById('dbType').value = connection.type;
                    document.getElementById('server').value = connection.server;
                    document.getElementById('port').value = connection.port;
                    document.getElementById('username').value = connection.username;
                    document.getElementById('password').value = ''; // Don't show existing password
                    document.getElementById('dbName').value = connection.database || '';
                    
                    // Update port placeholder
                    this.updatePortPlaceholder(connection.type);
                    
                    // Update modal title
                    document.querySelector('#createConnectionModal .modal-title').textContent = 'Edit Database Connection';
                    
                    // Show modal
                    this.modal = new bootstrap.Modal(document.getElementById('createConnectionModal'));
                    this.modal.show();
                } else {
                    this.showNotification('Connection not found', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showNotification('Error loading connection data', 'error');
            });
    }

    saveConnection() {
        const connectionData = {
            name: document.getElementById('connectionName').value,
            type: document.getElementById('dbType').value,
            server: document.getElementById('server').value,
            port: document.getElementById('port').value || this.getDefaultPort(document.getElementById('dbType').value),
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            database: document.getElementById('dbName').value
        };

        console.log('Saving connection:', { ...connectionData, password: '***' }); // Don't log password

        // Validate required fields
        if (!connectionData.name || !connectionData.type || !connectionData.server || 
            !connectionData.username || !connectionData.password || !connectionData.database) {
            this.showNotification('Please fill in all required fields', 'error');
            return;
        }

        // For edits, we need to handle name changes differently
        if (this.isEditMode && this.currentConnectionName !== connectionData.name) {
            if (!confirm('Changing connection name will create a new connection. Continue?')) {
                return;
            }
        }

        const url = '/api/connections';
        const method = 'POST';

        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(connectionData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                this.showNotification('Connection saved successfully!', 'success');
                this.modal.hide();
                setTimeout(() => {
                    location.reload(); // Reload to show updated connections
                }, 1000);
            } else {
                this.showNotification('Error: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showNotification('Error saving connection: ' + error.message, 'error');
        });
    }

    testConnection() {
        const connectionData = {
            name: document.getElementById('connectionName').value,
            type: document.getElementById('dbType').value,
            server: document.getElementById('server').value,
            port: parseInt(document.getElementById('port').value) || this.getDefaultPort(document.getElementById('dbType').value),
            username: document.getElementById('username').value,
            password: document.getElementById('password').value,
            database: document.getElementById('dbName').value
        };

        console.log('Testing connection:', { ...connectionData, password: '***' }); // Don't log password

        // Validate required fields
        if (!connectionData.name || !connectionData.type || !connectionData.server || 
            !connectionData.username || !connectionData.password || !connectionData.database) {
            this.showNotification('Please fill in all required fields to test connection', 'error');
            return;
        }

        this.showNotification(`Testing connection: ${connectionData.name}...`, 'info');
        
        fetch('/api/connections/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(connectionData)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                this.showNotification(`✓ ${data.message}`, 'success');
            } else {
                this.showNotification(`✗ ${data.message}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            this.showNotification('Error testing connection: ' + error.message, 'error');
        });
    }

    // Add helper method for default ports
    getDefaultPort(dbType) {
        const defaultPorts = {
            'postgresql': 5432,
            'mysql': 3306,
            'mssql': 1433,
            'oracle': 1521,
            'mongodb': 27017
        };
        return defaultPorts[dbType] || 5432;
    }

    deleteConnection(connectionName) {
        if (confirm(`Are you sure you want to delete connection "${connectionName}"?`)) {
            fetch('/api/connections', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: connectionName })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    this.showNotification('Connection deleted successfully!', 'success');
                    setTimeout(() => {
                        location.reload();
                    }, 1000);
                } else {
                    this.showNotification('Error: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                this.showNotification('Error deleting connection', 'error');
            });
        }
    }

    showNotification(message, type = 'info') {
        // Create a simple notification
        const alertClass = type === 'success' ? 'alert-success' : 
                          type === 'error' ? 'alert-danger' : 'alert-info';
        
        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 1060; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize connection manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('🌐 Initializing ConnectionManager...');
    window.connectionManager = new ConnectionManager();
    
    // Global functions for HTML onclick handlers
    window.showCreateConnectionModal = () => window.connectionManager.showCreateConnectionModal();
    window.editConnection = (name) => window.connectionManager.showEditConnectionModal(name);
    window.deleteConnection = (name) => window.connectionManager.deleteConnection(name);
    window.testConnection = () => window.connectionManager.testConnection();
    window.createConnection = () => window.connectionManager.saveConnection();
});