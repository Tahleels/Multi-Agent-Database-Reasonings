# nlq_engine.py - MODERN PROFESSIONAL VERSION WITH STRUCTURED OUTPUT
import os
import time
import uuid
from typing import Dict, List, Optional, Any
from collections import OrderedDict
from urllib.parse import quote_plus
from dataclasses import dataclass, asdict
from datetime import datetime
import json

import pyodbc
from sqlalchemy import create_engine

# Modern LangChain imports
try:
    from langchain_community.utilities import SQLDatabase
    from langchain_openai import ChatOpenAI
    from langchain.chains import create_sql_query_chain
    HAS_SQL_CHAIN = True
    print("✅ SQL chain imports available")
except ImportError as e:
    print(f"❌ SQL chain imports failed: {e}")
    HAS_SQL_CHAIN = False


# ============================================================================
# DATA MODELS - Professional structured responses
# ============================================================================

@dataclass
class ColumnMetadata:
    """Metadata about a column"""
    name: str
    type: str
    is_numeric: bool = False
    is_date: bool = False
    has_nulls: bool = False
    unique_count: Optional[int] = None
    sample_values: Optional[List[Any]] = None


@dataclass
class QueryInsight:
    """Individual insight about the data"""
    type: str  # 'info', 'warning', 'success', 'metric'
    icon: str  # emoji or icon name
    message: str
    value: Optional[Any] = None


@dataclass
class NLQResponse:
    """Structured response object - this is what gets returned"""
    
    # Core data
    success: bool
    question: str
    sql_query: str
    
    # Results
    data: List[Dict[str, Any]]
    columns: List[str]
    row_count: int
    
    # Metadata
    column_metadata: List[ColumnMetadata]
    insights: List[QueryInsight]
    
    # Execution info
    execution_time_ms: float
    cached: bool = False
    session_id: Optional[str] = None
    
    # Error handling
    error: Optional[str] = None
    error_type: Optional[str] = None
    suggestions: Optional[List[str]] = None
    
    # Timestamps
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'question': self.question,
            'sql_query': self.sql_query,
            'data': self.data,
            'columns': self.columns,
            'row_count': self.row_count,
            'column_metadata': [asdict(cm) for cm in self.column_metadata],
            'insights': [asdict(i) for i in self.insights],
            'execution_time_ms': self.execution_time_ms,
            'cached': self.cached,
            'session_id': self.session_id,
            'error': self.error,
            'error_type': self.error_type,
            'suggestions': self.suggestions,
            'timestamp': self.timestamp
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2, default=str)


# ============================================================================
# RESPONSE BUILDER - Generates structured responses
# ============================================================================

