"""
StockPilot - Veritabanı Modülü
SQLite ile arama geçmişi, izleme listesi ve günlük öneri verilerinin kalıcı depolanması.
"""

import sqlite3
import os
import sys
from datetime import datetime, date
from contextlib import contextmanager

# Veritabanı dosya yolu
DB_DIR = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys, '_MEIPASS'):
    # Paketlendiyse, veritabanını exe dosyasının yanına koyalım (kalıcı olması için)
    exe_dir = os.path.dirname(sys.executable)
    DB_PATH = os.path.join(exe_dir, "stockpilot.db")
else:
    # Web deployment: DATA_DIR env varsa kullan, yoksa backend klasörü
    data_dir = os.environ.get('DATA_DIR', os.environ.get('RENDER_DISK_PATH', DB_DIR))
    DB_PATH = os.path.join(data_dir, "stockpilot.db")


@contextmanager
def _get_connection():
    """Veritabanı bağlantısı için context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Veritabanı tablolarını oluşturur. Uygulama başlangıcında çağrılmalıdır."""
    with _get_connection() as conn:
        cursor = conn.cursor()

        # Arama geçmişi tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL DEFAULT 'TUT',
                confidence INTEGER NOT NULL DEFAULT 0
            )
        """)

        # İzleme listesi tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL
            )
        """)

        # Günlük öneriler tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL DEFAULT 'TUT',
                confidence INTEGER NOT NULL DEFAULT 0,
                score REAL NOT NULL DEFAULT 50.0,
                reason TEXT NOT NULL DEFAULT ''
            )
        """)

        # Portföy tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                buy_price REAL NOT NULL,
                quantity REAL NOT NULL,
                added_at TEXT NOT NULL
            )
        """)

        # İndeksler
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_history_timestamp
            ON search_history (timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_watchlist_symbol
            ON watchlist (symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_date
            ON daily_recommendations (date, symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_portfolio_symbol
            ON portfolio (symbol)
        """)

        conn.commit()


def add_to_history(symbol: str, name: str, action: str, confidence: int):
    """
    Arama geçmişine kayıt ekler.

    Args:
        symbol: Hisse sembolü
        name: Hisse adı
        action: Öneri aksiyonu (AL/SAT/TUT)
        confidence: Güven skoru (0-100)
    """
    with _get_connection() as conn:
        conn.execute(
            """INSERT INTO search_history (symbol, name, timestamp, action, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (symbol, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), action, confidence)
        )


def get_history(limit: int = 50) -> list:
    """
    Arama geçmişini döndürür (en yeni önce).

    Args:
        limit: Döndürülecek maksimum kayıt sayısı

    Returns:
        list: Geçmiş kayıtları listesi
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            """SELECT id, symbol, name, timestamp, action, confidence
               FROM search_history
               ORDER BY timestamp DESC
               LIMIT ?""",
            (limit,)
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "symbol": row["symbol"],
                "name": row["name"],
                "timestamp": row["timestamp"],
                "action": row["action"],
                "confidence": row["confidence"]
            }
            for row in rows
        ]


def add_to_watchlist(symbol: str, name: str):
    """
    İzleme listesine hisse ekler.

    Args:
        symbol: Hisse sembolü
        name: Hisse adı

    Raises:
        sqlite3.IntegrityError: Hisse zaten izleme listesindeyse
    """
    with _get_connection() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO watchlist (symbol, name, added_at)
               VALUES (?, ?, ?)""",
            (symbol, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )


def remove_from_watchlist(symbol: str):
    """
    İzleme listesinden hisse kaldırır.

    Args:
        symbol: Kaldırılacak hisse sembolü
    """
    with _get_connection() as conn:
        conn.execute(
            "DELETE FROM watchlist WHERE symbol = ?",
            (symbol,)
        )


def get_watchlist() -> list:
    """
    İzleme listesini döndürür.

    Returns:
        list: İzleme listesi kayıtları
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            """SELECT id, symbol, name, added_at
               FROM watchlist
               ORDER BY added_at DESC"""
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "symbol": row["symbol"],
                "name": row["name"],
                "added_at": row["added_at"]
            }
            for row in rows
        ]


def save_daily_recommendation(date_str: str, symbol: str, name: str,
                               action: str, confidence: int, score: float, reason: str):
    """
    Günlük öneri kaydeder.

    Args:
        date_str: Tarih (YYYY-MM-DD)
        symbol: Hisse sembolü
        name: Hisse adı
        action: Aksiyon (AL/SAT/TUT)
        confidence: Güven skoru
        score: Genel skor
        reason: Öneri açıklaması
    """
    with _get_connection() as conn:
        # Aynı gün ve sembol için var olan kaydı güncelle
        existing = conn.execute(
            "SELECT id FROM daily_recommendations WHERE date = ? AND symbol = ?",
            (date_str, symbol)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE daily_recommendations
                   SET name = ?, action = ?, confidence = ?, score = ?, reason = ?
                   WHERE date = ? AND symbol = ?""",
                (name, action, confidence, score, reason, date_str, symbol)
            )
        else:
            conn.execute(
                """INSERT INTO daily_recommendations (date, symbol, name, action, confidence, score, reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (date_str, symbol, name, action, confidence, score, reason)
            )


def get_daily_recommendations(target_date: str = None) -> list:
    """
    Belirtilen tarihin günlük önerilerini döndürür.

    Args:
        target_date: Tarih (YYYY-MM-DD), None ise bugünün tarihi kullanılır

    Returns:
        list: Günlük öneri kayıtları
    """
    if target_date is None:
        target_date = date.today().strftime("%Y-%m-%d")

    with _get_connection() as conn:
        cursor = conn.execute(
            """SELECT id, date, symbol, name, action, confidence, score, reason
               FROM daily_recommendations
               WHERE date = ?
               ORDER BY score DESC""",
            (target_date,)
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "date": row["date"],
                "symbol": row["symbol"],
                "name": row["name"],
                "action": row["action"],
                "confidence": row["confidence"],
                "score": row["score"],
                "reason": row["reason"]
            }
            for row in rows
        ]


def is_watchlisted(symbol: str) -> bool:
    """
    Hissenin izleme listesinde olup olmadığını kontrol eder.

    Args:
        symbol: Hisse sembolü

    Returns:
        bool: İzleme listesindeyse True
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) as cnt FROM watchlist WHERE symbol = ?",
            (symbol,)
        )
        row = cursor.fetchone()
        return row["cnt"] > 0


