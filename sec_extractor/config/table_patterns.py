"""
Patrones regex para identificar tablas críticas en N-CSR filings
Ordenados por prioridad (1 = más importante)
"""

CRITICAL_TABLE_PATTERNS = {
    1: {
        'name': 'portfolio_holdings',
        'description': 'Schedule of Investments - Portfolio Holdings',
        'patterns': [
            r'<table[^>]*(?:schedule.*of.*investments|portfolio.*holdings)[^>]*>.*?</table>',
            r'<table[^>]*investments.*securities.*unaffiliated[^>]*>.*?</table>',
            r'<table[^>]*investment.*portfolio[^>]*>.*?</table>'
        ],
        'critical': True
    },
    2: {
        'name': 'assets_liabilities',
        'description': 'Statement of Assets and Liabilities',
        'patterns': [
            r'<table[^>]*statement.*assets.*liabilities[^>]*>.*?</table>',
            r'<table[^>]*assets.*liabilities[^>]*>.*?</table>',
            r'<table[^>]*balance.*sheet[^>]*>.*?</table>'
        ],
        'critical': True
    },
    3: {
        'name': 'operations',
        'description': 'Statement of Operations',
        'patterns': [
            r'<table[^>]*statement.*operations[^>]*>.*?</table>',
            r'<table[^>]*income.*statement[^>]*>.*?</table>',
            r'<table[^>]*operations.*income[^>]*>.*?</table>'
        ],
        'critical': True
    },
    4: {
        'name': 'financial_highlights',
        'description': 'Financial Highlights',
        'patterns': [
            r'<table[^>]*financial.*highlights[^>]*>.*?</table>',
            r'<table[^>]*per.*share.*data[^>]*>.*?</table>',
            r'<table[^>]*highlights[^>]*>.*?</table>'
        ],
        'critical': True
    },
    5: {
        'name': 'expenses',
        'description': 'Expense Ratios and Fees',
        'patterns': [
            r'<table[^>]*expense.*ratio[^>]*>.*?</table>',
            r'<table[^>]*fees.*expenses[^>]*>.*?</table>',
            r'<table[^>]*operating.*expenses[^>]*>.*?</table>'
        ],
        'critical': True
    },
    6: {
        'name': 'performance',
        'description': 'Performance Data',
        'patterns': [
            r'<table[^>]*average.*annual.*return[^>]*>.*?</table>',
            r'<table[^>]*performance.*data[^>]*>.*?</table>',
            r'<table[^>]*total.*return[^>]*>.*?</table>'
        ],
        'critical': False
    },
    7: {
        'name': 'portfolio_composition',
        'description': 'Portfolio Composition by Category',
        'patterns': [
            r'<table[^>]*portfolio.*composition[^>]*>.*?</table>',
            r'<table[^>]*asset.*allocation[^>]*>.*?</table>',
            r'<table[^>]*holdings.*category[^>]*>.*?</table>'
        ],
        'critical': False
    },
    8: {
        'name': 'fund_statistics',
        'description': 'Fund Statistics',
        'patterns': [
            r'<table[^>]*fund.*statistics[^>]*>.*?</table>',
            r'<table[^>]*portfolio.*statistics[^>]*>.*?</table>'
        ],
        'critical': False
    },
    9: {
        'name': 'accountant_fees',
        'description': 'Principal Accountant Fees',
        'patterns': [
            r'<table[^>]*accountant.*fees[^>]*>.*?</table>',
            r'<table[^>]*audit.*fees[^>]*>.*?</table>'
        ],
        'critical': False
    },
    10: {
        'name': 'top_holdings',
        'description': 'Top Holdings Summary',
        'patterns': [
            r'<table[^>]*top.*holdings[^>]*>.*?</table>',
            r'<table[^>]*largest.*holdings[^>]*>.*?</table>'
        ],
        'critical': False
    }
}

# Patrones para extraer métricas clave sin parsear tablas completas
KEY_METRICS_PATTERNS = {
    'nav_per_share': r'net\s+asset\s+value.*?\$?([\d,]+\.?\d*)',
    'total_assets': r'total\s+(?:net\s+)?assets.*?\$?([\d,]+(?:,\d{3})*\.?\d*)',
    'expense_ratio': r'expense\s+ratio.*?([\d]+\.?\d*%)',
    'management_fee': r'management\s+fee.*?([\d]+\.?\d*%)',
    'portfolio_turnover': r'portfolio\s+turnover.*?([\d]+\.?\d*%)',
    'shares_outstanding': r'shares\s+outstanding.*?([\d,]+(?:,\d{3})*)'
}