class ResponseBuilder:
    """Build structured responses instead of formatted text"""
    
    @staticmethod
    def build_success_response(
        question: str,
        sql_query: str,
        results: List[Dict],
        columns: List[str],
        execution_time: float,
        session_id: str = None,
        cached: bool = False,
        llm = None  # Add LLM parameter
    ) -> NLQResponse:
        """Build a successful query response"""
        
        # Analyze data to generate metadata and insights
        column_metadata = ResponseBuilder._analyze_columns(results, columns)
        insights = ResponseBuilder._generate_insights(results, columns, column_metadata, question, llm)  # Pass LLM here
        
        return NLQResponse(
            success=True,
            question=question,
            sql_query=sql_query,
            data=results,
            columns=columns,
            row_count=len(results),
            column_metadata=column_metadata,
            insights=insights,
            execution_time_ms=execution_time * 1000,
            cached=cached,
            session_id=session_id,
            error=None,
            error_type=None,
            suggestions=None
        )
    
    @staticmethod
    def build_error_response(
        question: str,
        sql_query: str,
        error: str,
        error_type: str = "execution_error",
        execution_time: float = 0,
        session_id: str = None
    ) -> NLQResponse:
        """Build an error response"""
        
        suggestions = ResponseBuilder._generate_error_suggestions(error, error_type)
        
        return NLQResponse(
            success=False,
            question=question,
            sql_query=sql_query,
            data=[],
            columns=[],
            row_count=0,
            column_metadata=[],
            insights=[],
            execution_time_ms=execution_time * 1000,
            cached=False,
            session_id=session_id,
            error=error,
            error_type=error_type,
            suggestions=suggestions
        )
    
    @staticmethod
    def build_no_results_response(
        question: str,
        sql_query: str,
        execution_time: float,
        session_id: str = None,
        cached: bool = False
    ) -> NLQResponse:
        """Build a response when query returns no results"""
        
        insights = [
            QueryInsight(
                type='info',
                icon='🔍',
                message='Query executed successfully but returned no matching records'
            ),
            QueryInsight(
                type='info',
                icon='💡',
                message='Try rephrasing your question or checking if the data exists'
            )
        ]
        
        return NLQResponse(
            success=True,
            question=question,
            sql_query=sql_query,
            data=[],
            columns=[],
            row_count=0,
            column_metadata=[],
            insights=insights,
            execution_time_ms=execution_time * 1000,
            cached=cached,
            session_id=session_id,
            error=None
        )
    
    @staticmethod
    def _analyze_columns(results: List[Dict], columns: List[str]) -> List[ColumnMetadata]:
        """Analyze columns to generate metadata"""
        metadata = []
        
        if not results:
            return [ColumnMetadata(name=col, type='unknown') for col in columns]
        
        for col in columns:
            # Get sample values (non-null)
            values = [row.get(col) for row in results if row.get(col) is not None]
            
            # Determine type
            col_type = type(values[0]).__name__ if values else 'unknown'
            is_numeric = any(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values) if values else False
            is_date = any(keyword in col.lower() for keyword in ['date', 'time', 'created', 'updated', 'modified'])
            
            # Check for nulls
            has_nulls = any(row.get(col) is None for row in results)
            
            # Unique count
            unique_count = len(set(str(v) for v in values)) if values else 0
            
            # Sample values (first 3 unique)
            sample_values = list(set(values))[:3] if values else []
            
            metadata.append(ColumnMetadata(
                name=col,
                type=col_type,
                is_numeric=is_numeric,
                is_date=is_date,
                has_nulls=has_nulls,
                unique_count=unique_count,
                sample_values=sample_values
            ))
        
        return metadata
    
    # Add to ResponseBuilder class in nlq_engine.py

    @staticmethod
    def _detect_query_intent(question: str, columns: List[str], llm) -> str:
        """Use LLM to detect query intent dynamically"""
        try:
            prompt = f"""
            Analyze this database query and classify its primary intent:

            USER QUESTION: "{question}"
            RETURNED COLUMNS: {columns}

            Classify as ONE of these:
            - "analytical": Comparing, analyzing trends, performance, growth, differences, summaries
            - "exploratory": Looking for specific records, filtering, searching, listing data
            - "explanatory": Asking why, causes, reasons, explanations behind data patterns
            - "operational": Basic data retrieval, details, specific information requests

            Respond with ONLY the classification word. No explanations.
            """

            response = llm.invoke(prompt)
            intent = response.content.strip().lower()
            
            # Validate response
            valid_intents = ["analytical", "exploratory", "explanatory", "operational"]
            detected_intent = intent if intent in valid_intents else "exploratory"
            print(f"🔍 Detected query intent: {detected_intent}")
            return detected_intent
            
        except Exception as e:
            print(f"⚠️ Intent detection failed: {e}")
            return "exploratory"  # Default fallback

    @staticmethod
    def _get_llm_summary(prompt: str, llm) -> str:
        """Get concise summary from LLM"""
        try:
            response = llm.invoke(prompt)
            return response.content.strip()
        except Exception as e:
            print(f"⚠️ LLM summary failed: {e}")
            return "Analysis available in the data above."

    @staticmethod
    def _generate_analytical_insights(results: List[Dict], columns: List[str], question: str, llm) -> List[QueryInsight]:
        """Generate executive summary for analytical queries"""
        try:
            prompt = f"""
            Analyze this analytical data and create a concise executive summary.

            USER QUESTION: "{question}"
            DATA COLUMNS: {columns}
            SAMPLE DATA: {results[:5]}

            Focus on:
            - Key trends and patterns
            - Significant changes or differences
            - Top performers or outliers
            - Business implications

            FORMAT RULES:
            - Use ONLY bullet points starting with •
            - NO markdown formatting (no **bold**, no headers)
            - Each bullet should be 1 short sentence
            - Maximum 4 bullet points
            - Be specific and data-driven

            Example format:
            • Revenue increased 15% compared to last quarter
            • Product A was top performer with 25% growth
            • Q4 showed strongest seasonal performance
            • Customer retention rate improved to 85%

            Now create the summary:
            """

            summary = ResponseBuilder._get_llm_summary(prompt, llm)
            return [QueryInsight("success", "📈", f"Analysis Summary:\n{summary}")]
        except Exception as e:
            print(f"⚠️ Analytical insights failed: {e}")
            return []

    @staticmethod
    def _generate_explanatory_insights(results: List[Dict], columns: List[str], question: str, llm) -> List[QueryInsight]:
        """Generate explanatory insights for 'why' questions"""
        try:
            prompt = f"""
            Explain potential reasons and context for these results:

            USER QUESTION: "{question}"
            DATA: {results[:10]}
            COLUMNS: {columns}

            Provide 2-3 possible explanations considering:
            - Data patterns visible
            - Common business scenarios
            - Potential external factors

            FORMAT RULES:
            - Use ONLY bullet points starting with •
            - NO markdown formatting
            - Each bullet should be 1 short sentence
            - Maximum 3 bullet points
            - Be analytical but concise

            Example format:
            • Seasonal patterns typically affect performance during this period
            • Competitor promotions may have impacted market share
            • Supply chain disruptions could explain inventory issues

            Now provide explanations:
            """

            explanation = ResponseBuilder._get_llm_summary(prompt, llm)
            return [QueryInsight("info", "💡", f"Potential Explanations:\n{explanation}")]
        except Exception as e:
            print(f"⚠️ Explanatory insights failed: {e}")
            return []

    @staticmethod
    def _generate_explanatory_insights(results: List[Dict], columns: List[str], question: str, llm) -> List[QueryInsight]:
        """Generate explanatory insights for 'why' questions"""
        try:
            prompt = f"""
            Explain potential reasons and context for these results:

            USER QUESTION: "{question}"
            DATA: {results[:10]}
            COLUMNS: {columns}

            Provide 2-3 possible explanations considering:
            - Data patterns visible
            - Common business scenarios
            - Potential external factors

            FORMAT RULES:
            - Use ONLY bullet points starting with •
            - NO markdown formatting
            - Each bullet should be 1 short sentence
            - Maximum 3 bullet points
            - Be analytical but concise

            Example format:
            • Seasonal patterns typically affect performance during this period
            • Competitor promotions may have impacted market share
            • Supply chain disruptions could explain inventory issues

            Now provide explanations:
            """

            explanation = ResponseBuilder._get_llm_summary(prompt, llm)
            return [QueryInsight("info", "💡", f"Potential Explanations:\n{explanation}")]
        except Exception as e:
            print(f"⚠️ Explanatory insights failed: {e}")
            return []

    @staticmethod
    def _generate_operational_insights(results: List[Dict], columns: List[str], metadata: List[ColumnMetadata]) -> List[QueryInsight]:
        """Generate basic insights for operational queries"""
        insights = []
        
        # Basic dataset info
        if len(results) > 0:
            insights.append(QueryInsight(
                "info", "📊", 
                f"Dataset: {len(results)} records, {len(columns)} fields"
            ))
        
        # Data characteristics
        numeric_cols = [m for m in metadata if m.is_numeric]
        date_cols = [m for m in metadata if m.is_date]
        
        if numeric_cols:
            insights.append(QueryInsight(
                "info", "🔢", 
                f"Contains {len(numeric_cols)} numeric fields"
            ))
        
        if date_cols:
            insights.append(QueryInsight(
                "info", "📅", 
                f"Contains {len(date_cols)} date/time fields"
            ))
        
        return insights
    
    @staticmethod
    def _generate_insights(
        results: List[Dict], 
        columns: List[str], 
        metadata: List[ColumnMetadata],
        question: str,
        llm = None  # Add LLM parameter
    ) -> List[QueryInsight]:
        """Generate dynamic insights based on query intent"""
        
        # If no LLM available, fall back to basic insights
        if not llm:
            print("⚠️ LLM not available for insights, using basic insights")
            return ResponseBuilder._generate_operational_insights(results, columns, metadata)
        
        # Detect intent
        intent = ResponseBuilder._detect_query_intent(question, columns, llm)
        
        # Generate appropriate insights based on intent
        if intent == "analytical":
            return ResponseBuilder._generate_analytical_insights(results, columns, question, llm)
        elif intent == "explanatory":
            return ResponseBuilder._generate_explanatory_insights(results, columns, question, llm)
        elif intent == "operational":
            return ResponseBuilder._generate_operational_insights(results, columns, metadata)
        else:  # exploratory (default)
            return ResponseBuilder._generate_exploratory_insights(results, columns, metadata, llm)
        
    
    @staticmethod
    def _generate_error_suggestions(error: str, error_type: str) -> List[str]:
        """Generate helpful suggestions based on error"""
        suggestions = []
        error_lower = error.lower()
        
        if 'table' in error_lower or 'object' in error_lower:
            suggestions.append('Verify that the table name is correct and exists in the database')
            suggestions.append('Check if you have permissions to access the table')
        
        if 'column' in error_lower:
            suggestions.append('Check if the column name is spelled correctly')
            suggestions.append('Verify that the column exists in the selected table')
        
        if 'syntax' in error_lower:
            suggestions.append('Review the generated SQL query for syntax errors')
            suggestions.append('Try rephrasing your question more clearly')
        
        if 'permission' in error_lower or 'denied' in error_lower:
            suggestions.append('Contact your database administrator for access')
            suggestions.append('Verify your database credentials')
        
        if 'timeout' in error_lower:
            suggestions.append('Try limiting the result set with more specific filters')
            suggestions.append('Consider breaking the query into smaller parts')
        
        # Generic suggestions if no specific match
        if not suggestions:
            suggestions = [
                'Try simplifying your question',
                'Check your database connection',
                'Review the SQL query for potential issues'
            ]
        
        return suggestions


