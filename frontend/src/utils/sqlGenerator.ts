
export const escapeSqlString = (str: string): string => {
  return str.replace(/'/g, "''");
};

export const formatValue = (value: any): string => {
  if (value === null || value === undefined) {
    return 'NULL';
  }
  if (typeof value === 'number') {
    return String(value);
  }
  if (typeof value === 'boolean') {
    return value ? '1' : '0';
  }
  if (typeof value === 'object') {
    // Handle dates or other objects
    if (value instanceof Date) {
        return `'${value.toISOString()}'`;
    }
    return `'${escapeSqlString(JSON.stringify(value))}'`;
  }
  return `'${escapeSqlString(String(value))}'`;
};

export const generateInsertStatements = (tableName: string, rows: any[]): string => {
  if (!rows || rows.length === 0) return '';
  
  // Assuming all rows have same keys, or at least we take keys from first row
  // Better to take union of all keys if possible, but taking keys from first row is standard enough
  // Actually, we should probably use the keys present in the row object
  
  return rows.map(row => {
    const keys = Object.keys(row);
    const columns = keys.map(k => `\`${k}\``).join(', ');
    const values = keys.map(k => formatValue(row[k])).join(', ');
    return `INSERT INTO \`${tableName}\` (${columns}) VALUES (${values});`;
  }).join('\n');
};

export const generateUpdateStatements = (tableName: string, rows: any[], primaryKeys: string[]): string => {
  if (!rows || rows.length === 0) return '';
  if (!primaryKeys || primaryKeys.length === 0) {
    return '-- Cannot generate UPDATE statements without primary keys';
  }

  return rows.map(row => {
    const setClause = Object.keys(row)
      .filter(key => !primaryKeys.includes(key)) // Don't update PK
      .map(key => `\`${key}\` = ${formatValue(row[key])}`)
      .join(', ');
      
    const whereClause = primaryKeys
      .map(pk => `\`${pk}\` = ${formatValue(row[pk])}`)
      .join(' AND ');
      
    if (!setClause) return `-- No columns to update for row with PK ${whereClause}`;
    
    return `UPDATE \`${tableName}\` SET ${setClause} WHERE ${whereClause};`;
  }).join('\n');
};
