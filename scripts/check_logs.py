#!/usr/bin/env python3
"""
Script to check API request logs in the database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import get_settings
from app.models import ApiRequestLog
from datetime import datetime, timedelta

def check_logs():
    """Check and display recent API request logs"""
    
    settings = get_settings()
    
    # Create database connection
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD.get_secret_value()}@"
        f"{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/"
        f"{settings.POSTGRES_DB}"
    )
    
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    print("📊 API Request Logs Summary")
    print("=" * 60)
    
    with SessionLocal() as db:
        # Total logs count
        total_logs = db.query(ApiRequestLog).count()
        print(f"📈 Total logged requests: {total_logs}")
        
        if total_logs == 0:
            print("❌ No logs found. Make sure the server is running and receiving requests.")
            return
        
        # Recent logs (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_logs = db.query(ApiRequestLog).filter(
            ApiRequestLog.timestamp >= yesterday
        ).count()
        print(f"🕐 Requests in last 24 hours: {recent_logs}")
        
        # Logs by event type
        print("\n📋 Requests by Event Type:")
        event_types = db.execute(text("""
            SELECT event_type, COUNT(*) as count 
            FROM api_request_logs 
            GROUP BY event_type 
            ORDER BY count DESC
        """)).fetchall()
        
        for event_type, count in event_types:
            print(f"   {event_type}: {count}")
        
        # Recent requests
        print("\n🕒 Recent Requests (Last 10):")
        recent_requests = db.query(ApiRequestLog).order_by(
            ApiRequestLog.timestamp.desc()
        ).limit(10).all()
        
        for log in recent_requests:
            timestamp = log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            response_time = f"{log.response_time_ms:.1f}ms" if log.response_time_ms else "N/A"
            print(f"   {timestamp} | {log.method:4} {log.path:30} | {log.status_code} | {response_time} | {log.event_type}")
        
        # Generate endpoint stats
        generate_logs = db.query(ApiRequestLog).filter(
            ApiRequestLog.event_type == 'rag_generate'
        ).all()
        
        if generate_logs:
            print(f"\n🤖 Generate Endpoint Statistics:")
            print(f"   Total generate requests: {len(generate_logs)}")
            
            avg_response_time = sum(log.response_time_ms or 0 for log in generate_logs) / len(generate_logs)
            print(f"   Average response time: {avg_response_time:.1f}ms")
            
            successful = len([log for log in generate_logs if log.status_code == 200])
            success_rate = (successful / len(generate_logs)) * 100
            print(f"   Success rate: {success_rate:.1f}%")
            
            # Recent generate queries
            print("\n🔍 Recent Generate Queries:")
            for log in generate_logs[-5:]:
                query = (log.rag_query or '')[:80] + "..." if len(log.rag_query or '') > 80 else log.rag_query
                timestamp = log.timestamp.strftime("%H:%M:%S")
                print(f"   {timestamp}: {query}")
        
        # Error summary
        error_logs = db.query(ApiRequestLog).filter(
            ApiRequestLog.status_code >= 400
        ).count()
        
        if error_logs > 0:
            print(f"\n⚠️  Error Summary:")
            print(f"   Total errors: {error_logs}")
            
            error_breakdown = db.execute(text("""
                SELECT status_code, COUNT(*) as count 
                FROM api_request_logs 
                WHERE status_code >= 400
                GROUP BY status_code 
                ORDER BY count DESC
            """)).fetchall()
            
            for status_code, count in error_breakdown:
                print(f"   HTTP {status_code}: {count}")

if __name__ == "__main__":
    try:
        check_logs()
    except Exception as e:
        print(f"❌ Error checking logs: {e}")
        print("Make sure the database is running and accessible.")
