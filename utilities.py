def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_global_history(connection, cursor, limit=None):
    """
    Retrieve all entries from the database, sorted by datetime (newest first).
    
    Args:
        connection: SQLite connection object
        cursor: SQLite cursor object
        limit: Optional limit on number of entries to return
        
    Returns:
        List of entries sorted by datetime (newest first)
    """
    query = "SELECT * FROM lore ORDER BY datetime DESC"
    
    if limit:
        query += f" LIMIT {limit}"
    
    query += ";"
    
    results = cursor.execute(query)
    if not results:
        return []
    
    return results.fetchall()
