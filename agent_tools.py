# agent_tools.py
from datetime import datetime, timedelta

class MockLogger:
    """Mock สำหรับ sales_logger และ morning_report"""
    
    def append_sale(self, menu, qty, price):
        total = qty * price
        return {'ok': True, 'message': f'บันทึก {menu} x{qty} @ {price} = {total} บาท', 'total': total}
    
    def get_yesterday_summary(self):
        return {'ok': True, 'message': 'สรุปยอดขายเมื่อวาน: 150 แก้ว, รายได้ 8,250 บาท'}

sales_logger = MockLogger()
morning_report = MockLogger()

def validate_sale(menu, qty, price):
    """🛡️ Validation Guardrail: ปฏิเสธ qty ติดลบหรือ 0"""
    if qty <= 0:
        return 'qty > 0'
    if price < 0:
        return 'price >= 0'
    if qty > 500:
        return 'qty too large'
    return None

def log_sale(menu, quantity, price):
    """Tool: บันทึกการขาย"""
    err = validate_sale(menu, quantity, price)
    if err:
        return {'ok': False, 'tool': 'log_sale', 'error': f'Validation failed: {err}'}
    return sales_logger.append_sale(menu, quantity, price)

def get_yesterday_summary():
    """Tool: สรุปยอดขายเมื่อวาน"""
    return morning_report.get_yesterday_summary()

def send_alert(message):
    """Tool: ส่งแจ้งเตือน"""
    return {'ok': True, 'message': f'ส่งแจ้งเตือน: {message}'}

TOOL_REGISTRY = {
    'log_sale': {
        'fn': log_sale,
        'args': ('menu', 'quantity', 'price'),
        'coerce': {'menu': str, 'quantity': int, 'price': float}
    },
    'get_yesterday_summary': {
        'fn': get_yesterday_summary,
        'args': (),
        'coerce': {}
    },
    'send_alert': {
        'fn': send_alert,
        'args': ('message',),
        'coerce': {'message': str}
    }
}

def execute_tool(tool_name, kwargs):
    """ตัวรัน Tool"""
    if tool_name not in TOOL_REGISTRY:
        return {'ok': False, 'error': f'Unknown tool: {tool_name}'}
    
    tool = TOOL_REGISTRY[tool_name]
    
    # Coerce types
    for k, v_type in tool['coerce'].items():
        if k in kwargs:
            try:
                kwargs[k] = v_type(kwargs[k])
            except:
                return {'ok': False, 'error': f'Bad type for {k}'}
    
    # Execute function
    try:
        return tool['fn'](**{k: kwargs[k] for k in tool['args']})
    except Exception as e:
        return {'ok': False, 'error': str(e)}