# ============================================================================
# SESSION MANAGER - Handle user sessions
# ============================================================================

class SessionManager:
    def __init__(self, max_sessions=50, max_messages=20, session_timeout=7200):  # 2 hours
        self.sessions = OrderedDict()
        self.max_sessions = max_sessions
        self.max_messages = max_messages
        self.session_timeout = session_timeout
    
    def create_session(self, agent_config, connection_name, chain):
        session_id = str(uuid.uuid4())
        
        self._cleanup_expired_sessions()
        
        # Remove oldest session if at capacity
        if len(self.sessions) >= self.max_sessions:
            oldest_id = next(iter(self.sessions))
            print(f"🧹 Removing oldest session: {oldest_id}")
            del self.sessions[oldest_id]
        
        self.sessions[session_id] = {
            'agent_config': agent_config,
            'connection_name': connection_name,
            'chain': chain,
            'chat_history': [],
            'created_at': time.time(),
            'last_activity': time.time(),
            'message_count': 0
        }
        
        print(f"✅ Created session {session_id}")
        return session_id
    
    def get_session(self, session_id):
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if time.time() - session['last_activity'] > self.session_timeout:
                print(f"🧹 Session expired: {session_id}")
                del self.sessions[session_id]
                return None
            
            session['last_activity'] = time.time()
            self.sessions.move_to_end(session_id)
            return session
        return None
    
    def add_message(self, session_id, role, content):
        session = self.get_session(session_id)
        if session:
            session['chat_history'].append({
                'role': role, 
                'content': content,
                'timestamp': time.time()
            })
            session['message_count'] += 1
            session['last_activity'] = time.time()
            
            if len(session['chat_history']) > self.max_messages:
                session['chat_history'] = session['chat_history'][-self.max_messages:]
    
    def get_active_sessions(self):
        self._cleanup_expired_sessions()
        return list(self.sessions.keys())
    
    def _cleanup_expired_sessions(self):
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if current_time - session['last_activity'] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            print(f"🧹 Cleaning up expired session: {session_id}")
            del self.sessions[session_id]
    
    def delete_session(self, session_id):
        if session_id in self.sessions:
            print(f"🧹 Manually deleting session: {session_id}")
            del self.sessions[session_id]
            return True
        return False
    
    def get_session_stats(self):
        """Get statistics about sessions"""
        self._cleanup_expired_sessions()
        return {
            "total_sessions": len(self.sessions),
            "max_sessions": self.max_sessions,
            "session_timeout": self.session_timeout
        }


