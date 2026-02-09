# debug_schema.py
from sqlalchemy import create_engine, inspect, text

def debug_schema_fetch():
    try:
        # Your connection details
        server = '192.168.51.10'
        port = '1433'
        database = 'MaxnetSales_and_Marketing'
        username = 'ebio'
        password = '17of1Kr7pOPC'
        driver = 'ODBC Driver 18 for SQL Server'
        
        url = f"mssql+pyodbc://{username}:{password}@{server}:{port}/{database}?driver={driver.replace(' ', '+')}&TrustServerCertificate=yes&timeout=30"
        
        print("1. Creating engine...")
        engine = create_engine(url)
        
        print("2. Testing basic connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT @@VERSION as version"))
            version = result.scalar()
            print(f"   SQL Server version: {version}")
        
        print("3. Creating inspector...")
        inspector = inspect(engine)
        
        print("4. Fetching table names...")
        tables = inspector.get_table_names()
        print(f"   Found {len(tables)} tables")
        
        if tables:
            print("5. Fetching columns for first table...")
            columns = inspector.get_columns(tables[0])
            print(f"   Found {len(columns)} columns in {tables[0]}")
        
        print("✅ Schema fetch completed successfully!")
        
    except Exception as e:
        print(f"❌ Failed at step: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_schema_fetch()