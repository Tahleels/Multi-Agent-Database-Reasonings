# app.py - CLEANED VERSION
from flask import Flask, render_template, jsonify, request
from database_manager import db_manager
from agent_manager import agent_manager
from nlq_engine import NLQEngine
import os
import time
from dotenv import load_dotenv
from dashboard_generator import generate_dashboard_config
from reportgenerator import generate_report_config, get_report_data_with_filters
from infographicgenerator import InfographicGenerator
import pandas as pd

load_dotenv()

app = Flask(__name__)

# ========== SINGLE ENGINE INITIALIZATION ==========
# Global engine instance - initialized ONCE at module level
nlq_engine = NLQEngine(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    database_manager=db_manager
)

print("🚀 NLQ Engine initialized with caching on startup")

# ========== ROUTES ==========
@app.route('/')
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/bi-agents')
def bi_agents():
    return render_template('bi_agents.html')

@app.route('/reasoning-agents')
def reasoning_agents():
    return render_template('reasoning_agents.html')

@app.route('/database-connections')
def database_connections():
    connections = db_manager.load_connections()
    return render_template('database_connections.html', connections=connections)

@app.route('/knowledge-base')
def knowledge_base():
    return render_template('knowledge_base.html')

# API routes
@app.route('/api/chat-agents', methods=['GET', 'POST'])
def chat_agents():
    if request.method == 'GET':
        return jsonify([])
    else:
        data = request.get_json()
        return jsonify({"status": "success", "agent_id": 1})

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    return jsonify({"response": "This is a placeholder response"})

@app.route('/api/connections', methods=['GET', 'POST', 'DELETE'])
def connections():
    if request.method == 'GET':
        connections_list = db_manager.load_connections()
        return jsonify(connections_list)
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            required_fields = ['name', 'type', 'server', 'port', 'username', 'password']
            for field in required_fields:
                if field not in data:
                    return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
            
            success, message = db_manager.add_connection(data)
            if success:
                return jsonify({"status": "success", "message": message})
            else:
                return jsonify({"status": "error", "message": message}), 400
            
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            data = request.get_json()
            connection_name = data.get('name')
            if not connection_name:
                return jsonify({"status": "error", "message": "Connection name is required"}), 400
            
            success, message = db_manager.delete_connection(connection_name)
            if success:
                return jsonify({"status": "success", "message": message})
            else:
                return jsonify({"status": "error", "message": message}), 400
            
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/connections/test', methods=['POST'])
def test_connection():
    try:
        data = request.get_json()
        if 'name' in data:
            success, message = db_manager.test_connection_by_name(data['name'])
        else:
            success, message = db_manager.test_connection(data)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        return jsonify({"success": False, "message": f"Error testing connection: {str(e)}"})

@app.route('/api/documents/upload', methods=['POST'])
def upload_documents():
    return jsonify({"status": "success"})