# ============================================================================
# MAIN NLQ ENGINE - Core logic
# ============================================================================

class NLQEngine:
    def __init__(self, openai_api_key: str = None, database_manager=None):
        self.openai_api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        self.database_manager = database_manager
        
        # Initialize LLM
        if not self.openai_api_key:
            print("⚠️ WARNING: OpenAI API key not provided. LLM features will not work.")
            self.llm = None
        else:
            try:
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    temperature=0,
                    openai_api_key=self.openai_api_key
                )
                print("✅ LLM initialized successfully")
            except ImportError as e:
                print(f"❌ Failed to import ChatOpenAI: {e}")
                self.llm = None
            except Exception as e:
                print(f"❌ Failed to initialize LLM: {e}")
                self.llm = None
        
        # Enhanced caching
        self.chain_cache = {}
        self.db_cache = {}
        self.session_manager = SessionManager()
        
        print(f"✅ NLQ Engine initialized (LLM: {'available' if self.llm else 'not available'})")
    
    def set_database_manager(self, database_manager):
        """Set database manager after initialization if needed"""
        self.database_manager = database_manager
        print("✅ Database manager set for NLQ Engine")

    def get_or_create_chain(self, agent_config: Dict, connection_name: str):
        """Get cached chain or create new one"""
        cache_key = self._create_cache_key(agent_config, connection_name)
        
        if cache_key in self.chain_cache:
            print(f"✅ Using cached chain for: {cache_key}")
            return self.chain_cache[cache_key], None, True
        
        print(f"🔄 Creating new chain for: {cache_key}")
        chain, error = self._create_sql_chain(agent_config, connection_name)
        
        if chain and not error:
            self.chain_cache[cache_key] = chain
            print(f"✅ Chain cached for future use: {cache_key}")
        
        return chain, error, False

    def _create_cache_key(self, agent_config: Dict, connection_name: str) -> str:
        """Create unique cache key"""
        selected_tables = sorted(agent_config.get('selected_tables', []))
        tables_key = ":".join(selected_tables)
        return f"{connection_name}:{tables_key}"

    def _create_sql_chain(self, agent_config: Dict, connection_name: str):
        """Create SQL chain"""
        try:
            if not self.database_manager:
                return None, "Database manager not available"
            
            connection_config = self.database_manager.get_connection(connection_name)
            if not connection_config:
                return None, f"Connection '{connection_name}' not found"
            
            print(f"🔧 Creating SQL chain for: {connection_config['name']}")
            
            db = self._get_or_create_database(connection_config, agent_config)
            chain = create_sql_query_chain(llm=self.llm, db=db)
            enhanced_chain = self._enhance_chain_with_context(chain, agent_config)
            
            print("✅ SQL query chain created successfully")
            return enhanced_chain, None
            
        except Exception as e:
            print(f"❌ Error creating SQL chain: {e}")
            return None, f"Error creating SQL chain: {str(e)}"

    def _get_or_create_database(self, connection_config: Dict, agent_config: Dict):
        """Get cached database or create new one"""
        db_cache_key = f"{connection_config['name']}:{':'.join(sorted(agent_config.get('selected_tables', [])))}"
        
        if db_cache_key in self.db_cache:
            print(f"✅ Using cached database connection: {db_cache_key}")
            return self.db_cache[db_cache_key]
        
        print(f"🔄 Creating new database connection: {db_cache_key}")
        db = self._create_sql_database(connection_config, agent_config)
        self.db_cache[db_cache_key] = db
        return db

    def _enhance_chain_with_context(self, chain, agent_config: Dict):
        """Enhance the chain with custom context"""
        
        def process_with_context(inputs: Dict):
            try:
                question = inputs.get("question", "")
                enhanced_question = self._enhance_question(question, agent_config)
                sql_query = chain.invoke({"question": enhanced_question})
                sql_query = self._clean_sql_output(sql_query)
                
                # FIX: Clean up SQL query - remove Markdown formatting and SQLQuery: prefix
                if isinstance(sql_query, str):
                    # Remove Markdown code blocks
                    if sql_query.startswith('```sql'):
                        sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
                    elif sql_query.startswith('```'):
                        sql_query = sql_query.replace('```', '').strip()
                    
                    # Remove SQLQuery: prefix if present
                    if sql_query.startswith('SQLQuery:'):
                        sql_query = sql_query.replace('SQLQuery:', '').strip()
                    
                    # Remove any remaining backticks
                    sql_query = sql_query.replace('`', '').strip()
                
                return sql_query
                
            except Exception as e:
                print(f"❌ Error in enhanced chain: {e}")
                raise
        
        return process_with_context

    def _enhance_question(self, question: str, agent_config: Dict) -> str:
        """Enhance the question with custom instructions including agent description"""
        
        schema_context = agent_config.get('schema_context', {})
        tables_info = self._format_tables_for_context(schema_context)
        
        # Get agent description if available
        agent_description = agent_config.get('description', '')
        agent_name = agent_config.get('name', 'BI Agent')
        
        enhanced_prompt = f"""You are a SQL expert for business intelligence. {agent_description}

        DATABASE SCHEMA:
        {tables_info}

        IMPORTANT RULES:
        - Only use tables and columns mentioned above
        - Keep queries efficient and focused
        - DO NOT use TOP unless the user explicitly asks for a limit
        - If the user asks for “all”, “everything”, “full list”, generate a SELECT without TOP
        - Include only necessary columns in SELECT
        - Add WHERE clauses when filtering is needed
        - Use ORDER BY when sorting is requested
        - Return ONLY the SQL query, no explanations

        USER QUESTION: {question}

        SQL QUERY:"""
        return enhanced_prompt

    def _format_tables_for_context(self, schema_context: Dict) -> str:
        """Format table information for context"""
        tables_info = []
        
        for table in schema_context.get('tables', []):
            table_info = f"Table: {table['table_name']}\n"
            if table.get('description'):
                table_info += f"Description: {table['description']}\n"
            
            table_info += "Columns:\n"
            for col in table.get('columns', []):
                col_info = f"  - {col['name']} ({col.get('type', 'unknown')})"
                if col.get('inferred_purpose'):
                    col_info += f" - {col['inferred_purpose']}"
                table_info += col_info + "\n"
            
            tables_info.append(table_info)
        
        return "\n".join(tables_info)
    
    @staticmethod
    def _clean_sql_output(sql_output: str) -> str:
        """
        Clean raw SQL returned by LLM chains.
        Removes Markdown fences, SQLQuery prefix, and stray backticks.
        """
        if not sql_output:
            return ""
        
        import re

        # Remove Markdown code fences like ```sql or ```
        cleaned = re.sub(r"```(?:sql)?", "", sql_output, flags=re.IGNORECASE)
        
        # Remove SQLQuery: prefix
        cleaned = re.sub(r"SQLQuery\s*:", "", cleaned, flags=re.IGNORECASE)
        
        # Remove remaining backticks and trim whitespace
        cleaned = cleaned.replace("`", "").strip()
        
        return cleaned

    def _execute_and_format_response(
        self, 
        sql_query: str, 
        original_question: str, 
        execution_time: float,
        session_id: str = None,
        cached: bool = False
    ) -> NLQResponse:
        """Execute SQL and return STRUCTURED response"""
        try:
            # FIX: Strip SQLQuery wrapper if present
            if isinstance(sql_query, str) and sql_query.startswith('SQLQuery:'):
                sql_query = sql_query.replace('SQLQuery:', '').strip()
            
            print(f"🔧 Generated SQL: {sql_query}")
            
            connection_config = getattr(self, '_last_connection_config', None)
            if not connection_config:
                return ResponseBuilder.build_error_response(
                    question=original_question,
                    sql_query=sql_query,
                    error="Connection configuration not available",
                    error_type="config_error",
                    execution_time=execution_time,
                    session_id=session_id
                )
            
            # Execute SQL
            conn = self.database_manager.get_connection_object(connection_config)
            cursor = conn.cursor()
            cursor.execute(sql_query)
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convert to list of dicts
            results = [dict(zip(columns, row)) for row in rows]
            
            # Build structured response - PASS LLM HERE
            if len(results) == 0:
                return ResponseBuilder.build_no_results_response(
                    question=original_question,
                    sql_query=sql_query,
                    execution_time=execution_time,
                    session_id=session_id,
                    cached=cached
                )
            else:
                return ResponseBuilder.build_success_response(
                    question=original_question,
                    sql_query=sql_query,
                    results=results,
                    columns=columns,
                    execution_time=execution_time,
                    session_id=session_id,
                    cached=cached,
                    llm=self.llm  # Pass the LLM instance
                )
                
        except Exception as e:
            print(f"❌ Error executing SQL: {e}")
            return ResponseBuilder.build_error_response(
                question=original_question,
                sql_query=sql_query,
                error=str(e),
                error_type="execution_error",
                execution_time=execution_time,
                session_id=session_id
            )
        

    def process_question(
    self, 
    question: str, 
    agent_config: Dict, 
    connection_name: str, 
    session_id: str = None
) -> Dict:
        """Main method to process questions - returns dict for API compatibility"""
        start_time = time.time()
        
        try:
            # Handle session
            if session_id:
                session = self.session_manager.get_session(session_id)
                if session:
                    chain = session['chain']
                    cached = True
                    print(f"✅ Using existing session chain: {session_id}")
                else:
                    chain, error, cached = self.get_or_create_chain(agent_config, connection_name)
                    if error:
                        error_response = ResponseBuilder.build_error_response(
                            question=question,
                            sql_query="",
                            error=error,
                            error_type="chain_creation_error",
                            execution_time=time.time() - start_time
                        )
                        return error_response.to_dict()  # Convert to dict
                    session_id = self.session_manager.create_session(agent_config, connection_name, chain)
            else:
                chain, error, cached = self.get_or_create_chain(agent_config, connection_name)
                if error:
                    error_response = ResponseBuilder.build_error_response(
                        question=question,
                        sql_query="",
                        error=error,
                        error_type="chain_creation_error",
                        execution_time=time.time() - start_time
                    )
                    return error_response.to_dict()  # Convert to dict
                session_id = self.session_manager.create_session(agent_config, connection_name, chain)
            
            # Generate SQL query
            sql_query = chain({"question": question})
            
            # Execute and get structured response
            response = self._execute_and_format_response(
                sql_query=sql_query,
                original_question=question,
                execution_time=time.time() - start_time,
                session_id=session_id,
                cached=cached
            )
            
            # Update session history
            if response.success:
                self.session_manager.add_message(session_id, "user", question)
                # Store a simplified message for session history
                if response.row_count > 0:
                    assistant_message = f"Found {response.row_count} records for: {question}"
                else:
                    assistant_message = f"No results found for: {question}"
                self.session_manager.add_message(session_id, "assistant", assistant_message)
            
            print(f"✅ Query processed in {response.execution_time_ms:.0f}ms")
            
            # Convert NLQResponse to dict for API compatibility
            return response.to_dict()
            
        except Exception as e:
            print(f"❌ Error processing question: {e}")
            error_response = ResponseBuilder.build_error_response(
                question=question,
                sql_query="",
                error=str(e),
                error_type="processing_error",
                execution_time=time.time() - start_time
            )
            return error_response.to_dict()  # Convert to dict

    def _create_sql_database(self, connection_config: Dict, agent_config: Dict = None):
        """Create SQLDatabase instance"""
        if connection_config['type'] == 'mssql':
            drivers = pyodbc.drivers()
            driver = 'ODBC Driver 18 for SQL Server'
            
            if driver not in drivers:
                available = [d for d in drivers if 'SQL Server' in d]
                if available:
                    driver = available[0]
            
            server = connection_config['server']
            port = connection_config.get('port', '1433')
            database = connection_config['database']
            username = connection_config['username']
            password = connection_config['password']
            
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={server},{port};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                "TrustServerCertificate=yes;"
                "Encrypt=yes;"
            )
            
            quoted_conn_str = quote_plus(conn_str)
            url = f"mssql+pyodbc:///?odbc_connect={quoted_conn_str}"
        
        engine = create_engine(url)
        
        # Strip schema prefix (TS., dbo., etc.)
        raw_tables = agent_config.get('selected_tables', []) if agent_config else []
        selected_tables = [t.split('.')[-1] for t in raw_tables]

        schema = None
        if '.' in raw_tables[0]:
            schema = raw_tables[0].split('.')[0]
        db = SQLDatabase(
        engine=engine,
        include_tables=selected_tables,
        schema=schema,               # ⭐ ADD THIS
        sample_rows_in_table_info=2,
        max_string_length=100
    )
        # FIX: SQLDatabase MUST load TS schema instead of dbo
        #db = SQLDatabase.from_uri(
        #    url,
        #    include_tables=selected_tables,
        #    sample_rows_in_table_info=2,
        #    max_string_length=100,
        #    schema="TS"
#)

        
        self._last_connection_config = connection_config
        return db

    def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        current_size = len(self.chain_cache)
        if current_size > 50:
            keys_to_remove = list(self.chain_cache.keys())[:10]
            for key in keys_to_remove:
                del self.chain_cache[key]
            print(f"🧹 Cleaned up {len(keys_to_remove)} cache entries")


# ============================================================================
# GLOBAL INSTANCE (optional)
# ============================================================================

_global_nlq_engine = None

def get_global_nlq_engine():
    """Get or create global NLQ engine instance"""
    global _global_nlq_engine
    if _global_nlq_engine is None:
        _global_nlq_engine = NLQEngine(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            database_manager=None
        )
    return _global_nlq_engine