def clear_history():
    """Tüm arama geçmişini temizler."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM search_history")


def get_history_count() -> int:
    """Arama geçmişindeki kayıt sayısını döndürür."""
    with _get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM search_history")
        row = cursor.fetchone()
        return row["cnt"]


def add_portfolio_transaction(symbol: str, name: str, buy_price: float, quantity: float):
    """
    Portföye yeni alım işlemi ekler.
    """
    with _get_connection() as conn:
        conn.execute(
            """INSERT INTO portfolio (symbol, name, buy_price, quantity, added_at)
               VALUES (?, ?, ?, ?, ?)""",
            (symbol.upper().strip(), name, buy_price, quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )


def get_portfolio_transactions() -> list:
    """
    Portföydeki tüm işlemleri döndürür.
    """
    with _get_connection() as conn:
        cursor = conn.execute(
            """SELECT id, symbol, name, buy_price, quantity, added_at
               FROM portfolio
               ORDER BY added_at DESC"""
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "symbol": row["symbol"],
                "name": row["name"],
                "buy_price": row["buy_price"],
                "quantity": row["quantity"],
                "added_at": row["added_at"]
            }
            for row in rows
        ]


def delete_portfolio_transaction(transaction_id: int):
    """
    Portföyden işlem siler.
    """
    with _get_connection() as conn:
        conn.execute("DELETE FROM portfolio WHERE id = ?", (transaction_id,))
