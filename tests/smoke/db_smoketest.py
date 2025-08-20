#!/usr/bin/env python3
"""
Simple smoke test para verificar la conectividad básica de la base de datos
sin intentar crear o modificar tablas.
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def simple_db_test():
    """Test básico de conectividad de base de datos."""
    print("🔥 Edgar Simple Database Smoke Test")
    print("=" * 40)
    
    database_url = os.getenv("PG_DSN")
    if not database_url:
        print("❌ Variable PG_DSN no encontrada en .env")
        return False
    
    print(f"🔍 Conectando a la base de datos...")
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Test básico de conectividad
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                print("✅ Conexión exitosa")
            else:
                print("❌ Error en test de conexión")
                return False
            
            # Verificar que existe alguna tabla de filings
            tables_check = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE '%filing%'
                LIMIT 5
            """))
            
            filing_tables = tables_check.fetchall()
            if filing_tables:
                print("✅ Tablas de filing encontradas:")
                for table in filing_tables:
                    print(f"   📄 {table[0]}")
            else:
                print("⚠️ No se encontraron tablas de filing")
            
            # Test de conteo básico si existe alguna tabla
            if filing_tables:
                try:
                    # Intentar contar registros en la primera tabla encontrada
                    table_name = filing_tables[0][0]
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = count_result.scalar()
                    print(f"✅ Registros en {table_name}: {count}")
                except Exception as e:
                    print(f"⚠️ No se pudo contar registros: {e}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_environment():
    """Verificar variables de entorno necesarias."""
    print("\n🔧 Verificando configuración del entorno...")
    
    required_vars = ["PG_DSN"]
    all_present = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mostrar solo los primeros caracteres por seguridad
            masked_value = value[:20] + "..." if len(value) > 20 else value
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: No encontrada")
            all_present = False
    
    return all_present

def main():
    """Función principal del smoke test."""
    success_count = 0
    total_tests = 2
    
    # Test 1: Variables de entorno
    if test_environment():
        success_count += 1
    
    # Test 2: Conectividad de base de datos
    if simple_db_test():
        success_count += 1
    
    # Resumen final
    print("\n" + "=" * 40)
    print(f"🎯 Resultados: {success_count}/{total_tests} tests pasaron")
    
    if success_count == total_tests:
        print("🎉 Smoke test exitoso - Sistema básico funcionando!")
        return 0
    else:
        print("⚠️ Algunos tests fallaron - Revisar configuración")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