# BI Agents Management Routes
@app.route('/api/bi-agents', methods=['GET', 'POST', 'DELETE'])
def bi_agents_management():
    if request.method == 'GET':
        agents_list = agent_manager.load_agents()
        return jsonify(agents_list)
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            required_fields = ['name', 'description', 'database_connection']
            for field in required_fields:
                if field not in data:
                    return jsonify({"status": "error", "message": f"Missing required field: {field}"}), 400
            
            success, message = agent_manager.create_agent(data)
            if success:
                return jsonify({"status": "success", "message": message})
            else:
                return jsonify({"status": "error", "message": message}), 400
            
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            data = request.get_json()
            agent_name = data.get('name')
            if not agent_name:
                return jsonify({"status": "error", "message": "Agent name is required"}), 400
            
            success, message = agent_manager.delete_agent(agent_name)
            if success:
                return jsonify({"status": "success", "message": message})
            else:
                return jsonify({"status": "error", "message": message}), 400
            
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/bi-agents/schema', methods=['POST'])
def get_database_schema():
    try:
        data = request.get_json()
        connection_name = data.get('connection_name')
        selected_tables = data.get('tables', [])
        
        print(f"🔧 Schema request for connection: {connection_name}")
        
        if not connection_name:
            return jsonify({"status": "error", "message": "Connection name is required"}), 400
        
        schema_info, error = agent_manager.get_database_schema(connection_name, selected_tables)
        if error:
            print(f"❌ Schema error: {error}")
            return jsonify({"status": "error", "message": error}), 400
        
        return jsonify({"status": "success", "schema": schema_info})
        
    except Exception as e:
        print(f"❌ Unexpected error in schema endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500

@app.route('/api/bi-agents/generate-schema-context', methods=['POST'])
def generate_schema_context():
    try:
        data = request.get_json()
        connection_name = data.get('connection_name')
        selected_tables = data.get('tables', [])
        selected_columns = data.get('columns', {})
        
        print(f"🔧 Generate Schema Context - Connection: {connection_name}")
        print(f"🔧 Tables: {selected_tables}")
        print(f"🔧 Columns: {selected_columns}")
        
        if not connection_name or not selected_tables:
            return jsonify({"status": "error", "message": "Connection name and tables are required"}), 400
        
        schema_context, error = agent_manager.generate_schema_context(
            connection_name, selected_tables, selected_columns
        )
        
        if error:
            print(f"❌ Error generating schema context: {error}")
            return jsonify({"status": "error", "message": error}), 400
        
        print(f"✅ Successfully generated schema context")
        return jsonify({"status": "success", "schema_context": schema_context})
        
    except Exception as e:
        print(f"❌ Unexpected error in generate-schema-context endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500

@app.route('/api/bi-agents/tables', methods=['POST'])
def get_database_tables():
    try:
        data = request.get_json()  # ADDED: You were missing this line
        connection_name = data.get('connection_name')
        
        print(f"🔧 Table list request for: {connection_name}")
        
        if not connection_name:
            return jsonify({"status": "error", "message": "Connection name is required"}), 400
        
        tables, error = agent_manager.get_database_tables(connection_name)
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        return jsonify({"status": "success", "tables": tables})
        
    except Exception as e:
        print(f"❌ Error in tables endpoint: {e}")
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

@app.route('/api/bi-agents/table-columns', methods=['POST'])
def get_table_columns():
    try:
        data = request.get_json()
        connection_name = data.get('connection_name')
        table_names = data.get('table_names', [])
        
        print(f"🔧 Column request for {len(table_names)} tables")
        
        if not connection_name:
            return jsonify({"status": "error", "message": "Connection name is required"}), 400
        
        if not table_names:
            return jsonify({"status": "success", "tables": []})
        
        table_details, error = agent_manager.get_table_columns(connection_name, table_names)
        if error:
            return jsonify({"status": "error", "message": error}), 400
        
        return jsonify({"status": "success", "tables": table_details})
        
    except Exception as e:
        print(f"❌ Error in columns endpoint: {e}")
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

# ========== CHAT & SESSION ENDPOINTS ==========
@app.route('/api/bi-agents/chat', methods=['POST'])
def agent_chat():
    try:
        data = request.get_json()
        agent_name = data.get('agent_name')
        question = data.get('question')
        session_id = data.get('session_id')
        
        print(f"🚀 FAST Chat: {agent_name} - {question}")
        
        if not agent_name or not question:
            return jsonify({"status": "error", "message": "Agent name and question are required"}), 400
        
        agent_config = agent_manager.get_agent(agent_name)
        if not agent_config:
            return jsonify({"status": "error", "message": "Agent not found"}), 404
        
        # Use the global cached engine
        result = nlq_engine.process_question(
            question=question,
            agent_config=agent_config,
            connection_name=agent_config['database_connection'],
            session_id=session_id
        )
        
        # FIX: Return the result directly, not nested
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "response": f"Chat error: {str(e)}"
        }), 500

@app.route('/api/bi-agents/sessions/<session_id>', methods=['GET', 'DELETE'])
def manage_session(session_id):
    if request.method == 'GET':
        session_info = nlq_engine.session_manager.get_session(session_id)
        if session_info:
            formatted_info = {
                "session_id": session_id,
                "agent_name": session_info['agent_config']['name'],
                "message_count": session_info['message_count'],
                "chat_history": session_info['chat_history'],
                "created_at": session_info['created_at'],
                "last_activity": session_info['last_activity']
            }
            return jsonify({"status": "success", "session": formatted_info})
        else:
            return jsonify({"status": "error", "message": "Session not found"}), 404
    
    elif request.method == 'DELETE':
        if nlq_engine.session_manager.delete_session(session_id):
            return jsonify({"status": "success", "message": "Session deleted successfully"})
        else:
            return jsonify({"status": "error", "message": "Session not found"}), 404

@app.route('/api/bi-agents/sessions', methods=['GET'])
def list_sessions():
    active_sessions = nlq_engine.session_manager.get_active_sessions()
    sessions_info = []
    
    for session_id in active_sessions:
        session = nlq_engine.session_manager.get_session(session_id)
        if session:
            session_info = {
                "session_id": session_id,
                "agent_name": session['agent_config']['name'],
                "message_count": session['message_count'],
                "created_at": session['created_at'],
                "last_activity": session['last_activity']
            }
            sessions_info.append(session_info)
    
    return jsonify({"status": "success", "sessions": sessions_info})

@app.route('/api/system/stats', methods=['GET'])
def system_stats():
    """Get system statistics including cache performance"""
    session_stats = nlq_engine.session_manager.get_session_stats()
    cache_stats = {
        "cached_chains": len(nlq_engine.chain_cache),
        "cached_databases": len(nlq_engine.db_cache)
    }
    
    return jsonify({
        "status": "success",
        "session_stats": session_stats,
        "cache_stats": cache_stats
    })

@app.route('/api/bi-agents/generate-dashboard', methods=['POST'])
def generate_dashboard():
    try:
        data = request.get_json()
        rows = data.get('rows')

        df = pd.DataFrame(rows)

        config = generate_dashboard_config(df)
        if config is None:
            return jsonify({"status": "error", "message": "Failed to generate dashboard JSON"}), 400

        return jsonify({
            "status": "success",
            "dashboard_config": config,
            "raw_data": df.to_dict('records')
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/bi-agents/generate-report', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        rows = data.get('rows')

        df = pd.DataFrame(rows)

        # Build report configuration
        report_config = generate_report_config(df)

        # Full row data (used by report UI)
        raw_data = df.to_dict('records')

        return jsonify({
            "success": True,                 # required by reports.js
            "report_config": report_config,  # LLM-generated layout
            "raw_data": raw_data            # REQUIRED for table rendering
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

    
@app.route('/api/bi-agents/generate-infographic', methods=['POST'])
def generate_infographic():
    try:
        data = request.get_json()
        summary = data.get('summary')
        rows = data.get('rows')

        if not summary or not rows:
            return jsonify({
                "status": "error",
                "message": "Missing summary or rows data"
            }), 400

        gen = InfographicGenerator()
        layout = gen.generate_infographic_layout(summary, rows)

        if layout is None:
            return jsonify({
                "status": "error",
                "message": "Infographic generation failed"
            }), 400

        return jsonify({
            "status": "success",
            "infographic": layout
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/preview/dashboard')
def preview_dashboard():
    return render_template('dashboardlayout.html')

@app.route('/preview/report')
def preview_report():
    return render_template('reportlayout.html')

@app.route('/preview/infographic')
def preview_infographic():
    return render_template('infographiclayout.html')



if __name__ == '__main__':
    print("✅ Starting Flask application...")
    # app.run(debug=True)
    app.run(host="0.0.0.0", port=5000)